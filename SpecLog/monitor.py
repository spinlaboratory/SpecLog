"""
Monitor.py: plotting data in real-time or static

1. Read log files
2. Plot live or static data
3. Show warning information

It use PySide 6, there are some terms you need to know before modifying this script

1. 'name': the identification of a curve, and the key word to call the curve line and item. It can be the alias if the alias presents
2. 'item': the curve items, e.g Legend class from PySide 6
3. 'line': the data line for plotting, it is a class from PySide 6

Author: Yen-Chun Huang

Company: Bruker BioSpin
"""

import os
import csv
import math
from pathlib import Path
import re
import threading
import time as _time
from datetime import datetime, timezone
import numpy as _np
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QCheckBox,
    QPushButton,
    QSizePolicy,
)
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg 
import pyqtgraph.exporters as pg_exporters
from .ui.plotting import Ui_MainWindow
from .ui.historical_data import Ui_HistoricalDataWindow
from .loggerConfig import *
from .debugLog import *
from .logger_status import has_recent_log_activity, is_logger_running
from .history import HistoryCache
from .monitor_style import (
    attach_readable_legend,
    load_monitor_style,
    make_curve_pens,
    update_legend_columns,
)

red = "QCheckBox::indicator {\nwidth:10px;\nheight:10px;\nborder-radius:7px;\n}\n\nQCheckBox::indicator:unchecked {\nbackground-color:red;\nborder:2px solid white;\n}\n"
green = "QCheckBox::indicator {\nwidth:10px;\nheight:10px;\nborder-radius:7px;\n}\n\nQCheckBox::indicator:unchecked {\nbackground-color:green;\nborder:2px solid white;\n}\n"


