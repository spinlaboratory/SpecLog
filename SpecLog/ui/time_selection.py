"""UI for selecting and plotting a historical time range."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget


class Ui_TimeSelectionWindow:
    def setupUi(self, window):
        window.setWindowTitle("Select Time")
        window.resize(950, 650)
        central = QWidget(window)
        layout = QVBoxLayout(central)

        controls = QHBoxLayout()
        form = QFormLayout()
        self.startTime = QLineEdit()
        self.startTime.setPlaceholderText("yyyymmddHHMM")
        self.startTime.setMinimumWidth(180)
        form.addRow("Start Time", self.startTime)

        duration_container = QWidget()
        duration_layout = QHBoxLayout(duration_container)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(4)
        self.durationValue = QDoubleSpinBox()
        self.durationValue.setDecimals(2)
        self.durationValue.setMaximum(100000)
        self.durationValue.setSpecialValueText("All")
        self.durationUnit = QComboBox()
        self.durationUnit.addItems(["Hours", "Days"])
        duration_layout.addWidget(self.durationValue)
        duration_layout.addWidget(self.durationUnit)
        form.addRow("Duration", duration_container)
        controls.addLayout(form)
        controls.addStretch()

        self.statusLabel = QLabel()
        self.statusLabel.setMinimumWidth(0)
        self.statusLabel.setWordWrap(True)
        self.statusLabel.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.statusLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.resetButton = QPushButton("Reset")
        self.loadFileButton = QPushButton("Load")
        self.saveButton = QPushButton("Save")
        self.saveButton.setEnabled(False)
        self.saveFigureButton = QPushButton("Save Figure")
        self.saveFigureButton.setEnabled(False)
        self.okButton = QPushButton("OK")
        self.okButton.setDefault(True)
        controls.addWidget(self.loadFileButton)
        controls.addWidget(self.saveButton)
        controls.addWidget(self.saveFigureButton)
        controls.addWidget(self.okButton)
        controls.addWidget(self.resetButton)
        layout.addLayout(controls)
        layout.addWidget(self.statusLabel)

        content = QHBoxLayout()
        item_group = QGroupBox("Items to plot")
        item_group.setMaximumWidth(240)
        item_layout = QVBoxLayout(item_group)
        self.itemList = QListWidget()
        item_layout.addWidget(self.itemList)
        content.addWidget(item_group)
        self.graphWidget = PlotWidget()
        content.addWidget(self.graphWidget, 1)
        layout.addLayout(content, 1)
        window.setCentralWidget(central)

    def set_plot_items(self, names, selected):
        selected = set(selected)
        previous = {
            self.itemList.item(index).text():
            self.itemList.item(index).checkState() == Qt.CheckState.Checked
            for index in range(self.itemList.count())
        }
        self.itemList.blockSignals(True)
        self.itemList.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setForeground(QColor("#000000"))
            checked = previous.get(name, name in selected)
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            self.itemList.addItem(item)
        self.itemList.blockSignals(False)

    def selected_plot_items(self):
        return [
            self.itemList.item(index).text()
            for index in range(self.itemList.count())
            if self.itemList.item(index).checkState() == Qt.CheckState.Checked
        ]
