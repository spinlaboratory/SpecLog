# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'plotting.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QFormLayout,
    QGridLayout, QGroupBox, QLabel, QLayout,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMenuBar, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpinBox, QStatusBar, QWidget)

from pyqtgraph import PlotWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1330, 1009)
        self.loadFile = QAction(MainWindow)
        self.loadFile.setObjectName(u"loadFile")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.groupBox_6 = QGroupBox(self.centralwidget)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.groupBox_6.setMinimumSize(QSize(301, 0))
        self.groupBox_6.setMaximumSize(QSize(301, 16777215))
        self.groupBox_6.setFlat(False)
        self.groupBox_6.setCheckable(False)

        self.gridLayout_2.addWidget(self.groupBox_6, 4, 0, 1, 1)

        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setMinimumSize(QSize(301, 131))
        self.groupBox.setMaximumSize(QSize(301, 131))
        self.formLayout = QFormLayout(self.groupBox)
        self.formLayout.setObjectName(u"formLayout")
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(49, 20))
        self.label_3.setMaximumSize(QSize(49, 20))

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_3)

        self.startTime = QLineEdit(self.groupBox)
        self.startTime.setObjectName(u"startTime")
        self.startTime.setMinimumSize(QSize(200, 20))
        self.startTime.setMaximumSize(QSize(200, 20))

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.startTime)

        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setMinimumSize(QSize(43, 20))
        self.label_4.setMaximumSize(QSize(43, 20))

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_4)

        self.endTime = QLineEdit(self.groupBox)
        self.endTime.setObjectName(u"endTime")
        self.endTime.setMinimumSize(QSize(200, 20))
        self.endTime.setMaximumSize(QSize(200, 20))

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.endTime)

        self.setToLive = QPushButton(self.groupBox)
        self.setToLive.setObjectName(u"setToLive")
        self.setToLive.setMinimumSize(QSize(75, 23))
        self.setToLive.setMaximumSize(QSize(75, 23))

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.setToLive)

        self.setToStatic = QPushButton(self.groupBox)
        self.setToStatic.setObjectName(u"setToStatic")
        self.setToStatic.setMinimumSize(QSize(200, 23))
        self.setToStatic.setMaximumSize(QSize(200, 23))

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.setToStatic)


        self.gridLayout_2.addWidget(self.groupBox, 3, 0, 1, 1)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setMinimumSize(QSize(291, 301))
        self.groupBox_2.setMaximumSize(QSize(291, 301))
        self.gridLayout = QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.shownListWidget = QListWidget(self.groupBox_2)
        self.shownListWidget.setObjectName(u"shownListWidget")
        self.shownListWidget.setMinimumSize(QSize(101, 251))
        self.shownListWidget.setMaximumSize(QSize(101, 251))
        self.shownListWidget.setSelectionMode(QAbstractItemView.MultiSelection)

        self.gridLayout.addWidget(self.shownListWidget, 0, 2, 5, 1)

        self.hiddenListWidget = QListWidget(self.groupBox_2)
        self.hiddenListWidget.setObjectName(u"hiddenListWidget")
        self.hiddenListWidget.setMinimumSize(QSize(101, 251))
        self.hiddenListWidget.setMaximumSize(QSize(101, 251))
        self.hiddenListWidget.setSelectionMode(QAbstractItemView.MultiSelection)

        self.gridLayout.addWidget(self.hiddenListWidget, 0, 0, 5, 1)

        self.Shown = QLabel(self.groupBox_2)
        self.Shown.setObjectName(u"Shown")
        self.Shown.setMinimumSize(QSize(41, 20))
        self.Shown.setMaximumSize(QSize(41, 20))

        self.gridLayout.addWidget(self.Shown, 0, 1, 1, 1)

        self.shownToHidden = QPushButton(self.groupBox_2)
        self.shownToHidden.setObjectName(u"shownToHidden")
        self.shownToHidden.setMinimumSize(QSize(31, 23))
        self.shownToHidden.setMaximumSize(QSize(31, 23))

        self.gridLayout.addWidget(self.shownToHidden, 3, 1, 1, 1)

        self.Hidden = QLabel(self.groupBox_2)
        self.Hidden.setObjectName(u"Hidden")
        self.Hidden.setMinimumSize(QSize(41, 20))
        self.Hidden.setMaximumSize(QSize(41, 20))

        self.gridLayout.addWidget(self.Hidden, 4, 1, 1, 1)

        self.hiddenToShown = QPushButton(self.groupBox_2)
        self.hiddenToShown.setObjectName(u"hiddenToShown")
        self.hiddenToShown.setMinimumSize(QSize(31, 23))
        self.hiddenToShown.setMaximumSize(QSize(31, 23))

        self.gridLayout.addWidget(self.hiddenToShown, 1, 1, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox_2, 2, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.centralwidget)
        self.groupBox_4.setObjectName(u"groupBox_4")
        sizePolicy.setHeightForWidth(self.groupBox_4.sizePolicy().hasHeightForWidth())
        self.groupBox_4.setSizePolicy(sizePolicy)
        self.groupBox_4.setMinimumSize(QSize(452, 121))
        self.groupBox_4.setMaximumSize(QSize(452, 121))
        self.groupBox_4.setFlat(False)
        self.gridLayout_3 = QGridLayout(self.groupBox_4)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.clearWarningText = QPushButton(self.groupBox_4)
        self.clearWarningText.setObjectName(u"clearWarningText")
        self.clearWarningText.setMinimumSize(QSize(75, 23))
        self.clearWarningText.setMaximumSize(QSize(75, 23))

        self.gridLayout_3.addWidget(self.clearWarningText, 0, 1, 1, 1)

        self.warningText = QPlainTextEdit(self.groupBox_4)
        self.warningText.setObjectName(u"warningText")
        self.warningText.setMinimumSize(QSize(351, 71))
        self.warningText.setMaximumSize(QSize(351, 71))
        self.warningText.setReadOnly(True)

        self.gridLayout_3.addWidget(self.warningText, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox_4, 0, 1, 1, 1)

        self.groupBox_5 = QGroupBox(self.centralwidget)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.groupBox_5.setMinimumSize(QSize(155, 53))
        self.groupBox_5.setMaximumSize(QSize(301, 53))
        self.gridLayout_4 = QGridLayout(self.groupBox_5)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.label_8 = QLabel(self.groupBox_5)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_4.addWidget(self.label_8, 0, 0, 1, 1)

        self.windowLength = QSpinBox(self.groupBox_5)
        self.windowLength.setObjectName(u"windowLength")
        self.windowLength.setReadOnly(False)
        self.windowLength.setKeyboardTracking(False)
        self.windowLength.setMinimum(10)
        self.windowLength.setMaximum(10000)
        self.windowLength.setSingleStep(100)
        self.windowLength.setDisplayIntegerBase(10)

        self.gridLayout_4.addWidget(self.windowLength, 0, 1, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox_5, 1, 0, 1, 1)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setTextFormat(Qt.PlainText)
        self.label.setScaledContents(False)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.graphWidget = PlotWidget(self.centralwidget)
        self.graphWidget.setObjectName(u"graphWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.graphWidget.sizePolicy().hasHeightForWidth())
        self.graphWidget.setSizePolicy(sizePolicy1)
        self.graphWidget.setMinimumSize(QSize(511, 460))
        self.graphWidget.setMouseTracking(False)
        self.graphWidget.setLayoutDirection(Qt.LeftToRight)
        self.graphWidget.setAutoFillBackground(False)

        self.gridLayout_2.addWidget(self.graphWidget, 1, 1, 4, 2)

        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.systemStatus = QCheckBox(self.groupBox_3)
        self.systemStatus.setObjectName(u"systemStatus")
        self.systemStatus.setGeometry(QRect(40, 30, 241, 61))
        font1 = QFont()
        font1.setPointSize(20)
        self.systemStatus.setFont(font1)
        self.systemStatus.setStyleSheet(u"QCheckBox::indicator {\n"
"	width:40px;\n"
"	height:40px;\n"
"	border-radius:22px;}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"	background-color:red;\n"
"	border:2px solid white;}")
        self.systemStatus.setCheckable(False)

        self.gridLayout_2.addWidget(self.groupBox_3, 0, 2, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1330, 21))
        self.menuFile = QMenu(self.menuBar)
        self.menuFile.setObjectName(u"menuFile")
        MainWindow.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuFile.addAction(self.loadFile)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"pyMonitor", None))
        self.loadFile.setText(QCoreApplication.translate("MainWindow", u"Load File", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("MainWindow", u"Status", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Data Selection - format: yyyymmddHHMM", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Start Time", None))
        self.startTime.setText(QCoreApplication.translate("MainWindow", u"yyyymmddHHMM", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"End Time", None))
        self.endTime.setText(QCoreApplication.translate("MainWindow", u"yyyymmddHHMM", None))
        self.setToLive.setText(QCoreApplication.translate("MainWindow", u"Reset", None))
        self.setToStatic.setText(QCoreApplication.translate("MainWindow", u"Ok", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Monitoring Item", None))
        self.Shown.setText(QCoreApplication.translate("MainWindow", u"Shown", None))
        self.shownToHidden.setText(QCoreApplication.translate("MainWindow", u"<", None))
        self.Hidden.setText(QCoreApplication.translate("MainWindow", u"Hidden", None))
        self.hiddenToShown.setText(QCoreApplication.translate("MainWindow", u">", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"Warnings", None))
        self.clearWarningText.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"Monitor Settings", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Window Length", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"PyMonitor", None))
        self.groupBox_3.setTitle("")
        self.systemStatus.setText(QCoreApplication.translate("MainWindow", u"System Status", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
    # retranslateUi

