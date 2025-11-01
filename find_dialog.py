# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from find import Ui_Dialog


class FindDialog(QDialog):
    """Find dialog extracted from Abib.py and made parent-aware.

    This version avoids referencing the global `w` by using the provided parent
    MainWindow instance for data (nwin) and actions (findf3, close_find_window).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._main = parent  # MainWindow reference

        # Create an instance of the GUI
        self.ui = Ui_Dialog()
        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)

        # checks[0] is 1-4 for radiobuttons 1 to 4
        # checks[1] is 0-1 for checkBox
        # checks[2] is 5-6 for radiobuttons 5 & 6
        self.checks = [1, 0, 5]
        self.setGeometry(700, 300, 400, 378)

        self.ui.lineEdit_1.setToolTip("press RETURN to find")
        self.ui.lineEdit_1.returnPressed.connect(self.getter)
        self.ui.lineEdit_1.setClearButtonEnabled(False)
        self.ui.lineEdit_1.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.ui.pushButton_1.clicked.connect(self.ui.lineEdit_1.clear)

        # Populate book range comboboxes from the parent window state
        if hasattr(self._main, "nwin") and isinstance(self._main.nwin, list):
            self.ui.comboBox_1.addItems(self._main.nwin)
            self.ui.comboBox_2.addItems(self._main.nwin)
        self.ui.comboBox_1.setCurrentIndex(0)
        # Expect BOOKS_IN_THE_BIBLE - 1 as last index
        try:
            from shared import BOOKS_IN_THE_BIBLE  # local import to avoid heavy module import at top
            self.ui.comboBox_2.setCurrentIndex(BOOKS_IN_THE_BIBLE - 1)
        except Exception:
            # Fallback if constant not available for any reason
            if self.ui.comboBox_2.count() > 0:
                self.ui.comboBox_2.setCurrentIndex(self.ui.comboBox_2.count() - 1)

        QOk = QDialogButtonBox.StandardButton.Ok
        self.ui.buttonBox.button(QOk).setEnabled(True)
        self.ui.buttonBox.button(QOk).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.buttonBox.button(QOk).clicked.connect(self.getter)
        QCancel = QDialogButtonBox.StandardButton.Cancel
        self.ui.buttonBox.button(QCancel).setEnabled(True)
        self.ui.buttonBox.button(QCancel).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Use parent's close handler
        if hasattr(self._main, "close_find_window"):
            self.ui.buttonBox.button(QCancel).clicked.connect(self._main.close_find_window)

        self.ui.lineEdit_1.setFocus()

        self.ui.comboBox_1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.comboBox_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_4.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_5.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_6.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.checkBox.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.ui.lineEdit_1.textChanged.connect(self.ui.lineEdit_1.setFocus)
        self.ui.pushButton_1.hide()

        # Dynamically show/hide the clear button based on text presence
        self.ui.lineEdit_1.textChanged.connect(self.toggle_clear_button)

    def toggle_clear_button(self) -> None:
        if self.ui.lineEdit_1.text():
            self.ui.pushButton_1.show()
            self.ui.lineEdit_1.setFocus()
        else:
            self.ui.pushButton_1.hide()
            self.ui.lineEdit_1.setFocus()

    def getter(self) -> None:
        """Get values from the find window and transfer to findf3 on the parent."""
        key = self.ui.lineEdit_1.text()
        i, j = self.get_scope()
        self.get_checks()
        if hasattr(self._main, "findf3"):
            # mirror previous behavior by setting parent's key and calling findf3
            setattr(self._main, "key", key)
            self._main.findf3(i, j)
        if hasattr(self._main, "close_find_window"):
            self._main.close_find_window()

    def get_scope(self) -> Tuple[int, int]:
        """Get the scope from the comboboxes."""
        i: int = self.ui.comboBox_1.currentIndex()
        j: int = self.ui.comboBox_2.currentIndex()
        if i > j:
            i, j = j, i
            self.ui.comboBox_1.setCurrentIndex(i)
            self.ui.comboBox_2.setCurrentIndex(j)
        return i, j

    def check_changed(self) -> None:
        """Ensure that the checkBox is correct."""
        self.checks[1] = 1 if self.ui.checkBox.isChecked() else 0

    def radiobutton1_4_changed(self) -> None:
        """Ensure that radiobuttons 1 to 4 are correct."""
        if self.ui.radiobutton_1.isChecked():
            self.checks[0] = 1
        elif self.ui.radiobutton_2.isChecked():
            self.checks[0] = 2
        elif self.ui.radiobutton_3.isChecked():
            self.checks[0] = 3
        elif self.ui.radiobutton_4.isChecked():
            self.checks[0] = 4

    def radiobutton5_6_changed(self) -> None:
        """Ensure that radiobuttons 5 & 6 are correct."""
        if self.ui.radiobutton_6.isChecked():
            self.checks[2] = 6
            self.ui.radiobutton_1.setChecked(True)
            self.checks[0] = 1
        else:
            self.checks[2] = 5

    def get_checks(self) -> None:
        """Store the states of the checkboxes in the list checks."""
        self.checks = [1, 0, 5]
        self.check_changed()
        self.radiobutton1_4_changed()
        self.radiobutton5_6_changed()