class MonitorDateAxisItem(pg.DateAxisItem):
    """Adaptive date axis whose time labels always retain the date."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # DateAxisItem estimates density from short, time-only examples. Our
        # two-line labels are wider, so use their real worst-case footprint.
        for zoom_level in self.zoomLevels.values():
            zoom_level.exampleText = "2026-08-05\n23:59"
        # Permit centered labels near the left and right edges to extend into
        # the plot margins instead of suppressing both labels on narrow views.
        self.setStyle(hideOverlappingLabels=70)

    def tickStrings(self, values, scale, spacing):
        labels = []
        for value in values:
            try:
                date_time = datetime.fromtimestamp(value, timezone.utc)
                if spacing < 1:
                    label = date_time.strftime("%Y-%m-%d\n%H:%M:%S.%f")[:-3]
                elif spacing < 60:
                    label = date_time.strftime("%Y-%m-%d\n%H:%M:%S")
                elif spacing < 24 * 60 * 60:
                    label = date_time.strftime("%Y-%m-%d\n%H:%M")
                else:
                    label = date_time.strftime("%Y-%m-%d")
            except (OverflowError, OSError, ValueError):
                label = ""
            labels.append(label)
        return labels

    def tickValues(self, minVal, maxVal, size):
        levels = super().tickValues(minVal, maxVal, size)
        if any(values for _spacing, values in levels) or maxVal <= minVal:
            return levels
        # PyQtGraph may return no ticks when a narrow axis cannot fit its
        # preferred calendar interval. Always retain one centered reference.
        spacing = maxVal - minVal
        return [(spacing, [(minVal + maxVal) / 2])]


class TimeOnlyAxisItem(MonitorDateAxisItem):
    """Historical-window axis; the date range is displayed in the title."""

    def tickStrings(self, values, scale, spacing):
        labels = []
        for value in values:
            try:
                date_time = datetime.fromtimestamp(value, timezone.utc)
                label = date_time.strftime(
                    "%H:%M:%S" if spacing < 60 else "%H:%M"
                )
            except (OverflowError, OSError, ValueError):
                label = ""
            labels.append(label)
        return labels

    def tickValues(self, minVal, maxVal, size):
        """Use uniform clock intervals instead of calendar-day boundaries."""
        span = maxVal - minVal
        if span <= 0:
            return []
        target_ticks = max(4, min(10, int(size / 90)))
        desired = span / target_ticks
        intervals = [
            1,
            2,
            5,
            10,
            15,
            30,
            60,
            2 * 60,
            5 * 60,
            10 * 60,
            15 * 60,
            30 * 60,
            60 * 60,
            2 * 60 * 60,
            3 * 60 * 60,
            6 * 60 * 60,
            12 * 60 * 60,
            24 * 60 * 60,
        ]
        spacing = next(
            (interval for interval in intervals if interval >= desired),
            intervals[-1] * math.ceil(desired / intervals[-1]),
        )
        first = math.ceil(minVal / spacing) * spacing
        count = max(0, math.floor((maxVal - first) / spacing) + 1)
        values = [first + index * spacing for index in range(count)]
        return [(spacing, values)]


def set_historical_plot_title(plot_widget, start_text, end_text):
    """Set a centered two-line title with enough layout height."""
    title = (
        '<table cellspacing="0" cellpadding="0">'
        '<tr><td align="center" style="font-size:18pt;font-weight:600">'
        "SpecLog</td></tr>"
        '<tr><td align="center" style="font-size:14pt">'
        f"{start_text} - {end_text}</td></tr>"
        "</table>"
    )
    plot_widget.setTitle(title)
    title_label = plot_widget.plotItem.titleLabel
    title_label.setAttr("justify", "center")
    cursor = pg.QtGui.QTextCursor(title_label.item.document())
    cursor.select(pg.QtGui.QTextCursor.SelectionType.Document)
    block_format = pg.QtGui.QTextBlockFormat()
    block_format.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
    cursor.mergeBlockFormat(block_format)
    title_height = 64
    title_label.setMaximumHeight(title_height)
    plot_widget.plotItem.layout.setRowFixedHeight(0, title_height)
    title_label.resizeEvent(None)


class HistoricalDataWindow(QMainWindow, Ui_HistoricalDataWindow):
    """Non-modal historical plot that leaves the main monitor live."""

    historyLoaded = QtCore.Signal(object)
    historyFailed = QtCore.Signal(object)

    def __init__(self, monitor):
        super().__init__(monitor)
        self.monitor = monitor
        self._loading = False
        self._request_id = 0
        self._last_data = None
        self.setupUi(self)
        self.refresh_items()
        self._setup_plot()
        self.okButton.clicked.connect(self.load_selection)
        self.resetButton.clicked.connect(self.reset_selection)
        self.loadFileButton.clicked.connect(self.load_file)
        self.saveButton.clicked.connect(self.save_data)
        self.saveFigureButton.clicked.connect(self.save_figure)
        self.itemList.itemChanged.connect(self.update_selected_curves)
        self.historyLoaded.connect(self._history_loaded)
        self.historyFailed.connect(self._history_failed)

    def refresh_items(self):
        names = [
            name
            for name in self.monitor.all_names
            if name not in {"Date", "Time", "Seconds"}
            and name not in self.monitor.ignore_list
        ]
        self.set_plot_items(names, self.monitor.shown_list)

    def _setup_plot(self):
        axis = TimeOnlyAxisItem(orientation="bottom", utcOffset=0)
        self.graphWidget.setAxisItems({"bottom": axis})
        self.graphWidget.setBackground("w")
        self.graphWidget.showGrid(x=True, y=True)
        self.legend = attach_readable_legend(self.graphWidget)
        self._history_lines = {}
        bottom = self.graphWidget.getAxis("bottom")
        bottom.setStyle(
            tickFont=pg.QtGui.QFont("Arial", 10),
            tickTextOffset=6,
            tickTextHeight=24,
            autoExpandTextSpace=False,
        )
        bottom.setHeight(40)
        self.graphWidget.getAxis("left").setStyle(
            tickFont=pg.QtGui.QFont("Arial", 10)
        )

    def reset_selection(self):
        self._request_id += 1
        self._loading = False
        self.okButton.setEnabled(True)
        self.saveButton.setEnabled(False)
        self.saveFigureButton.setEnabled(False)
        self.startTime.clear()
        self.durationValue.setValue(0)
        self.durationUnit.setCurrentIndex(0)
        self.statusLabel.clear()
        self.graphWidget.clear()
        self.graphWidget.setTitle("")
        self.legend.clear()
        self._history_lines.clear()
        self._last_data = None

    def load_selection(self):
        if self._loading:
            return
        start = self.monitor.returnSeconds(self.startTime.text().strip())
        duration = self.durationValue.value()
        if start is False:
            self._show_error("Start Time is not valid.")
            return
        if start is None and duration > 0:
            self._show_error("Start Time is required when Duration is not All.")
            return
        selected_items = self.selected_plot_items()
        if not selected_items:
            self._show_error("Select at least one item to plot.")
            return
        multiplier = 24 * 60 * 60 if self.durationUnit.currentText() == "Days" else 60 * 60
        end = start + duration * multiplier if start is not None and duration > 0 else None
        self._loading = True
        self.okButton.setEnabled(False)
        self.statusLabel.setStyleSheet("")
        self.statusLabel.setText("Loading historical data...")
        max_points = max(1000, self.graphWidget.width() * 2)
        self._request_id += 1
        request_id = self._request_id
        thread = threading.Thread(
            target=self._load_history,
            args=(request_id, start, end, max_points),
            daemon=True,
        )
        thread.start()

    def _load_history(self, request_id, start, end, max_points):
        try:
            all_files = sorted(Path(self.monitor.file_dir).glob("log_*.csv"))
            self.monitor.history_cache.prune(all_files)
            files = []
            for path in all_files:
                try:
                    day = datetime.strptime(path.name, "log_%Y%m%d.csv")
                except ValueError:
                    continue
                day_start = int((day - datetime(1970, 1, 1)).total_seconds())
                day_end = day_start + 24 * 60 * 60 - 1
                if start is not None and day_end < start:
                    continue
                if end is not None and day_start > end:
                    continue
                files.append(path)
            self.monitor.history_cache.sync(files)
            rows = self.monitor.history_cache.query(
                start, end, max_points=max_points
            )
            self.historyLoaded.emit(
                (request_id, self.monitor._history_rows_to_data(rows))
            )
        except Exception as error:
            self.monitor.debugLogger.exception("Historical data loading failed")
            self.historyFailed.emit((request_id, str(error)))

    def _history_loaded(self, result):
        request_id, data = result
        if request_id != self._request_id:
            return
        self._loading = False
        self.okButton.setEnabled(True)
        if not data["Seconds"]:
            self._show_error("No logged data was found in the selected range.")
            return
        self._last_data = data
        self.saveButton.setEnabled(True)
        self.saveFigureButton.setEnabled(True)
        self.update_selected_curves()

    def update_selected_curves(self):
        data = self._last_data
        if not data or not data.get("Seconds"):
            return
        start_text = datetime.fromtimestamp(
            data["Seconds"][0], timezone.utc
        ).strftime("%Y-%m-%d %H:%M")
        end_text = datetime.fromtimestamp(
            data["Seconds"][-1], timezone.utc
        ).strftime("%Y-%m-%d %H:%M")
        set_historical_plot_title(
            self.graphWidget, start_text, end_text
        )
        plotted = 0
        selected_names = self.selected_plot_items()
        selected_pens = make_curve_pens(
            selected_names, self.monitor.monitor_style
        )
        legend_before = tuple(label.text for _sample, label in self.legend.items)
        selected_set = set(selected_names)
        for name in tuple(self._history_lines):
            if name not in selected_set:
                line = self._history_lines.pop(name)
                self.legend.removeItem(line)
                self.graphWidget.removeItem(line)
        for name in selected_names:
            values = data.get(name)
            if values is None:
                continue
            try:
                numeric_values = _np.asarray(values, dtype=float)
                if len(numeric_values) != len(data["Seconds"]):
                    continue
            except (TypeError, ValueError):
                continue
            line = self._history_lines.get(name)
            if line is None:
                line = self.graphWidget.plot(name=name)
                self._history_lines[name] = line
                self.legend.addItem(line, name)
            line.setPen(selected_pens[name])
            line.setData(data["Seconds"], numeric_values)
            plotted += 1
        legend_after = tuple(label.text for _sample, label in self.legend.items)
        update_legend_columns(
            self.legend,
            plotted,
            force=legend_after != legend_before,
        )
        # Historical data is a newly selected fixed range. Always fit it after
        # OK, even if a previous zoom or pan disabled automatic ranging.
        self.graphWidget.enableAutoRange()
        self.graphWidget.autoRange()
        self.statusLabel.setStyleSheet("")
        if plotted:
            self.statusLabel.setText(
                f"Loaded {len(data['Seconds'])} points across {plotted} curves."
            )
        else:
            self.statusLabel.setText("Select at least one item to plot.")

    def save_data(self):
        data = self._last_data
        if not data or not data.get("Seconds"):
            self._show_error("Load a time range before saving data.")
            return
        names = [name for name in self.selected_plot_items() if name in data]
        if not names:
            self._show_error("Select at least one item to save.")
            return
        start_name = datetime.fromtimestamp(
            data["Seconds"][0], timezone.utc
        ).strftime("%Y%m%d%H%M")
        end_name = datetime.fromtimestamp(
            data["Seconds"][-1], timezone.utc
        ).strftime("%Y%m%d%H%M")
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save selected data",
            f"log_{start_name}-{end_name}.csv",
            "CSV files (*.csv)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".csv"):
            filename += ".csv"
        try:
            with open(filename, "w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Date", "Time", *names])
                for index in range(len(data["Seconds"])):
                    writer.writerow(
                        [
                            data["Date"][index],
                            data["Time"][index],
                            *(data[name][index] for name in names),
                        ]
                    )
        except (OSError, IndexError) as error:
            self._show_error(f"Could not save data: {error}")
            return
        self.statusLabel.setStyleSheet("")
        self.statusLabel.setText(f"Saved data: {Path(filename).name}")
        self.statusLabel.setToolTip(str(Path(filename)))

    def save_figure(self):
        if not self._last_data or not self.graphWidget.listDataItems():
            self._show_error("Plot at least one item before saving the figure.")
            return
        start_name = datetime.fromtimestamp(
            self._last_data["Seconds"][0], timezone.utc
        ).strftime("%Y%m%d%H%M")
        end_name = datetime.fromtimestamp(
            self._last_data["Seconds"][-1], timezone.utc
        ).strftime("%Y%m%d%H%M")
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save historical figure",
            f"log_{start_name}-{end_name}.png",
            "PNG images (*.png)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".png"):
            filename += ".png"
        export_graph = None
        try:
            # Render an independent plot. Exporting or grabbing the live
            # QGraphicsScene can resolve new minimum sizes and resize its
            # parent window, even if no item properties are changed directly.
            export_axis = TimeOnlyAxisItem(orientation="bottom", utcOffset=0)
            export_graph = pg.PlotWidget(axisItems={"bottom": export_axis})
            export_graph.resize(self.graphWidget.size())
            export_graph.setBackground("w")
            export_graph.showGrid(x=True, y=True)
            export_legend = attach_readable_legend(export_graph)
            export_graph.getAxis("bottom").setStyle(
                tickFont=pg.QtGui.QFont("Arial", 10),
                tickTextOffset=6,
                tickTextHeight=24,
                autoExpandTextSpace=False,
            )
            export_graph.getAxis("bottom").setHeight(40)
            export_graph.getAxis("left").setStyle(
                tickFont=pg.QtGui.QFont("Arial", 10)
            )
            export_start_text = datetime.fromtimestamp(
                self._last_data["Seconds"][0], timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            export_end_text = datetime.fromtimestamp(
                self._last_data["Seconds"][-1], timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            set_historical_plot_title(
                export_graph, export_start_text, export_end_text
            )

            selected_names = self.selected_plot_items()
            selected_pens = make_curve_pens(
                selected_names, self.monitor.monitor_style
            )
            plotted = 0
            for name in selected_names:
                try:
                    values = _np.asarray(self._last_data[name], dtype=float)
                except (KeyError, TypeError, ValueError):
                    continue
                line = export_graph.plot(
                    self._last_data["Seconds"],
                    values,
                    pen=selected_pens[name],
                )
                export_legend.addItem(line, name)
                plotted += 1
            update_legend_columns(export_legend, plotted, force=True)
            export_graph.autoRange()
            export_graph.plotItem.layout.activate()

            exporter = pg_exporters.ImageExporter(export_graph.plotItem)
            exporter.parameters()["width"] = max(
                1200, max(1, self.graphWidget.width()) * 2
            )
            ignore_transforms = (
                export_legend.GraphicsItemFlag.ItemIgnoresTransformations
            )
            export_legend.setFlag(ignore_transforms, False)
            image = exporter.export(toBytes=True)
            padding = max(20, round(image.width() * 0.015))
            padded_image = pg.QtGui.QImage(
                image.width() + 2 * padding,
                image.height() + 2 * padding,
                image.format(),
            )
            padded_image.fill(pg.QtGui.QColor("white"))
            painter = pg.QtGui.QPainter(padded_image)
            painter.drawImage(padding, padding, image)
            painter.end()
            if not padded_image.save(filename):
                raise OSError("The image encoder could not save the figure.")
        except Exception as error:
            self._show_error(f"Could not save figure: {error}")
            return
        finally:
            if export_graph is not None:
                export_graph.close()
                export_graph.deleteLater()
        self.statusLabel.setStyleSheet("")
        self.statusLabel.setText(f"Saved figure: {Path(filename).name}")
        self.statusLabel.setToolTip(str(Path(filename)))

    def load_file(self):
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Load SpecLog data",
            self.monitor.file_dir,
            "CSV files (*.csv)",
        )
        if not filename:
            return
        try:
            with open(filename, "r", newline="", encoding="utf-8-sig") as stream:
                reader = csv.reader(stream)
                headers = next(reader, None)
                if not headers:
                    raise ValueError("The selected file is empty.")
                headers = self.monitor.convertNames(
                    [header.strip() for header in headers]
                )
                data = {name: [] for name in headers}
                data.setdefault("Date", [])
                data.setdefault("Time", [])
                data["Seconds"] = []
                for row in reader:
                    values = {
                        name: value.strip()
                        for name, value in zip(headers, row)
                    }
                    date_text = values.get("Date")
                    time_text = values.get("Time")
                    if not date_text or not time_text:
                        continue
                    try:
                        seconds = self.monitor.getXAxisFromTime(
                            date_text, time_text
                        )
                    except ValueError:
                        continue
                    data["Date"].append(date_text)
                    data["Time"].append(time_text)
                    data["Seconds"].append(seconds)
                    for name in headers:
                        if name in {"Date", "Time", "Seconds"}:
                            continue
                        value = values.get(name, "nan")
                        try:
                            data[name].append(float(value))
                        except (TypeError, ValueError):
                            data[name].append(_np.nan)
        except (OSError, ValueError) as error:
            self._show_error(f"Could not load data: {error}")
            return
        if not data["Seconds"]:
            self._show_error("The selected file contains no valid data.")
            return

        available = [
            name
            for name in data
            if name not in {"Date", "Time", "Seconds"}
        ]
        current = self.selected_plot_items()
        selected = [name for name in current if name in available]
        if not selected:
            selected = available
        self.set_plot_items(available, selected)
        self._request_id += 1
        self._loading = False
        self.okButton.setEnabled(True)
        self._last_data = data
        self.saveButton.setEnabled(True)
        self.saveFigureButton.setEnabled(True)
        self.update_selected_curves()
        self.statusLabel.setText(
            f"Loaded {len(data['Seconds'])} points from {Path(filename).name}."
        )

    def _history_failed(self, result):
        request_id, message = result
        if request_id != self._request_id:
            return
        self._loading = False
        self.okButton.setEnabled(True)
        self._show_error(f"Historical data could not be loaded: {message}")

    def _show_error(self, message):
        self.statusLabel.setStyleSheet("color: red;")
        self.statusLabel.setText(message)


class MainWindow(QMainWindow, Ui_MainWindow):
    historyLoaded = QtCore.Signal(object)
    historyFailed = QtCore.Signal(str)

    def __init__(self, config_file: str = None, number_of_files: int = 10):
        super().__init__()
        self.setupUi(self)
        self.groupBox_4.setTitle("Monitor Messages")
        self.groupBox_6.setTitle("Device Status")
        self.groupBox_3.setTitle("System Status")
        self.systemStatus.setText("Overall")
        self._configure_monitor_items_ui()
        self.groupBox_4.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.groupBox_3.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.gridLayout_2.setColumnStretch(1, 1)
        self.gridLayout_2.setColumnStretch(2, 1)
        self.groupBox.hide()
        self.groupBox_5.setTitle("Plot Controls")
        self.groupBox_5.setMinimumHeight(84)
        self.groupBox_5.setMaximumHeight(84)
        self.historicalDataButton = QPushButton(
            "Historical Data", self.groupBox_5
        )
        self.gridLayout_4.addWidget(self.historicalDataButton, 1, 0, 1, 2)
        self.historical_data_window = None

        # configuration file
        config = loggerConfig(config_file)
        self.settings = config.settings
        self.limit_hours = int(self.settings['limit_hours'])
        self.log_interval = max(1, int(self.settings["log_interval"]))
        self.device_config = config.devices
        self.file_dir = self.settings["log_folder_location"] + "/LOG/"
        self.commands = config.commands
        self.monitor_style = load_monitor_style()
        self._main_curve_style_slot = {}
        self._main_curve_pen = {}
        self.number_of_files = max(1, number_of_files)
        os.makedirs(self.file_dir, exist_ok=True)
        self.current_file = None
        self.f = None
        self.names = []
        self.latest_data = None
        self._logger_running = False
        self._last_process_check = 0.0
        self._history_loading = False
        self.history_cache = HistoryCache(
            os.path.join(self.file_dir, "monitor_cache.sqlite")
        )
        self.historyLoaded.connect(self._history_loaded)
        self.historyFailed.connect(self._history_failed)
        self.getAlias()
        self.getCommandInfoByName()
        self.status_string = ""

        # debug log
        self.debugLogger = debugLog(config_file).logger

        # get files from directionary
        self.getFiles()
        self.getData()
        self.setWarningLevelByName()
        self.getPenByName()
        self.getLine()  # initialize plot

        # Shown items
        if not self.loadDisplaySettings():
            self.saveDisplaySettings()  # initial saving

        self._populate_monitor_items()

        # Status Indicator
        self.setLEDIndicator()
        self.setStatus()

        # Buttons and Menu settings
        self.shownListWidget.itemChanged.connect(self._monitor_item_changed)
        self.clearWarningText.clicked.connect(
            self.clearWarning
        )  # button to clear warning message
        self.setPlotType()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.updateFiles)
        self.timer.timeout.connect(self.updateData)
        self.timer.timeout.connect(self.setStatus)
        self.timer.timeout.connect(self.printWarning)
        self.timer.timeout.connect(self.plot)
        self.timer.start()

    def _configure_monitor_items_ui(self):
        """Replace the legacy shown/hidden lists with one checkbox list."""
        for widget in (
            self.hiddenListWidget,
            self.Shown,
            self.Hidden,
            self.hiddenToShown,
            self.shownToHidden,
        ):
            self.gridLayout.removeWidget(widget)
            widget.hide()
        self.gridLayout.removeWidget(self.shownListWidget)
        self.shownListWidget.setMinimumSize(0, 0)
        self.shownListWidget.setMaximumSize(16777215, 16777215)
        self.shownListWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        self.gridLayout.addWidget(self.shownListWidget, 0, 0, 5, 3)
        self.groupBox_2.setTitle("Monitor Items")

    def _populate_monitor_items(self):
        """Populate main-plot choices using the Data Selection checkbox style."""
        self.shownListWidget.blockSignals(True)
        self.shownListWidget.clear()
        shown = set(self.shown_list)
        for name in self.all_names:
            if name in self.ignore_list:
                continue
            item = QtWidgets.QListWidgetItem(name)
            item.setFlags(
                item.flags()
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if name in shown
                else QtCore.Qt.CheckState.Unchecked
            )
            item.setForeground(pg.mkColor("black"))
            self.shownListWidget.addItem(item)
        self.shownListWidget.blockSignals(False)

    def _monitor_item_changed(self, _item):
        shown = []
        hidden = []
        for index in range(self.shownListWidget.count()):
            item = self.shownListWidget.item(index)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                shown.append(item.text())
            else:
                hidden.append(item.text())
        self.shown_list = shown
        self.hidden_list = hidden
        self.saveDisplaySettings()
        # Apply curves and legend as one visual update. Otherwise the timer can
        # paint the temporary layout left by removing a legend entry.
        self.graphWidget.setUpdatesEnabled(False)
        try:
            self.plot()
            self.graphWidget.plotItem.layout.activate()
        finally:
            self.graphWidget.setUpdatesEnabled(True)
            self.graphWidget.viewport().update()

    ### ======================================================= Log Data Files  =======================================================
    def getFiles(self):
        """
        Get files from directory
        """
        self.all_file_list = sorted(
            file
            for file in os.listdir(self.file_dir)
            if file.startswith("log_") and file.endswith(".csv")
        )
        self.file_list = self.all_file_list[-self.number_of_files :]
        return True

    def updateFiles(self):
        """
        update files from directory
        """
        files = sorted(
            file
            for file in os.listdir(self.file_dir)
            if file.startswith("log_") and file.endswith(".csv")
        )
        if files == self.all_file_list:
            return False

        self.all_file_list = files
        self.file_list = files[-self.number_of_files :]
        self.getData()
        self.getPenByName()
        for name in self.all_names:
            if name not in self.line_by_name:
                self.line_by_name[name] = self.graphWidget.plot(
                    [], [], name=name, pen=self.pen_by_name[name]
                )
            if name not in self.warning_level_by_name:
                self.warning_level_by_name[name] = 0
            if (
                name not in self.hidden_list
                and name not in self.shown_list
                and name not in self.ignore_list
            ):
                if self.command_info_by_name.get(name, [None] * 4)[3]:
                    self.ignore_list.append(name)
                else:
                    self.hidden_list.append(name)
                    self._populate_monitor_items()
        return True

    ### ======================================================= Data Dictionary =======================================================
    def getData(self):
        """
        Get data from logger files when monitor starts. It is not used for updating data reading
        """
        self.all_data_by_name = {"Date": [], "Time": [], "Seconds": []}
        self.latest_data = None
        window_length = self.windowLength.value()

        if not self.file_list:
            if self.f is not None:
                self.f.close()
            self.f = None
            self.current_file = None
            self.names = []
            self.all_names = []
            self.all_x = self.all_data_by_name["Seconds"]
            self.data_by_name = {}
            self.x = []
            self.window_length = window_length
            self.debugLogger.warning("Logged data not found; waiting for logger")
            return True

        if self.f is not None:
            self.f.close()
            self.f = None

        # When the monitor starts or a new file presents
        for file in self.file_list:
            f = open(os.path.join(self.file_dir, file), "r", newline="")
            names = f.readline().strip("\n").split(",")
            if names[0]:
                names = self.convertNames(
                    names
                )  # at this point, the name is used locally
                for data in csv.reader(f, delimiter=","):
                    self.all_data_by_name = self.updateDataToDict(
                        names, data, self.all_data_by_name, self.limit_hours
                    )

            if file != self.file_list[-1]:  # close the file
                f.close()
            else:  # leave the current file open for further reading
                # after reading all data, put the local names list to global
                self.current_file = file
                self.f = f
                self.names = names
                self.window_length = window_length

            # for initial data dictionary
            self.all_names = [
                name
                for name in self.all_data_by_name.keys()
                if name not in ["Date", "Time", "Seconds"]
            ]  # get list of data name except Date, Time and Seconds
            self.all_x = self.all_data_by_name["Seconds"]
            self.data_by_name = {
                name: val[-1 * window_length :]
                for name, val in self.all_data_by_name.items()
                if name not in ["Date", "Time", "Seconds"]
            }
            self.x = self.all_x[-1 * window_length :]

    def updateData(self):
        """
        Update data when new line appears or new file presents

        This is the data checking processing and used for live data
        """

        if not self.file_list or self.f is None:
            return False

        if self.current_file != self.file_list[-1]:
            self.f.close()  # when new file exist, close the previous file
            self.current_file = self.file_list[-1]
            self.f = open(os.path.join(self.file_dir, self.current_file), "r", newline="")
            self.names = self.f.readline().strip("\n").split(",")
            self.names = self.convertNames(self.names)  # convert names list from alias

        self.line = self.f.readline().strip("\n")
        if self.line:
            self.all_data_by_name = self.updateDataToDict(
                self.names, self.line.strip("\n").split(",") , self.all_data_by_name, self.limit_hours
            )
            # self.all_x doesn't need to be updated because it is the reference to self.all_data_by_name['Seconds']

        if self.plot_type:
            self.livePlot()

        else:
            self.staticPlot()

    def livePlot(self):
        """
        Choose to plot data in live
        it is always updating

        Modification Suggestions: might add a condition: '# if self.window_length != window_length or self.line or [change_from_static_to_live]:'

        """
        window_length = self.windowLength.value()
        if self.window_length != window_length:
            self.saveDisplaySettings()  # update the window length
        self.window_length = window_length
        self.data_by_name = {
            name: val[-1 * window_length :]
            for name, val in self.all_data_by_name.items()
            if name not in ["Date", "Time"]
        }
        self.x = self.all_x[-1 * window_length :]

        return self.plot_type

    def staticPlot(self):
        if self.static_update_request:
            if self.selected_data_by_date:
                if (
                    self.time_is_valid
                ):  # only update plot when time is valid, 'OK' button is pressed, and file is not selected
                    index = self.static_index
                    self.data_by_name = {
                        name: val[index[0] : index[1]]
                        for name, val in self.all_data_by_name.items()
                        if name not in ["Date", "Time"]
                    }
                    self.x = self.all_x[index[0] : index[1]]
                    self.static_update_request = (
                        False  # just update the static figure once
                    )

            elif (
                self.selected_data_by_file
            ):  # only update when time when 'OK' button is pressed and file is selected
                self.data_by_name = {
                    name: val
                    for name, val in self.temp_data_by_name.items()
                    if name not in ["Date", "Time"]
                }
                self.x = self.temp_data_by_name["Seconds"]
                self.static_update_request = False  # just update the static figure once

        return self.plot_type

    def updateDataToDict(self, names: list, data, d: dict, hours: int = 0):
        """
        Add data to target dictionary based on name

        Args:
            names (list): list of key (name) to add to target dictionary
            data: csv read data
            d (dict): target dictionary to add data
            hours (int): the limited hours saved in this dictionary, greater than 0 means no hour limit

        Return:
            d (dict): target dictionary with added data
        """

        # convert name from alias:
        # temporary dictionary
        td = {name.strip(): val.strip() for name, val in zip(names, data)}
        if "Date" not in td or "Time" not in td:
            self.debugLogger.warning("Ignoring incomplete log row: %r", data)
            return d

        # remove the overtime data if necessary
        # if hours > 0:
        #     if d['Seconds'] != []:
        #         # print(td)
        #         while self.getXAxisFromTime(td["Date"].strip(), td["Time"].strip()) - d['Seconds'][0] > hours * 60 * 60:
        #             for name, value in d.items():
        #                 value.pop(0)
                
        # create empty list if key not exists in dictionary
        for name in td.keys():
            if name not in d.keys():
                d[name] = [_np.nan] * len(d["Date"])

        for name in d.keys():
            if name in ["Date", "Time"]:
                td[name] = td[name].strip()
            elif name == "Seconds":
                td[name] = self.getXAxisFromTime(td["Date"].strip(), td["Time"].strip())
            elif name in td and td[name] != "nan":
                try:
                    if self.command_info_by_name.get(name, [None] * 4)[3]:
                        td[name] = str(td[name])
                    else:
                        td[name] = float(td[name])
                except (TypeError, ValueError):
                    td[name] = _np.nan
            elif name:
                td[name] = _np.nan
            
            d[name].append(td[name])
        self.latest_data = td

        return d

    ### ======================================================= X-axis Processing =======================================================
    def getXAxisFromTime(self, date: str, time: str):
        """
        Convert Date and Time string to the seconds from 1970/1/1

        Use seconds as X axis

        Args:
            date (str): in format %Y-%m-%d
            time (str): in format %H:%M:%S

        Returns:
            seconds (int): seconds from 1970/1/1
        """

        string = date + " " + time  # in format '%Y-%m-%d %H:%M:%S'
        datetime_object = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
        delta = datetime_object - datetime(1970, 1, 1)

        return int(delta.total_seconds())

    def getLine(self):
        """
        Initialize plotting and get line based on name
        """
        self.date_axis = MonitorDateAxisItem(
            orientation="bottom", utcOffset=0
        )
        self.graphWidget.setAxisItems({"bottom": self.date_axis})
        self.line_by_name = {}  # {name: line}
        for name, data in self.data_by_name.items():  # loop all names
            pen = self.pen_by_name[name]  # set pen
            self.line_by_name[name] = self.graphWidget.plot(
                [], [], name=name, pen=pen
            )  # initialize data plotting and get line for each name

        self.graphWidget.setBackground("w")
        self.graphWidget.showGrid(x=True, y=True)
        self.legend = attach_readable_legend(self.graphWidget)
        self.ax = self.graphWidget.getAxis("bottom")
        self.ax.setStyle(
            tickFont=pg.QtGui.QFont("Arial", 10),
            tickTextOffset=6,
            tickTextHeight=42,
            autoExpandTextSpace=False,
        )
        # Date/time ticks use two lines, while DateAxisItem normally reserves
        # space based on its original single-line examples.
        self.ax.setHeight(52)
        self.graphWidget.getAxis("left").setStyle(
            tickFont=pg.QtGui.QFont("Arial", 10)
        )
    
        return True

    ### ======================================================= Drawing Pen =======================================================
    def getPenByName(self):
        """
        Set curve color and line style to pen

        Idea: loop color list. If color is the same, use different dash line
        1. loop the color list. e.g. 1%4 = 1 and 5%4 = 1, so the second and fifth element use the same color
        2. loop the dash list. e.g. 1//4%4 = 0 and 5//4%4 = 1, so the second element doesn't have dash line but fifth element use dash line [16, 16]

        """
        self.pen_by_name = {}  # {name: pen}
        self.pen_by_name.update(
            make_curve_pens(self.all_names, self.monitor_style)
        )

        return True

    ### ================================================ Set Static or Live plot ===============================================
    def setPlotType(self):
        """
        The setToStatic button will set the static plot
        The setToLive button will set the live plot
        By default, the plot is live
        """
        self.plot_type = True  # plot is live
        self.historicalDataButton.clicked.connect(self.openHistoricalData)
        # Historical files are loaded from the Historical Data window so the main
        # graph always remains a live plot.
        self.menuFile.menuAction().setVisible(False)

    def openHistoricalData(self):
        if self.historical_data_window is None:
            self.historical_data_window = HistoricalDataWindow(self)
        else:
            self.historical_data_window.refresh_items()
        self.historical_data_window.show()
        self.historical_data_window.raise_()
        self.historical_data_window.activateWindow()

    def setStatic(self):
        """
        Set plot type to static if the input is valid, or give the error and set plot type back to live
        """
        self.getSelectedDataRangeByDate()

    def setLive(self):
        self.plot_type = True
        self.selected_data_by_file = False
        self.selected_data_by_date = False
        self.static_update_request = False
        self.startTime.clear()
        self.durationValue.setValue(0)
        self.durationUnit.setCurrentIndex(0)
        self.statusbar.clearMessage()

    ### =============================================== Static Plot by File Name ===============================================
    def loadStaticFile(self):
        """
        Load file from menu bar
        """
        filename, ext = QFileDialog.getOpenFileName(
            caption="Import File", dir=self.file_dir, filter="*.csv"
        )
        if filename and "log_" in filename and '.csv' in filename:  # if a file is selected and file is valid
            try:
                self.temp_data_by_name = {"Date": [], "Time": [], "Seconds": []}
                with open(filename, "r", newline="") as f:
                    names = f.readline().strip("\n").split(",")
                    names = self.convertNames(names)
                    for data in csv.reader(f, delimiter=","):
                        self.temp_data_by_name = self.updateDataToDict(
                            names, data, self.temp_data_by_name
                        )
                if self.temp_data_by_name["Date"]:
                    self.plot_type = False
                    self.static_update_request = True
                    self.selected_data_by_file = True
                    self.selected_data_by_date = False

                    return True
                else:
                    self.warningText.appendPlainText("The selected file is empty.")

            except Exception:
                self.debugLogger.exception("Could not load static file %s", filename)
                self.warningText.appendPlainText(
                    "The selected file is invalid or compromised."
                )

        self.static_update_request = False
        self.selected_data_by_file = False
        return False

    ### ================================================= Static Plot by Date ==================================================
    def getSelectedDataRangeByDate(self):
        """
        Use formatted input dates to calculated the index range, and give the index for staticPlot function
        """
        self.time_is_valid = True  # initial True and force to False if input time is not valid. This value is used for making a new static plot

        # Get the start time and calculate the end from the selected duration.

        # Value explains
        # False: the incorrect format that will give the warning message, and the plot will not be static until the input is correct
        # None: the not given value, eg. [1, None] means 1 s to the moment when user click ok and plot is static
        # seconds (int): the seconds converted from formatted input. eg. [500, 1500] means 500 s to 1500 s

        # The format is yyyymmddHHMM, where yyyy is complete year, mm is complete month, dd is complete day, HH is hour in 24 hour format, and MM is minutes
        # Hours and minutes are optional, the rest are required
        # If the Input and string 'yyyymmddHHMM' or empty, it will assign None to list

        start = self.returnSeconds(self.startTime.text().strip())
        duration = self.durationValue.value()
        if start is False:
            self.warningText.appendPlainText("Static input time is not valid")
            self.time_is_valid = False
            return False
        if start is None and duration > 0:
            self.warningText.appendPlainText(
                "Start Time is required when Duration is not All."
            )
            self.time_is_valid = False
            return False

        multiplier = 24 * 60 * 60 if self.durationUnit.currentText() == "Days" else 60 * 60
        end = start + duration * multiplier if start is not None and duration > 0 else None
        self.static_time_range = [start, end]

        if self.time_is_valid:
            start, end = self.static_time_range
            if start is not None and end is not None and start > end:
                self.warningText.appendPlainText(
                    "Static input time is not valid: end time should be later than start time"
                )
                self.time_is_valid = False
                return False
            if self._history_loading:
                return False

            self._history_loading = True
            self.statusbar.showMessage("Loading historical data…")
            max_points = max(1000, self.graphWidget.width() * 2)
            self._history_thread = threading.Thread(
                target=self._load_history,
                args=(start, end, max_points),
                daemon=True,
            )
            self._history_thread.start()
            return True

        return False

    def _history_file_paths(self, start, end):
        paths = []
        for filename in self.all_file_list:
            try:
                day = datetime.strptime(filename, "log_%Y%m%d.csv")
            except ValueError:
                continue
            day_start = int((day - datetime(1970, 1, 1)).total_seconds())
            day_end = day_start + 24 * 60 * 60 - 1
            if start is not None and day_end < start:
                continue
            if end is not None and day_start > end:
                continue
            paths.append(Path(self.file_dir) / filename)
        return paths

    def _load_history(self, start, end, max_points):
        try:
            all_files = [Path(self.file_dir) / name for name in self.all_file_list]
            self.history_cache.prune(all_files)
            files = self._history_file_paths(start, end)
            self.history_cache.sync(files)
            rows = self.history_cache.query(start, end, max_points=max_points)
            self.historyLoaded.emit(self._history_rows_to_data(rows))
        except Exception as error:
            self.debugLogger.exception("Historical data loading failed")
            self.historyFailed.emit(str(error))

    def _history_rows_to_data(self, rows):
        data = {"Date": [], "Time": [], "Seconds": []}
        for name in self.command_info_by_name:
            data[name] = []

        for timestamp, date_text, time_text, payload in rows:
            data["Date"].append(date_text)
            data["Time"].append(time_text)
            data["Seconds"].append(timestamp)
            aliased = {
                self.alias_by_name.get(name, name): value
                for name, value in payload.items()
                if name not in {"Date", "Time"}
            }
            for name in data:
                if name in {"Date", "Time", "Seconds"}:
                    continue
                value = aliased.get(name, "nan")
                if value == "nan":
                    data[name].append(_np.nan)
                elif self.command_info_by_name.get(name, [None] * 4)[3]:
                    data[name].append(str(value))
                else:
                    try:
                        data[name].append(float(value))
                    except (TypeError, ValueError):
                        data[name].append(_np.nan)
        return data

    def _history_loaded(self, data):
        self._history_loading = False
        self.statusbar.clearMessage()
        if not data["Seconds"]:
            self.warningText.appendPlainText(
                "No logged data was found in the selected range."
            )
            return
        self.temp_data_by_name = data
        self.plot_type = False
        self.static_update_request = True
        self.selected_data_by_file = True
        self.selected_data_by_date = False

    def _history_failed(self, message):
        self._history_loading = False
        self.statusbar.clearMessage()
        self.warningText.appendPlainText(
            f"Historical data could not be loaded: {message}"
        )

    def returnSeconds(self, time: str):
        """
        Check if a time string is valid in format yyyymmdd or yyyymmddHH or yyyymmddHHMM or empty and return seconds
        """

        # check empty
        if time == "yyyymmddHHMM" or not time:  # by default or not given
            return None

        # check length:
        if len(time) not in [
            len("yyyymmdd"),
            len("yyyymmddHH"),
            len("yyyymmddHHMM"),
        ]:  # incorrect length
            return False

        if len(time) == len("yyyymmdd"):
            try:
                datetime_object = datetime.strptime(time, "%Y%m%d")
            except ValueError:
                return False

        elif len(time) == len("yyyymmddHH"):
            try:
                datetime_object = datetime.strptime(time, "%Y%m%d%H")
            except ValueError:
                return False

        elif len(time) == len("yyyymmddHHMM"):
            try:
                datetime_object = datetime.strptime(time, "%Y%m%d%H%M")
            except ValueError:
                return False
        else:
            return False

        delta = datetime_object - datetime(1970, 1, 1)  # use 1970/1/1 as reference

        return int(delta.total_seconds())

    ### ======================================================= Plotting =======================================================
    def plot(self):
        """
        Plotting data
        """
        selected_pens = self._persistent_main_curve_pens()
        legend_before = tuple(label.text for _sample, label in self.legend.items)
        for name in self.all_names:
            if name in self.shown_list:  # plot line in shown widget
                self.line_by_name[name].setPen(selected_pens[name])
                if not self.legend.getLabel(
                    self.line_by_name[name]
                ):  # if not legend, add legend
                    self.legend.addItem(self.line_by_name[name], name)

                self.line_by_name[name].setData(self.x, self.data_by_name[name])
            else:  # hide line in hidden widget
                self.legend.removeItem(name)  # remove legend
                self.line_by_name[name].setData([], [])  # display empty line
        legend_after = tuple(label.text for _sample, label in self.legend.items)
        update_legend_columns(
            self.legend,
            len(legend_after),
            force=legend_after != legend_before,
        )

    def _persistent_main_curve_pens(self):
        """Keep each curve's style stable until that curve is unselected."""
        selected = set(self.shown_list)
        for name in tuple(self._main_curve_style_slot):
            if name not in selected:
                self._main_curve_style_slot.pop(name, None)
                self._main_curve_pen.pop(name, None)

        used_slots = set(self._main_curve_style_slot.values())
        for name in self.shown_list:
            if name in self._main_curve_style_slot:
                continue
            slot = 0
            while slot in used_slots:
                slot += 1
            slot_names = list(range(slot + 1))
            pen = make_curve_pens(slot_names, self.monitor_style)[slot]
            self._main_curve_style_slot[name] = slot
            self._main_curve_pen[name] = pen
            used_slots.add(slot)
        return self._main_curve_pen

    ### ======================================================= List Widget Interaction =======================================================
    def saveDisplaySettings(self):
        """
        This will save hidden and shown items and window length in the file called 'display_settings.txt'
        format:
        1st line: 'hidden[, item1][, item2]....'
        2nd line: 'shown[, item3][, item4]....'
        3rd line: 'window length,[window_length]'
        """

        hidden_list = ["hidden"]
        hidden_list.extend(self.hidden_list)
        hidden_string = ",".join(hidden_list) + "\n"
        shown_list = ["shown"]
        shown_list.extend(self.shown_list)
        shown_string = ",".join(shown_list) + "\n"
        ingnore_list = ["ignore"]
        ingnore_list.extend(self.ignore_list)
        ignore_string = ",".join(ingnore_list) + "\n"
        window_length_string = "window length," + self.windowLength.text()
        with open(
            os.path.join(self.file_dir, "display_settings.txt"), "w"
        ) as f:
            f.write(hidden_string + shown_string + ignore_string + window_length_string)

        return True

    def loadDisplaySettings(self):
        """
        This will load hidden item and shown item settings
        return True if loading successfully, else False
        """

        self.hidden_list = []
        self.shown_list = []
        self.ignore_list =[]
        if "display_settings.txt" in os.listdir(self.file_dir):
            try:
                with open(
                    os.path.join(self.file_dir, "display_settings.txt"), "r"
                ) as f:
                    hidden_list = f.readline().strip("\n").split(",")[1:]
                    shown_list = f.readline().strip("\n").split(",")[1:]
                    ignore_list = f.readline().strip("\n").split(",")[1:]
                    window_parts = f.readline().strip("\n").split(",")
                    self.windowLength.setValue(int(window_parts[1]))
            except (OSError, ValueError, IndexError):
                self.debugLogger.exception("Invalid display settings; using defaults")
                self.hidden_list = self.all_names.copy()
                self.ignore_list = [
                    name for name in self.hidden_list
                    if self.command_info_by_name.get(name, [None] * 4)[3]
                ]
                self.hidden_list = [
                    name for name in self.hidden_list if name not in self.ignore_list
                ]
                return False
            for name in self.all_names:
                if name in shown_list:
                    self.shown_list.append(name)
                elif name in hidden_list:  # in the case that the item is hidden or hasn't been set up
                    self.hidden_list.append(name)
                elif name in ignore_list:
                    self.ignore_list.append(name)
            return True
        else:  # if the file not exist, copy all names to hidden list
            self.hidden_list = self.all_names.copy()
            for name in self.all_names:
                if self.command_info_by_name[name][3]:
                    self.ignore_list.append(self.hidden_list.pop(self.hidden_list.index(name)))
            return False

    def hideItems(self):
        """
        Move items from shown list to hidden list, and from shown widget to hidden widget
        """
        selected = self.shownListWidget.selectedItems()  # multi selection
        for item in selected:
            row = self.shownListWidget.row(item)  # get row
            self.hiddenListWidget.addItem(
                self.shownListWidget.takeItem(row)
            )  # remove item from shown widget to hidden widget
            self.shown_list.remove(item.text())  # add the item from hidden list
            self.hidden_list.append(item.text())  # remove the item to the shown list

        self.saveDisplaySettings()  # save current setting
        return True

    def showItems(self):
        """
        Move items from hidden list to shown list, and from hidden widget to shown widget
        """

        selected = self.hiddenListWidget.selectedItems()  # multi selection
        for item in selected:
            row = self.hiddenListWidget.row(item)  # get row
            self.shownListWidget.addItem(
                self.hiddenListWidget.takeItem(row)
            )  # remove item from hidden widget to shown widget
            self.hidden_list.remove(item.text())  # remove the item from hidden list
            self.shown_list.append(item.text())  # add the item to the shown list

        self.saveDisplaySettings()  # save current setting
        return True

    ### =======================================================Alias Related=======================================================
    def getAlias(self, name: str = None):
        """
        Get alias and assign it to the name

        Args:
            name (str, option): if name is provided, return the alias, otherwise get alias by name dict

        Returns:
            alias (str): an alias
        """
        if not name:  # generate alias dictionary
            self.alias_by_name = {}  # {name: alias}
            for device in self.device_config:
                for name, info in self.commands[device].items():
                    if info["alias"]:
                        self.alias_by_name[name] = info["alias"]
                    else:
                        self.alias_by_name[name] = name

            return True
        else:
            return self.alias_by_name[
                name
            ]  # this is the special case that the name is actually variable name

    def convertNames(self, names: list):
        """
        Convert a list of name to a list of alias
        Args:
            Names (list): a list of name

        Returns:
            Names (list): a list of name from alias
        """

        for i in range(len(names)):
            if names[i].strip() in [
                "Date",
                "Time",
                "Seconds",
            ]:  # not consider x-axis labels
                pass
            else:
                raw_name = names[i].strip()
                names[i] = self.alias_by_name.get(raw_name, raw_name)

        return names

    ### =======================================================Status Related=======================================================
    def setLEDIndicator(self):
        """
        Set indicators based on the number of devices and status of devices
        """
        self.status_names = {} # the list to store what need to be shown as status
        self.indicator_dictionary = {}
        self.status = {False: red, True: green}
        self.logger_status = {
            state: (
                "QCheckBox { font-size: 20pt; }"
                "QCheckBox::indicator {"
                "width:40px; height:40px; border-radius:22px; }"
                "QCheckBox::indicator:unchecked {"
                f"background-color:{'green' if state else 'red'};"
                "border:2px solid white; }"
            )
            for state in (False, True)
        }

        logger_led = QCheckBox("Logger", self.groupBox_3)
        logger_led.setCheckable(False)
        logger_led.setStyleSheet(self.logger_status[False])
        self.systemStatusLayout.addWidget(logger_led)
        self.indicator_dictionary["Logger"] = logger_led

        status_layout = QVBoxLayout()
        connections_group = QGroupBox("Connections", self.groupBox_6)
        connections_layout = QVBoxLayout(connections_group)
        readings_group = QGroupBox("Readings", self.groupBox_6)
        readings_layout = QVBoxLayout(readings_group)
        has_readings = False

        for device in self.device_config:
            led = QCheckBox(device, connections_group)
            led.setCheckable(False)
            led.setStyleSheet(self.status[False])
            connections_layout.addWidget(led)
            self.indicator_dictionary[device] = led
            self.status_names[device] = []
            device_readings_group = QGroupBox(device, readings_group)
            device_readings_layout = QVBoxLayout(device_readings_group)
            device_has_readings = False
            for name, info in self.commands[device].items():
                if info['indicators']:
                    self.status_names[device].append(name)
                    for indicator in info['indicators']:
                        has_readings = True
                        device_has_readings = True
                        led = QCheckBox(indicator, device_readings_group)
                        led.setCheckable(False)
                        led.setStyleSheet(self.status[False])
                        device_readings_layout.addWidget(led)
                        self.indicator_dictionary[indicator] = led
            if device_has_readings:
                readings_layout.addWidget(device_readings_group)
            else:
                device_readings_group.deleteLater()

        if not has_readings:
            readings_layout.addWidget(
                QtWidgets.QLabel("No bit readings configured")
            )
        status_layout.addWidget(connections_group)
        status_layout.addWidget(readings_group)
        status_layout.addStretch()
        self.groupBox_6.setLayout(status_layout)
        
    def setStatus(self):
        """
        Set indicator values of devices
        """
        now = _time.monotonic()
        if now - self._last_process_check >= 2.0:
            self._logger_running = (
                self._is_logger_running() or self._has_recent_log_activity()
            )
            self._last_process_check = now

        logger_status_change = self._logger_running != (
            self.indicator_dictionary["Logger"].styleSheet()
            == self.logger_status[True]
        )
        if logger_status_change:
            self.indicator_dictionary["Logger"].setStyleSheet(
                self.logger_status[self._logger_running]
            )

        for device in self.device_config:
            if self._logger_running:
                readings = [
                    self.latest_data.get(self.getAlias(name), _np.nan)
                    for name in self.commands[device]
                ] if self.latest_data else []
                connected = bool(
                    self.device_config[device]["device_status"]
                    and readings
                    and any(not self._is_missing(value) for value in readings)
                )
                change_detected = connected != (
                    self.indicator_dictionary[device].styleSheet()
                    == self.status[True]
                )
                if change_detected:
                    self.indicator_dictionary[device].setStyleSheet(
                        self.status[connected]
                    )
            
                if self.latest_data:
                    for name in self.status_names[device]:
                        indicators = self.commands[device][name]['indicators']
                        indicators_reverse = self.commands[device][name]['indicators_reverse']
                        status = self.convertStringtoBit(
                            self.latest_data.get(self.getAlias(name), _np.nan),
                            len(indicators),
                            True,
                        )
                        if status == -1:
                            for i, indicator in enumerate(indicators):
                               self.indicator_dictionary[indicator].setStyleSheet(self.status[False])
                        else:
                            for i, indicator in enumerate(indicators):
                                bit = status[i] == "1"
                                res = bit if not indicators_reverse[i] else not bit
                                self.indicator_dictionary[indicator].setStyleSheet(self.status[res])
            else:
                self.indicator_dictionary[device].setStyleSheet(self.status[False])
                for name in self.status_names[device]:
                    indicators = self.commands[device][name]['indicators']
                    for indicator in indicators:
                        self.indicator_dictionary[indicator].setStyleSheet(self.status[False])
                        
        self.setSystemStatus()
        
    def setSystemStatus(self):
        """
        Set System Status based on indicator values
        """
        indicator_error = any(
            "red" in indicator.styleSheet()
            for indicator in self.indicator_dictionary.values()
        )
        levels = self.warning_level_by_name.values()
        if indicator_error or 2 in levels:
            color = "red"
        elif 1 in levels:
            color = "orange"
        else:
            color = "green"

        stylesheet = re.sub(
            r"background-color\s*:\s*(?:red|green|orange)",
            f"background-color:{color}",
            self.systemStatus.styleSheet(),
        )
        self.systemStatus.setStyleSheet(stylesheet)
        return color == "green"
        
    ### ======================================================= Warning Related =======================================================
    def getCommandInfoByName(self):
        """
        Get commands returns information: [min, max, static, bit_static]
        """

        self.command_info_by_name = {}
        for device in self.device_config:
            for name, info in self.commands[device].items():
                name = self.getAlias(name)  # convert to alias
                self.command_info_by_name[name] = [None, None, None, None]
                self.command_info_by_name[name][0] = info["min"]
                self.command_info_by_name[name][1] = info["max"]
                self.command_info_by_name[name][2] = info["static"]
                if info['bit_static']:
                    self.command_info_by_name[name][3] = self.convertStringtoBit(info['bit_static'], info['bits'], True)

    ### ======================================================= Warning Related =======================================================
    def setWarningLevelByName(self):
        """
        Set warning level for system indicator
        """

        self.warning_level_by_name = {name: 0 for name in self.data_by_name}

    def printWarning(self):
        """
        Print warning if the value is not in range
        """
        for name in self.all_data_by_name:
            if name not in ["Date", "Time", "Seconds"]:
                warning_level = 0
                command_info = self.command_info_by_name.get(name, [None] * 4)
                minimum = command_info[0]
                maximum = command_info[1]
                static = command_info[2]
                value = self.all_data_by_name[name][-1]
                if self._is_missing(value):
                    warning_level = 2
                elif static is not None:
                    if value != static:
                        warning_level = 2

                if minimum is not None and not self._is_missing(value):
                    if value < minimum:
                        warning_level = 2

                    elif value < 1.05 * minimum:
                        warning_level = max(warning_level, 1)

                if maximum is not None and not self._is_missing(value):
                    if value > maximum:
                        warning_level = 2
                    elif value > 0.95 * maximum:
                        warning_level = max(warning_level, 1)
                
                if (
                    warning_level > 0
                    and warning_level != self.warning_level_by_name[name]
                ):
                    current_time = (
                        self.all_data_by_name["Date"][-1]
                        + " "
                        + self.all_data_by_name["Time"][-1]
                    )
                    self.warning_level_by_name[name] = warning_level
                    if self._is_missing(value):
                        string = current_time + ": " + name + " has no valid data"
                    elif warning_level == 1:
                        string = current_time + ": " + name + " is reaching limit"
                    elif warning_level == 2:
                        string = current_time + ": " + name + " exceeds limit"
                    self.warningText.appendPlainText(string)

                elif (
                    warning_level == 0 and self.warning_level_by_name[name] > 0
                ):  # warning ends
                    current_time = (
                        self.all_data_by_name["Date"][-1]
                        + " "
                        + self.all_data_by_name["Time"][-1]
                    )
                    self.warning_level_by_name[name] = warning_level
                    string = current_time + ": " + name + " warning/error clean."
                    self.warningText.appendPlainText(string)

    def clearWarning(self):
        """
        Clear warning information
        """
        for name in self.data_by_name:
            if name not in ["Date", "Time", "Seconds"]:
                self.warning_level_by_name[name] = 0
        self.warningText.clear()

        return True

    ### ======================================================= Internal Used Functions ====================================================
    def binary_search(self, array, value):
        """
        It is used for searching the index of closest value in a given array. The method is binary search, faster in large array

        Please be notified that the array has been sorted already. The return is modified to get the index

        Reference: https://www.geeksforgeeks.org/find-closest-number-array/
        """
        if value == None:
            return None

        n = len(array)
        if value < array[0]:
            return 0
        elif value > array[-1]:
            return n - 1

        i = 0  # lower limit
        j = n  # upper limit

        while i < j:
            mid = (i + j) // 2

            if array[mid] == value:
                return mid

            if value < array[mid]:  # in the case value is on the left side of array
                if (
                    mid > 0 and value > array[mid - 1]
                ):  # array[mid] > value > array[mid - 1]
                    return self.get_closest(mid - 1, mid, value, array)

                j = mid  # move upper limit to mid

            else:  # in the case value is on the right side of array
                if (
                    mid < n - 1 and value < array[mid + 1]
                ):  # array[mid] < value < array[mid + 1]
                    return self.get_closest(1, mid + 1, value, array)

                i = mid + 1  # move lower limit to mid

        return mid

    def get_closest(self, index1, index2, target, array):
        if target - array[index1] >= array[index2] - target:
            return index2
        else:
            return index1
    
    def convertStringtoBit(self, string, bits = None, reverse = False):
        '''
        convert string to bit string, and optionally to trim it and reverse it
        eg. if string is 301, the function will return 1100000001,
            if bits is 9 and reverse is False, the function will return 100000001,
            if reverse is True and bits is None, the function will return 1000000011,

            Trimming will be applied before Reverse.
            
        '''
        if self._is_missing(string):
            return -1

        value = str(string).strip()
        try:
            number = int(value, 16)
        except (TypeError, ValueError):
            return -1
        out = bin(number)
        out = out.replace('0b', '')
        if bits:
            out = out[-1 * bits:]
            if len(out) < bits:
                out = '0' * (bits - len(out)) + out
        if reverse:
            out = out[::-1]
        
        return out

    @staticmethod
    def _is_missing(value):
        try:
            return bool(_np.isnan(value))
        except (TypeError, ValueError):
            return value is None or value == "nan"

    @staticmethod
    def _is_logger_running() -> bool:
        return is_logger_running()

    def _has_recent_log_activity(self) -> bool:
        """Recognize active loggers that predate or do not use our mutex."""
        if not self.current_file:
            return False
        path = os.path.join(self.file_dir, self.current_file)
        return has_recent_log_activity(path, self.log_interval)

    def closeEvent(self, event):
        self.timer.stop()
        if self.f is not None:
            self.f.close()
            self.f = None
        super().closeEvent(event)



if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
