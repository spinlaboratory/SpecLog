"""Qt editor for the public SpecLog configuration file."""

import ast
from configparser import ConfigParser
import locale
import os
from pathlib import Path
import shutil
import sys
import tempfile
from xml.etree import ElementTree

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .config.config import ensure_public_config
from .loggerConfig import device_default, loggerConfig
from .logger_status import is_logger_running
from .startup_task import (
    POWERSHELL,
    TASK_SCHEDULER,
    control_arguments,
    query_arguments,
    state_arguments,
)


class IndicatorEditor(QDialog):
    """Edit the ordered status bits and their good-state polarity."""

    def __init__(self, indicators, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bit-status indicators")
        self.resize(540, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Reverse means that a zero bit is healthy; otherwise a one bit "
                "is healthy."
            )
        )
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Indicator", "Reverse"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 390)
        layout.addWidget(self.table)
        controls = QHBoxLayout()
        add_button = QPushButton("Add indicator")
        add_button.clicked.connect(lambda: self._add_row("", False))
        delete_button = QPushButton("Delete indicator")
        delete_button.clicked.connect(self._delete_rows)
        controls.addWidget(add_button)
        controls.addWidget(delete_button)
        controls.addStretch()
        layout.addLayout(controls)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for indicator in indicators:
            self._add_row(indicator["name"], indicator["reverse"])
        self._update_summary()

    def _add_row(self, name, reverse):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        checkbox = QCheckBox()
        checkbox.setChecked(reverse)
        checkbox.stateChanged.connect(self._update_summary)
        self.table.setCellWidget(row, 1, checkbox)
        self._update_summary()

    def _delete_rows(self):
        rows = sorted(
            {index.row() for index in self.table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            self.table.removeRow(row)
        self._update_summary()

    def indicators(self):
        result = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            checkbox = self.table.cellWidget(row, 1)
            if name:
                result.append({"name": name, "reverse": checkbox.isChecked()})
        return result

    def _update_summary(self):
        indicators = self.indicators()
        bits, bit_static = ConfigEditor._calculate_bit_settings(indicators)
        self.summary.setText(
            f"Automatically calculated: bits = {bits or 0}, "
            f"bit_static = {bit_static or '-'}"
        )


class ConfigEditor(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        self.config_path = Path(config_path or ensure_public_config())
        self.config = ConfigParser(interpolation=None)
        self.current_section = None
        self.logger_action = None
        self.logger_action_uses_task = False
        self.logger_log_offset = 0
        self.startup_state = "Checking..."
        self.scheduled_task_running = False
        self.setWindowTitle("SpecLog Configuration")
        self.resize(900, 600)
        self._build_ui()
        self.load_config()

    def _build_ui(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)

        splitter = QSplitter()
        section_panel = QWidget()
        section_layout = QVBoxLayout(section_panel)
        section_layout.addWidget(QLabel("Sections"))
        self.section_list = QListWidget()
        self.section_list.currentTextChanged.connect(self.change_section)
        section_layout.addWidget(self.section_list)
        section_buttons = QHBoxLayout()
        add_section = QPushButton("Add")
        add_section.clicked.connect(self.add_section)
        delete_section = QPushButton("Delete")
        delete_section.clicked.connect(self.delete_section)
        section_buttons.addWidget(add_section)
        section_buttons.addWidget(delete_section)
        section_layout.addLayout(section_buttons)
        splitter.addWidget(section_panel)

        value_panel = QWidget()
        value_layout = QVBoxLayout(value_panel)
        self.section_label = QLabel("Values")
        value_layout.addWidget(self.section_label)
        self.value_tabs = QTabWidget()

        communication_tab = QWidget()
        communication_layout = QVBoxLayout(communication_tab)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Attribute", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        communication_layout.addWidget(self.table)
        row_buttons = QHBoxLayout()
        add_row = QPushButton("Add attribute")
        add_row.clicked.connect(self.add_row)
        delete_row = QPushButton("Delete attribute")
        delete_row.clicked.connect(self.delete_rows)
        row_buttons.addWidget(add_row)
        row_buttons.addWidget(delete_row)
        row_buttons.addStretch()
        communication_layout.addLayout(row_buttons)
        self.value_tabs.addTab(communication_tab, "Communication")

        commands_tab = QWidget()
        commands_layout = QVBoxLayout(commands_tab)
        self.command_type_tabs = QTabWidget()
        self.value_command_table = self._make_command_table(
            ["Variable", "Command", "Alias", "Min", "Max", "Static"]
        )
        self.bit_command_table = self._make_command_table(
            ["Variable", "Command", "Alias", "Indicators"]
        )
        self.command_type_tabs.addTab(self.value_command_table, "Values")
        self.command_type_tabs.addTab(self.bit_command_table, "Status Indicators")
        commands_layout.addWidget(self.command_type_tabs)
        command_buttons = QHBoxLayout()
        self.add_value_command_button = QPushButton("Add value command")
        self.add_value_command_button.clicked.connect(self.add_value_command)
        self.add_status_command_button = QPushButton(
            "Add status indicator command"
        )
        self.add_status_command_button.clicked.connect(self.add_bit_command)
        self.add_status_command_button.hide()
        delete_command = QPushButton("Delete command")
        delete_command.clicked.connect(self.delete_commands)
        command_buttons.addWidget(self.add_value_command_button)
        command_buttons.addWidget(self.add_status_command_button)
        command_buttons.addWidget(delete_command)
        command_buttons.addStretch()
        commands_layout.addLayout(command_buttons)
        self.command_type_tabs.currentChanged.connect(
            self._update_command_buttons
        )
        self.value_tabs.addTab(commands_tab, "Commands")
        value_layout.addWidget(self.value_tabs)
        splitter.addWidget(value_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)

        logger_title = QLabel("SpecLogger:")
        logger_title.setStyleSheet("font-weight: bold;")
        self.logger_status_label = QLabel("Checking status...")
        self.logger_message_area = QPlainTextEdit()
        self.logger_message_area.setReadOnly(True)
        self.logger_message_area.setMaximumHeight(58)
        self.logger_message_area.setPlaceholderText("SpecLogger messages")
        self.full_logger_message = ""
        self.logger_message_is_error = False
        self.start_logger_button = QPushButton("Start")
        self.start_logger_button.clicked.connect(
            lambda: self._run_logger_command("start")
        )
        self.stop_logger_button = QPushButton("Stop")
        self.stop_logger_button.clicked.connect(
            lambda: self._run_logger_command("stop")
        )
        startup_title = QLabel("Startup:")
        startup_title.setStyleSheet("font-weight: bold;")
        self.startup_status_label = QLabel("Checking...")
        self.enable_startup_button = QPushButton("Enable")
        self.enable_startup_button.clicked.connect(
            lambda: self._run_startup_command(True)
        )
        self.disable_startup_button = QPushButton("Disable")
        self.disable_startup_button.clicked.connect(
            lambda: self._run_startup_command(False)
        )
        self.logger_process = QProcess(self)
        self.logger_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self.logger_process.finished.connect(self._logger_command_finished)
        self.logger_process.errorOccurred.connect(self._logger_command_error)
        self.task_state_process = QProcess(self)
        self.task_state_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self.task_state_process.finished.connect(self._task_state_finished)
        self.task_state_process.errorOccurred.connect(
            lambda error: self._set_logger_running_state(None)
        )
        self.logger_timer = QTimer(self)
        self.logger_timer.setInterval(1000)
        self.logger_timer.timeout.connect(self._refresh_logger_status)
        self.logger_timer.start()
        self._refresh_logger_status()

        self.startup_process = QProcess(self)
        self.startup_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self.startup_process.finished.connect(self._startup_command_finished)
        self.startup_process.errorOccurred.connect(self._startup_command_error)
        self.startup_query_process = QProcess(self)
        self.startup_query_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self.startup_query_process.finished.connect(self._startup_query_finished)
        self.startup_query_process.errorOccurred.connect(self._startup_query_error)
        self.startup_timer = QTimer(self)
        self.startup_timer.setInterval(5000)
        self.startup_timer.timeout.connect(self._refresh_startup_status)
        self.startup_timer.start()
        self._refresh_startup_status()

        message_row = QHBoxLayout()
        message_label = QLabel("Messages:")
        message_label.setStyleSheet("font-weight: bold;")
        message_row.addWidget(message_label)
        message_row.addWidget(self.logger_message_area, 1)
        layout.addLayout(message_row)

        actions = QHBoxLayout()
        actions.addWidget(logger_title)
        actions.addWidget(self.logger_status_label)
        actions.addWidget(self.start_logger_button)
        actions.addWidget(self.stop_logger_button)
        actions.addSpacing(8)
        actions.addWidget(startup_title)
        actions.addWidget(self.startup_status_label)
        actions.addWidget(self.enable_startup_button)
        actions.addWidget(self.disable_startup_button)
        actions.addSpacing(12)
        self.status_label = QLabel()
        actions.addWidget(self.status_label)
        actions.addStretch()
        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.load_config)
        save_button = QPushButton("Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self.save_config)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        actions.addWidget(reload_button)
        actions.addWidget(save_button)
        actions.addWidget(close_button)
        layout.addLayout(actions)
        self.setCentralWidget(central)

    @staticmethod
    def _make_command_table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        return table

    def _update_command_buttons(self, tab_index):
        self.add_value_command_button.setVisible(tab_index == 0)
        self.add_status_command_button.setVisible(tab_index == 1)

    def _set_logger_message(self, message, popup=False):
        message = str(message).strip()
        self.full_logger_message = message
        self.logger_message_is_error = popup
        self.logger_message_area.setPlainText(message)
        self.logger_message_area.setStyleSheet(
            "QPlainTextEdit { color: #b00020; }" if popup else ""
        )
        scrollbar = self.logger_message_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _is_logger_running():
        return is_logger_running()

    def _refresh_logger_status(self):
        if os.name != "nt":
            self.logger_status_label.setText("Status unavailable")
            self.start_logger_button.setEnabled(False)
            self.stop_logger_button.setEnabled(False)
            return
        # "Unknown" means that the task was found but its XML did not expose a
        # startup setting we understand.  Its runtime state is still available
        # from Task Scheduler and is more authoritative than the process-local
        # mutex check (the task normally runs as SYSTEM).
        if self.startup_state in {"Enabled", "Disabled", "Unknown"}:
            if (
                self.task_state_process.state()
                != QProcess.ProcessState.NotRunning
            ):
                return
            self.task_state_process.start(
                POWERSHELL,
                state_arguments(),
            )
            return
        running = self._is_logger_running()
        self._set_logger_running_state(running)

    def _task_state_finished(self, exit_code, exit_status):
        output = self._decode_process_output(self.task_state_process.readAll()).strip()
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code:
            self.scheduled_task_running = False
            self._set_logger_running_state(None)
            return
        try:
            state = int(output)
        except ValueError:
            self.scheduled_task_running = False
            self._set_logger_running_state(None)
            return
        # MSFT_TaskState: Disabled=1, Queued=2, Ready=3, Running=4.
        self.scheduled_task_running = state in {2, 4}
        self._set_logger_running_state(self.scheduled_task_running)

    def _set_logger_running_state(self, running):
        if running is None:
            self.logger_status_label.setText("Status unavailable")
            self.logger_status_label.setStyleSheet(
                "color: gray; font-weight: bold;"
            )
            self.start_logger_button.setEnabled(False)
            self.stop_logger_button.setEnabled(False)
            return
        self.logger_status_label.setText("Running" if running else "Stopped")
        self.logger_status_label.setStyleSheet(
            "color: green; font-weight: bold;"
            if running
            else "color: red; font-weight: bold;"
        )
        command_active = (
            self.logger_process.state() != QProcess.ProcessState.NotRunning
        )
        self.start_logger_button.setEnabled(not running and not command_active)
        self.stop_logger_button.setEnabled(running and not command_active)

    def _run_logger_command(self, action):
        if self.logger_process.state() != QProcess.ProcessState.NotRunning:
            return
        self.logger_action = action
        self.logger_action_uses_task = (
            self.startup_state == "Enabled" or self.scheduled_task_running
        )
        debug_log = self._debug_log_path()
        try:
            self.logger_log_offset = debug_log.stat().st_size
        except OSError:
            self.logger_log_offset = 0
        self._set_logger_message(
            "Starting SpecLogger..." if action == "start" else "Stopping SpecLogger..."
        )
        self.start_logger_button.setEnabled(False)
        self.stop_logger_button.setEnabled(False)
        if self.logger_action_uses_task:
            self.logger_process.start(
                TASK_SCHEDULER, control_arguments(action)
            )
        else:
            self.logger_process.start(
                sys.executable, ["-m", "SpecLog.SpecLogger", action]
            )

    def _logger_command_finished(self, exit_code, exit_status):
        output = bytes(self.logger_process.readAll()).decode(errors="replace").strip()
        action = self.logger_action
        used_task = self.logger_action_uses_task
        self.logger_action = None
        self.logger_action_uses_task = False
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code:
            self._set_logger_message(
                output or f"SpecLogger command failed with exit code {exit_code}.",
                popup=True,
            )
            self._refresh_logger_status()
            return
        if output:
            self._set_logger_message(output)
        if used_task:
            self._set_logger_message(
                "SpecLogger scheduled task start requested."
                if action == "start"
                else "SpecLogger scheduled task stopped."
            )
            QTimer.singleShot(800, self._refresh_logger_status)
            return
        QTimer.singleShot(1200, lambda: self._verify_logger_action(action))

    def _logger_command_error(self, error):
        self._set_logger_message(
            f"Could not run the SpecLogger command: "
            f"{self.logger_process.errorString()}",
            popup=True,
        )
        self.logger_action = None
        self._refresh_logger_status()

    def _verify_logger_action(self, action):
        self._refresh_logger_status()
        running = self._is_logger_running()
        succeeded = running if action == "start" else not running
        if succeeded:
            self._set_logger_message(
                "SpecLogger started." if running else "SpecLogger stopped."
            )
        else:
            error = self._latest_logger_error()
            self._set_logger_message(
                error
                or (
                    "SpecLogger stopped before startup completed."
                    if action == "start"
                    else "SpecLogger did not stop."
                ),
                popup=True,
            )

    def _refresh_startup_status(self):
        if os.name != "nt":
            self._set_startup_state("Unavailable")
            return
        if (
            self.startup_process.state() != QProcess.ProcessState.NotRunning
            or self.startup_query_process.state()
            != QProcess.ProcessState.NotRunning
        ):
            return
        if self.startup_state not in {"Enabled", "Disabled", "Not installed"}:
            self._set_startup_state("Checking...")
        self.startup_query_process.start(
            TASK_SCHEDULER,
            query_arguments(xml=True),
        )

    def _startup_query_finished(self, exit_code, exit_status):
        raw_output = bytes(self.startup_query_process.readAll())
        output = self._decode_process_output(raw_output)
        if exit_status != QProcess.ExitStatus.NormalExit:
            self._set_startup_state("Unavailable")
            self._set_logger_message(
                output or "Could not query the SpecLogger startup task.",
                popup=True,
            )
            return
        if exit_code:
            lowered = output.lower()
            missing = any(
                phrase in lowered
                for phrase in (
                    "cannot find",
                    "does not exist",
                    "path specified",
                )
            )
            self._set_startup_state("Not installed" if missing else "Unavailable")
            if not missing:
                self._set_logger_message(
                    output
                    or "The startup task exists but this account cannot query it. "
                    "Run the configuration editor as administrator.",
                    popup=True,
                )
            return
        try:
            enabled = self._parse_task_enabled(raw_output)
        except (ElementTree.ParseError, StopIteration, ValueError):
            self._set_startup_state("Unknown")
            self._set_logger_message(
                "Task Scheduler returned an unreadable startup-task definition.",
                popup=True,
            )
            return
        self._set_startup_state("Enabled" if enabled else "Disabled")

    def _startup_query_error(self, error):
        self._set_startup_state("Unavailable")
        self._set_logger_message(
            f"Could not query the startup task: "
            f"{self.startup_query_process.errorString()}",
            popup=True,
        )

    @staticmethod
    def _parse_task_enabled(raw_output):
        """Read the Enabled setting from UTF-8 or UTF-16 task XML."""
        raw = bytes(raw_output)
        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError:
            text = ConfigEditor._decode_process_output(raw)
            declaration_end = text.find("?>")
            if declaration_end >= 0:
                text = text[declaration_end + 2 :]
            root = ElementTree.fromstring(text.lstrip("\ufeff\r\n "))
        enabled_element = next(
            (
                element
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] == "Enabled"
            ),
            None,
        )
        # Enabled is optional in the Task Scheduler schema and defaults to
        # true when omitted.
        if enabled_element is None:
            return True
        enabled_text = enabled_element.text
        normalized = (enabled_text or "").strip().lower()
        if normalized not in {"true", "false"}:
            raise ValueError(f"Unexpected Enabled value: {enabled_text!r}")
        return normalized == "true"

    def _set_startup_state(self, state):
        previous_state = self.startup_state
        self.startup_state = state
        self.startup_status_label.setText(state)
        color = {
            "Enabled": "green",
            "Disabled": "red",
            "Not installed": "red",
        }.get(state, "gray")
        self.startup_status_label.setStyleSheet(
            f"color: {color}; font-weight: bold;"
        )
        command_active = (
            self.startup_process.state() != QProcess.ProcessState.NotRunning
        )
        self.enable_startup_button.setEnabled(
            not command_active and state in {"Disabled", "Not installed"}
        )
        self.disable_startup_button.setEnabled(
            not command_active and state == "Enabled"
        )
        if state != previous_state and state != "Checking...":
            self._refresh_logger_status()

    def _run_startup_command(self, enabled):
        if self.startup_process.state() != QProcess.ProcessState.NotRunning:
            return
        self._set_logger_message(
            "Enabling startup..." if enabled else "Disabling startup..."
        )
        self.enable_startup_button.setEnabled(False)
        self.disable_startup_button.setEnabled(False)
        self.startup_process.start(
            sys.executable,
            ["-m", "SpecLog.SpecLogger", "-startup", str(enabled)],
        )

    def _startup_command_finished(self, exit_code, exit_status):
        output = self._decode_process_output(self.startup_process.readAll()).strip()
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code:
            self._set_logger_message(
                output
                or "Could not change startup. Run the configuration editor as "
                "administrator.",
                popup=True,
            )
        else:
            self._set_logger_message(
                output.splitlines()[-1] if output else "Startup setting updated."
            )
        QTimer.singleShot(500, self._refresh_startup_status)

    def _startup_command_error(self, error):
        self._set_logger_message(
            f"Could not change startup: {self.startup_process.errorString()}",
            popup=True,
        )
        self._refresh_startup_status()

    @staticmethod
    def _decode_process_output(output):
        raw = bytes(output)
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw[:100]:
            return raw.decode("utf-16", errors="replace")
        return raw.decode(locale.getpreferredencoding(False), errors="replace")

    def _latest_logger_error(self):
        debug_log = self._debug_log_path()
        try:
            with debug_log.open("rb") as stream:
                stream.seek(self.logger_log_offset)
                text = stream.read().decode("utf-8", errors="replace")
            lines = text.splitlines()
        except OSError:
            return ""
        for line in reversed(lines):
            if " - ERROR - " in line or " - CRITICAL - " in line:
                return line
        return ""

    def _debug_log_path(self):
        try:
            folder = Path(self.config["SETTINGS"]["log_folder_location"])
        except KeyError:
            return Path("debug_log.txt")
        return folder / "LOG" / "debug_log.txt"

    def load_config(self):
        self.current_section = None
        self.config = ConfigParser(interpolation=None)
        read = self.config.read(self.config_path)
        if not read:
            QMessageBox.critical(
                self, "Configuration error", f"Could not read {self.config_path}"
            )
            return
        self.setWindowTitle(f"SpecLog Configuration - {self.config_path.name}")
        self.status_label.setToolTip(str(self.config_path))
        self.section_list.blockSignals(True)
        self.section_list.clear()
        self.section_list.addItems(self.config.sections())
        self.section_list.blockSignals(False)
        if self.section_list.count():
            self.section_list.setCurrentRow(0)
        self.status_label.setText("Loaded")

    def _commit_current_section(self):
        if not self.current_section:
            return
        values = {}
        for table in [self.table]:
            for row in range(table.rowCount()):
                key_item = table.item(row, 0)
                value_item = table.item(row, 1)
                key = key_item.text().strip() if key_item else ""
                value = value_item.text().strip() if value_item else ""
                if not key:
                    raise ValueError(
                        f"Section [{self.current_section}] has an empty key"
                    )
                normalized = key.lower()
                if normalized in values:
                    raise ValueError(
                        f"Section [{self.current_section}] contains duplicate key "
                        f"{key!r}"
                    )
                values[normalized] = value
        if self.current_section != "SETTINGS":
            command_tables = (
                (self.value_command_table, ["alias", "min", "max", "static"]),
                (
                    self.bit_command_table,
                    ["alias"],
                ),
            )
            for table, option_names in command_tables:
                for row in range(table.rowCount()):
                    key = self._cell_text(table, row, 0)
                    command = self._cell_text(table, row, 1)
                    if not key or not command:
                        raise ValueError(
                            f"Section [{self.current_section}] has a command with "
                            "an empty variable or command"
                        )
                    normalized = key.lower()
                    if normalized in values:
                        raise ValueError(
                            f"Section [{self.current_section}] contains duplicate "
                            f"key {key!r}"
                        )
                    parts = [command]
                    for column, option in enumerate(option_names, start=2):
                        option_value = self._cell_text(table, row, column)
                        if option_value:
                            parts.append(f"{option} = {option_value}")
                    if table is self.bit_command_table:
                        indicators = self._indicator_data(table, row)
                        if not indicators:
                            raise ValueError(
                                f"Bit-status command {key!r} requires at least one "
                                "indicator"
                            )
                        bits, bit_static = self._calculate_bit_settings(indicators)
                        indicator_values = [
                            ("*" if item["reverse"] else "") + item["name"]
                            for item in indicators
                        ]
                        parts.extend(
                            [
                                f"bits = {bits}",
                                f"bit_static = {bit_static}",
                                f"indicators = {indicator_values!r}",
                            ]
                        )
                    values[normalized] = ", ".join(parts)
        self.config.remove_section(self.current_section)
        self.config.add_section(self.current_section)
        for key, value in values.items():
            self.config.set(self.current_section, key, value)

    def change_section(self, section):
        try:
            self._commit_current_section()
        except ValueError as error:
            QMessageBox.warning(self, "Invalid value", str(error))
            return
        self.current_section = section or None
        self.section_label.setText(f"Values - [{section}]" if section else "Values")
        self.table.setRowCount(0)
        self.value_command_table.setRowCount(0)
        self.bit_command_table.setRowCount(0)
        if not section or not self.config.has_section(section):
            return
        is_settings = section == "SETTINGS"
        self.value_tabs.setTabText(0, "Settings" if is_settings else "Communication")
        self.table.setHorizontalHeaderLabels(
            ["Setting", "Value"] if is_settings else ["Attribute", "Value"]
        )
        self.value_tabs.setTabVisible(1, not is_settings)
        for key, value in self.config.items(section):
            if is_settings or key in device_default:
                self._append_row(self.table, key, value)
            else:
                self._append_command_row(key, value)

    @staticmethod
    def _append_row(table, key, value):
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(key))
        table.setItem(row, 1, QTableWidgetItem(value))

    @staticmethod
    def _cell_text(table, row, column):
        item = table.item(row, column)
        return item.text().strip() if item else ""

    def _append_command_row(self, variable, command_string):
        parts = loggerConfig._split_command_items(command_string)
        command = parts[0].strip() if parts else ""
        options = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                options[key.strip().lower()] = value.strip()
        is_bit_status = "bits" in options
        table = self.bit_command_table if is_bit_status else self.value_command_table
        option_names = ["alias"] if is_bit_status else ["alias", "min", "max", "static"]
        row = table.rowCount()
        table.insertRow(row)
        entries = [variable, command] + [options.get(name, "") for name in option_names]
        for column, entry in enumerate(entries):
            table.setItem(row, column, QTableWidgetItem(entry))
        if is_bit_status:
            indicators = self._parse_indicators(options.get("indicators", ""))
            self._set_indicator_button(table, row, indicators)

    @staticmethod
    def _parse_indicators(value):
        if not value:
            return []
        try:
            names = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            names = []
        return [
            {
                "name": str(name).lstrip("*").strip(),
                "reverse": str(name).startswith("*"),
            }
            for name in names
            if str(name).lstrip("*").strip()
        ]

    @staticmethod
    def _calculate_bit_settings(indicators):
        bits = len(indicators)
        if not bits:
            return 0, ""
        displayed_bits = "".join(
            "0" if indicator["reverse"] else "1" for indicator in indicators
        )
        raw_bits = displayed_bits[::-1]
        # Status words include a leading set bit before the indicator payload.
        # The monitor later trims this marker when it keeps only ``bits`` bits.
        status_word = (1 << bits) | int(raw_bits, 2)
        return bits, format(status_word, "X")

    @staticmethod
    def _indicator_data(table, row):
        button = table.cellWidget(row, 3)
        return button.property("indicators") if button else []

    def _set_indicator_button(self, table, row, indicators):
        button = QPushButton()
        button.setProperty("indicators", indicators)
        self._refresh_indicator_button(button)
        button.clicked.connect(lambda: self._edit_indicators(button))
        table.setCellWidget(row, 3, button)

    @staticmethod
    def _refresh_indicator_button(button):
        indicators = button.property("indicators") or []
        bits, bit_static = ConfigEditor._calculate_bit_settings(indicators)
        button.setText(f"{bits} indicators - edit")
        button.setToolTip(f"bits = {bits}; bit_static = {bit_static or '-'}")

    def _edit_indicators(self, button):
        editor = IndicatorEditor(button.property("indicators") or [], self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            button.setProperty("indicators", editor.indicators())
            self._refresh_indicator_button(button)

    def add_section(self):
        name, accepted = QInputDialog.getText(self, "Add section", "Section name:")
        name = name.strip()
        if not accepted or not name:
            return
        if self.config.has_section(name):
            QMessageBox.warning(self, "Duplicate section", f"[{name}] already exists")
            return
        self._commit_current_section()
        self.config.add_section(name)
        self.section_list.addItem(name)
        self.section_list.setCurrentRow(self.section_list.count() - 1)

    def delete_section(self):
        section = self.section_list.currentItem()
        if section is None:
            return
        name = section.text()
        if name == "SETTINGS":
            QMessageBox.warning(self, "Required section", "[SETTINGS] cannot be deleted")
            return
        if QMessageBox.question(
            self, "Delete section", f"Delete [{name}]?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.config.remove_section(name)
        self.current_section = None
        self.section_list.takeItem(self.section_list.row(section))

    def add_row(self):
        if not self.current_section:
            return
        existing = {
            self.table.item(row, 0).text().strip().lower()
            for row in range(self.table.rowCount())
            if self.table.item(row, 0)
        }
        missing = [key for key in device_default if key not in existing]
        key = "new_setting" if self.current_section == "SETTINGS" else (
            missing[0] if missing else "new_attribute"
        )
        self._append_row(self.table, key, "")
        row = self.table.rowCount() - 1
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))

    def delete_rows(self):
        self._delete_selected_rows(self.table)

    def add_value_command(self):
        if not self.current_section or self.current_section == "SETTINGS":
            return
        self._add_empty_command(self.value_command_table)
        self.command_type_tabs.setCurrentIndex(0)

    def add_bit_command(self):
        if not self.current_section or self.current_section == "SETTINGS":
            return
        self._add_empty_command(self.bit_command_table)
        self._set_indicator_button(
            self.bit_command_table, self.bit_command_table.rowCount() - 1, []
        )
        self.command_type_tabs.setCurrentIndex(1)

    @staticmethod
    def _add_empty_command(table):
        row = table.rowCount()
        table.insertRow(row)
        for column in range(table.columnCount()):
            table.setItem(row, column, QTableWidgetItem(""))
        table.setItem(row, 0, QTableWidgetItem("new_variable"))
        table.setCurrentCell(row, 0)
        table.editItem(table.item(row, 0))

    def delete_commands(self):
        table = (
            self.value_command_table
            if self.command_type_tabs.currentIndex() == 0
            else self.bit_command_table
        )
        self._delete_selected_rows(table)

    @staticmethod
    def _delete_selected_rows(table):
        rows = sorted(
            {index.row() for index in table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            table.removeRow(row)

    def save_config(self):
        temp_path = None
        try:
            self._commit_current_section()
            self._validate_structure()
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                prefix="config-", suffix=".cfg", dir=self.config_path.parent
            )
            temp_path = Path(temp_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                self.config.write(stream)
            # Exercise the same parser used by the logger before replacing the
            # working configuration.
            loggerConfig(str(temp_path))
            if self.config_path.exists():
                shutil.copy2(self.config_path, self.config_path.with_suffix(".cfg.bak"))
            os.replace(temp_path, self.config_path)
            temp_path = None
            self.status_label.setText(
                "Saved - restart SpecLogger and SpecMonitor to apply changes"
            )
        except Exception as error:
            QMessageBox.critical(self, "Could not save configuration", str(error))
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def _validate_structure(self):
        if not self.config.has_section("SETTINGS"):
            raise ValueError("The required [SETTINGS] section is missing")
        required = {"log_interval", "log_folder_location", "save_file_size_kb"}
        missing = required.difference(self.config["SETTINGS"])
        if missing:
            raise ValueError(
                "[SETTINGS] is missing: " + ", ".join(sorted(missing))
            )


def main_func(config_path=None):
    app = QApplication.instance() or QApplication([])
    window = ConfigEditor(config_path)
    window.show()
    return app.exec()
