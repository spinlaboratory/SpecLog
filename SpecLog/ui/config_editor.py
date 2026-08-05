"""Widget construction for the SpecLog configuration editor."""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class IndicatorEditor(QDialog):
    """Edit the ordered status bits and their good-state polarity."""

    def __init__(self, indicators, calculator, parent=None):
        super().__init__(parent)
        self.calculator = calculator
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
        bits, bit_static = self.calculator(self.indicators())
        self.summary.setText(
            f"Automatically calculated: bits = {bits or 0}, "
            f"bit_static = {bit_static or '-'}"
        )


def _make_command_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    return table


def setup_config_editor_ui(editor):
    """Build the editor widgets and connect them to its controller methods."""
    central = QWidget(editor)
    layout = QVBoxLayout(central)

    splitter = QSplitter()
    section_panel = QWidget()
    section_layout = QVBoxLayout(section_panel)
    section_layout.addWidget(QLabel("Sections"))
    editor.section_list = QListWidget()
    editor.section_list.currentTextChanged.connect(editor.change_section)
    section_layout.addWidget(editor.section_list)
    section_buttons = QHBoxLayout()
    add_section = QPushButton("Add")
    add_section.clicked.connect(editor.add_section)
    delete_section = QPushButton("Delete")
    delete_section.clicked.connect(editor.delete_section)
    section_buttons.addWidget(add_section)
    section_buttons.addWidget(delete_section)
    section_layout.addLayout(section_buttons)
    splitter.addWidget(section_panel)

    value_panel = QWidget()
    value_layout = QVBoxLayout(value_panel)
    editor.section_label = QLabel("Values")
    value_layout.addWidget(editor.section_label)
    editor.value_tabs = QTabWidget()

    communication_tab = QWidget()
    communication_layout = QVBoxLayout(communication_tab)
    editor.table = QTableWidget(0, 2)
    editor.table.setHorizontalHeaderLabels(["Attribute", "Value"])
    editor.table.horizontalHeader().setStretchLastSection(True)
    editor.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    communication_layout.addWidget(editor.table)
    row_buttons = QHBoxLayout()
    add_row = QPushButton("Add attribute")
    add_row.clicked.connect(editor.add_row)
    delete_row = QPushButton("Delete attribute")
    delete_row.clicked.connect(editor.delete_rows)
    row_buttons.addWidget(add_row)
    row_buttons.addWidget(delete_row)
    row_buttons.addStretch()
    communication_layout.addLayout(row_buttons)
    editor.value_tabs.addTab(communication_tab, "Communication")

    commands_tab = QWidget()
    commands_layout = QVBoxLayout(commands_tab)
    editor.command_type_tabs = QTabWidget()
    editor.value_command_table = _make_command_table(
        ["Variable", "Command", "Alias", "Min", "Max", "Static"]
    )
    editor.bit_command_table = _make_command_table(
        ["Variable", "Command", "Alias", "Indicators"]
    )
    editor.command_type_tabs.addTab(editor.value_command_table, "Values")
    editor.command_type_tabs.addTab(
        editor.bit_command_table, "Status Indicators"
    )
    commands_layout.addWidget(editor.command_type_tabs)
    command_buttons = QHBoxLayout()
    editor.add_value_command_button = QPushButton("Add value command")
    editor.add_value_command_button.clicked.connect(editor.add_value_command)
    editor.add_status_command_button = QPushButton(
        "Add status indicator command"
    )
    editor.add_status_command_button.clicked.connect(editor.add_bit_command)
    editor.add_status_command_button.hide()
    delete_command = QPushButton("Delete command")
    delete_command.clicked.connect(editor.delete_commands)
    command_buttons.addWidget(editor.add_value_command_button)
    command_buttons.addWidget(editor.add_status_command_button)
    command_buttons.addWidget(delete_command)
    command_buttons.addStretch()
    commands_layout.addLayout(command_buttons)
    editor.command_type_tabs.currentChanged.connect(editor._update_command_buttons)
    editor.value_tabs.addTab(commands_tab, "Commands")
    value_layout.addWidget(editor.value_tabs)
    splitter.addWidget(value_panel)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 4)
    layout.addWidget(splitter)

    logger_title = QLabel("SpecLogger:")
    logger_title.setStyleSheet("font-weight: bold;")
    editor.logger_status_label = QLabel("Checking status...")
    editor.logger_message_area = QPlainTextEdit()
    editor.logger_message_area.setReadOnly(True)
    editor.logger_message_area.setMaximumHeight(58)
    editor.logger_message_area.setPlaceholderText("SpecLogger messages")
    editor.start_logger_button = QPushButton("Start")
    editor.start_logger_button.clicked.connect(
        lambda: editor._run_logger_command("start")
    )
    editor.stop_logger_button = QPushButton("Stop")
    editor.stop_logger_button.clicked.connect(
        lambda: editor._run_logger_command("stop")
    )
    startup_title = QLabel("Startup:")
    startup_title.setStyleSheet("font-weight: bold;")
    editor.startup_status_label = QLabel("Checking...")
    editor.enable_startup_button = QPushButton("Enable")
    editor.enable_startup_button.clicked.connect(
        lambda: editor._run_startup_command(True)
    )
    editor.disable_startup_button = QPushButton("Disable")
    editor.disable_startup_button.clicked.connect(
        lambda: editor._run_startup_command(False)
    )

    message_row = QHBoxLayout()
    message_label = QLabel("Messages:")
    message_label.setStyleSheet("font-weight: bold;")
    message_row.addWidget(message_label)
    message_row.addWidget(editor.logger_message_area, 1)
    layout.addLayout(message_row)

    actions = QHBoxLayout()
    actions.addWidget(logger_title)
    actions.addWidget(editor.logger_status_label)
    actions.addWidget(editor.start_logger_button)
    actions.addWidget(editor.stop_logger_button)
    actions.addSpacing(8)
    actions.addWidget(startup_title)
    actions.addWidget(editor.startup_status_label)
    actions.addWidget(editor.enable_startup_button)
    actions.addWidget(editor.disable_startup_button)
    actions.addSpacing(12)
    editor.status_label = QLabel()
    actions.addWidget(editor.status_label)
    actions.addStretch()
    reload_button = QPushButton("Reload")
    reload_button.clicked.connect(editor.load_config)
    save_button = QPushButton("Save")
    save_button.setDefault(True)
    save_button.clicked.connect(editor.save_config)
    close_button = QPushButton("Close")
    close_button.clicked.connect(editor.close)
    actions.addWidget(reload_button)
    actions.addWidget(save_button)
    actions.addWidget(close_button)
    layout.addLayout(actions)
    editor.setCentralWidget(central)
