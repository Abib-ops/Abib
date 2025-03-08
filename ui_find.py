# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading the UI file 'find.ui'
##
## Created by: Qt User Interface Compiler version 6.4.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect, Qt)
# from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
#                            QFont, QFontDatabase, QGradient, QIcon,
#                            QImage, QKeySequence, QLinearGradient, QPainter,
#                            QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialogButtonBox, QFrame,
                               QLabel, QLineEdit, QPushButton, QRadioButton, QWidget)


class Ui_Dialog(object):
    def __init__(self):
        # Define instance variables inside the constructor (__init__)
        self.frame: QFrame | None = None
        self.frame_2: QFrame | None = None
        self.frame_3: QFrame | None = None
        self.buttonBox: QDialogButtonBox | None = None
        self.buttonGroup: QButtonGroup | None = None
        self.buttonGroup_2: QButtonGroup | None = None
        self.label: QLabel | None = None
        self.label_1: QLabel | None = None
        self.label_2: QLabel | None = None
        self.comboBox_1: QComboBox | None = None
        self.comboBox_2: QComboBox | None = None
        self.pushButton_1: QPushButton | None = None
        self.lineEdit_1: QLineEdit | None = None
        self.checkBox: QCheckBox | None = None
        self.radiobutton_1: QRadioButton | None = None
        self.radiobutton_2: QRadioButton | None = None
        self.radiobutton_3: QRadioButton | None = None
        self.radiobutton_4: QRadioButton | None = None
        self.radiobutton_5: QRadioButton | None = None
        self.radiobutton_6: QRadioButton | None = None

    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")

        Dialog.resize(400, 378)
        Dialog.setWindowOpacity(1.0)

        # Assign the instance attributes here
        self.frame = QFrame(Dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setGeometry(QRect(10, 240, 191, 91))
        self.frame.setMouseTracking(True)
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Sunken)

        self.radiobutton_5: QRadioButton = QRadioButton(self.frame)
        self.radiobutton_5.setObjectName(u"radiobutton_5")
        self.radiobutton_5.setGeometry(QRect(10, 10, 171, 17))
        self.radiobutton_5.setChecked(True)
        self.buttonGroup_2 = QButtonGroup(Dialog)
        self.buttonGroup_2.setObjectName(u"buttonGroup_2")
        self.buttonGroup_2.addButton(self.radiobutton_5)
        self.radiobutton_6: QRadioButton = QRadioButton(self.frame)
        self.radiobutton_6.setObjectName(u"radiobutton_6")
        self.radiobutton_6.setGeometry(QRect(10, 50, 171, 17))
        self.buttonGroup_2.addButton(self.radiobutton_6)
        self.label_1 = QLabel(Dialog)
        self.label_1.setObjectName(u"label_1")
        self.label_1.setGeometry(QRect(20, 220, 181, 16))
        self.checkBox = QCheckBox(Dialog)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setGeometry(QRect(20, 180, 361, 31))
        self.lineEdit_1 = QLineEdit(Dialog)
        self.lineEdit_1.setObjectName(u"lineEdit_1")
        self.lineEdit_1.setGeometry(QRect(70, 10, 321, 21))

        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 10, 71, 21))

        self.pushButton_1: QPushButton = QPushButton(Dialog)
        self.pushButton_1.setObjectName(u"pushButton_1")
        self.pushButton_1.setGeometry(QRect(370, 10, 21, 21))
        self.frame_2 = QFrame(Dialog)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setGeometry(QRect(220, 240, 171, 91))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Sunken)
        self.comboBox_1 = QComboBox(self.frame_2)
        self.comboBox_1.setObjectName(u"comboBox_1")
        self.comboBox_1.setGeometry(QRect(10, 10, 151, 22))
        self.comboBox_1.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.comboBox_2 = QComboBox(self.frame_2)
        self.comboBox_2.setObjectName(u"comboBox_2")
        self.comboBox_2.setGeometry(QRect(10, 50, 151, 22))
        self.comboBox_2.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.label_2 = QLabel(Dialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(230, 220, 161, 20))
        self.radiobutton_1 = QRadioButton(Dialog)
        self.buttonGroup = QButtonGroup(Dialog)
        self.buttonGroup.setObjectName(u"buttonGroup")
        self.buttonGroup.addButton(self.radiobutton_1)
        self.radiobutton_1.setObjectName(u"radiobutton_1")
        self.radiobutton_1.setGeometry(QRect(20, 50, 361, 31))
        self.radiobutton_1.setTabletTracking(True)
        self.radiobutton_1.setChecked(True)
        self.radiobutton_2 = QRadioButton(Dialog)
        self.buttonGroup.addButton(self.radiobutton_2)
        self.radiobutton_2.setObjectName(u"radiobutton_2")
        self.radiobutton_2.setGeometry(QRect(20, 80, 361, 31))
        self.radiobutton_3 = QRadioButton(Dialog)
        self.buttonGroup.addButton(self.radiobutton_3)
        self.radiobutton_3.setObjectName(u"radiobutton_3")
        self.radiobutton_3.setGeometry(QRect(20, 110, 361, 31))
        self.radiobutton_4 = QRadioButton(Dialog)
        self.buttonGroup.addButton(self.radiobutton_4)
        self.radiobutton_4.setObjectName(u"radiobutton_4")
        self.radiobutton_4.setGeometry(QRect(20, 140, 361, 31))
        self.frame_3 = QFrame(Dialog)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setGeometry(QRect(10, 49, 381, 121))
        self.frame_3.setMouseTracking(True)
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Sunken)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(230, 340, 156, 23))
        self.buttonBox.setMouseTracking(True)
        # self.buttonBox.setFocusPolicy(Qt.StrongFocus)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.frame_2.raise_()
        self.frame_3.raise_()
        self.frame.raise_()
        self.label_1.raise_()
        self.checkBox.raise_()
        self.lineEdit_1.raise_()
        self.label.raise_()
        self.pushButton_1.raise_()
        self.label_2.raise_()
        self.radiobutton_1.raise_()
        self.radiobutton_2.raise_()
        self.radiobutton_3.raise_()
        self.radiobutton_4.raise_()
        self.buttonBox.raise_()

        # Allow focus only for lineEdit_1
        self.lineEdit_1.setFocusPolicy(Qt.StrongFocus)

        # Disable focus for all other widgets
        self.frame.setFocusPolicy(Qt.NoFocus)
        self.frame_2.setFocusPolicy(Qt.NoFocus)
        self.frame_3.setFocusPolicy(Qt.NoFocus)
        self.checkBox.setFocusPolicy(Qt.NoFocus)
        self.pushButton_1.setFocusPolicy(Qt.NoFocus)
        self.comboBox_1.setFocusPolicy(Qt.NoFocus)
        self.comboBox_2.setFocusPolicy(Qt.NoFocus)
        self.radiobutton_1.setFocusPolicy(Qt.NoFocus)
        self.radiobutton_2.setFocusPolicy(Qt.NoFocus)
        self.radiobutton_3.setFocusPolicy(Qt.NoFocus)
        self.radiobutton_4.setFocusPolicy(Qt.NoFocus)
        self.radiobutton_5.setFocusPolicy(Qt.NoFocus)
        self.radiobutton_6.setFocusPolicy(Qt.NoFocus)
        self.buttonBox.setFocusPolicy(Qt.NoFocus)

        self.label.setBuddy(self.lineEdit_1)

        QWidget.setTabOrder(self.lineEdit_1, self.pushButton_1)
        # QWidget.setTabOrder(self.pushButton_1, self.radiobutton_1)
        # QWidget.setTabOrder(self.radiobutton_1, self.radiobutton_2)
        # QWidget.setTabOrder(self.radiobutton_2, self.radiobutton_3)
        # QWidget.setTabOrder(self.radiobutton_3, self.radiobutton_4)
        # QWidget.setTabOrder(self.radiobutton_4, self.checkBox)
        # QWidget.setTabOrder(self.checkBox, self.radiobutton_5)
        # QWidget.setTabOrder(self.radiobutton_5, self.radiobutton_6)
        # QWidget.setTabOrder(self.radiobutton_6, self.comboBox_1)
        # QWidget.setTabOrder(self.comboBox_1, self.comboBox_2)

        self.retranslateUi(Dialog)
        self.pushButton_1.clicked.connect(self.lineEdit_1.clear)
        self.radiobutton_5.clicked.connect(self.radiobutton_4.show)
        self.radiobutton_5.clicked.connect(self.radiobutton_3.show)
        self.radiobutton_5.clicked.connect(self.radiobutton_2.show)
        self.radiobutton_5.clicked.connect(self.radiobutton_1.show)
        self.radiobutton_6.clicked.connect(self.radiobutton_1.hide)
        self.radiobutton_6.clicked.connect(self.radiobutton_2.hide)
        self.radiobutton_6.clicked.connect(self.radiobutton_3.hide)
        self.radiobutton_6.clicked.connect(self.radiobutton_4.hide)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Find Options", None))
        self.radiobutton_5.setText(QCoreApplication.translate("Dialog", u"Normal", None))
        self.radiobutton_6.setText(QCoreApplication.translate("Dialog", u"Regular expression", None))
        self.label_1.setText(QCoreApplication.translate("Dialog", u"Mode", None))
        self.checkBox.setText(QCoreApplication.translate("Dialog", u"Match case", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"&Find what:", None))
        self.pushButton_1.setText(QCoreApplication.translate("Dialog", u"X", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Search Limits", None))
        self.radiobutton_1.setText(QCoreApplication.translate(
            "Dialog", u"Raw Search                      (Literal search - part words - anything)", None))
        self.radiobutton_2.setText(QCoreApplication.translate(
            "Dialog", u"Match whole words          (Single word or phrase)", None))
        self.radiobutton_3.setText(QCoreApplication.translate(
            "Dialog", u"All the words                    (Somewhere in the verse)", None))
        self.radiobutton_4.setText(QCoreApplication.translate(
            "Dialog", u"Any of the words             (With results sorted)", None))
        self.buttonBox.setProperty(".standardButtons", "")
    # retranslateUi

