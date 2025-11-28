# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple, Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from ui_find import Ui_Dialog as UiDialog


class FindDialog(QDialog):
    """Find a dialog extracted from Abib.py and made parent-aware.

    This version avoids referencing the global `w` by using the provided parent
    MainWindow instance for data (nwin) and actions (findf3, close_find_window).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._main = parent  # MainWindow reference

        # Create an instance of the GUI
        self.ui = UiDialog()
        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)

        # checks[0] is 1-4 for radiobuttons 1 to 4
        # checks[1] is 0-1 for checkBox
        # checks[2] is 5-6 for radiobuttons 5 & 6
        self.checks = [1, 0, 5]
        self.setGeometry(700, 300, 400, 378)

        self.ui.lineEdit_1.setToolTip("press RETURN to find")
        cast(Any, self.ui.lineEdit_1.returnPressed).connect(self.getter)
        self.ui.lineEdit_1.setClearButtonEnabled(False)
        self.ui.lineEdit_1.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Associate label mnemonic with the line edit (moved from ui_find.py)
        self.ui.label.setBuddy(self.ui.lineEdit_1)

        cast(Any, self.ui.pushButton_1.clicked).connect(lambda _b: self.ui.lineEdit_1.clear())
        # Mirror Designer-time connections previously in ui_find.py
        cast(Any, self.ui.radiobutton_5.clicked).connect(lambda _b: self.ui.radiobutton_4.show())
        cast(Any, self.ui.radiobutton_5.clicked).connect(lambda _b: self.ui.radiobutton_3.show())
        cast(Any, self.ui.radiobutton_5.clicked).connect(lambda _b: self.ui.radiobutton_2.show())
        cast(Any, self.ui.radiobutton_5.clicked).connect(lambda _b: self.ui.radiobutton_1.show())
        cast(Any, self.ui.radiobutton_6.clicked).connect(lambda _b: self.ui.radiobutton_1.hide())
        cast(Any, self.ui.radiobutton_6.clicked).connect(lambda _b: self.ui.radiobutton_2.hide())
        cast(Any, self.ui.radiobutton_6.clicked).connect(lambda _b: self.ui.radiobutton_3.hide())
        cast(Any, self.ui.radiobutton_6.clicked).connect(lambda _b: self.ui.radiobutton_4.hide())

        # Populate book range comboboxes from the parent window state
        if hasattr(self._main, "nwin") and isinstance(self._main.nwin, list):
            self.ui.comboBox_1.addItems(self._main.nwin)
            self.ui.comboBox_2.addItems(self._main.nwin)
        self.ui.comboBox_1.setCurrentIndex(0)
        # Expect BOOKS_IN_THE_BIBLE - 1 as the last index
        try:
            from shared import BOOKS_IN_THE_BIBLE  # local import to avoid heavy module import at the top
            self.ui.comboBox_2.setCurrentIndex(BOOKS_IN_THE_BIBLE - 1)
        except (ImportError, TypeError, ValueError):
            # Fallback if constant not available for any reason
            if self.ui.comboBox_2.count() > 0:
                self.ui.comboBox_2.setCurrentIndex(self.ui.comboBox_2.count() - 1)

        # Enforce range rules dynamically: start (comboBox_1) must be <= end (comboBox_2)
        # and the end dropdown must reflect this by disabling invalid items.
        # Connect handlers and initialise once.
        cast(Any, self.ui.comboBox_1.currentIndexChanged).connect(self._on_start_changed)
        cast(Any, self.ui.comboBox_2.currentIndexChanged).connect(self._on_end_changed)
        self._apply_end_constraints()

        QOk = QDialogButtonBox.StandardButton.Ok
        self.ui.buttonBox.button(QOk).setEnabled(True)
        self.ui.buttonBox.button(QOk).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cast(Any, self.ui.buttonBox.button(QOk).clicked).connect(lambda _b: self.getter())
        QCancel = QDialogButtonBox.StandardButton.Cancel
        self.ui.buttonBox.button(QCancel).setEnabled(True)
        self.ui.buttonBox.button(QCancel).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Use parent's close handler
        if hasattr(self._main, "close_find_window"):
            cast(Any, self.ui.buttonBox.button(QCancel).clicked).connect(lambda _b: self._main.close_find_window())

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

        cast(Any, self.ui.lineEdit_1.textChanged).connect(lambda _t: self.ui.lineEdit_1.setFocus())
        self.ui.pushButton_1.hide()

        # Dynamically show/hide the clear button based on text presence
        cast(Any, self.ui.lineEdit_1.textChanged).connect(lambda _t: self.toggle_clear_button())

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
            # mirror previous behaviour by setting the parent's key and calling findf3
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

    # ---- Range constraints helpers ----
    def _apply_end_constraints(self) -> None:
        """Disable items in the end combo that are before the current start index.

        This makes the rule (start <= end) visible in the dropdown list.
        """
        start_idx = max(0, self.ui.comboBox_1.currentIndex())
        count = self.ui.comboBox_2.count()
        model = self.ui.comboBox_2.model()
        for k in range(count):
            enabled = k >= start_idx
            # Prefer QStandardItemModel-style enable/disable if available
            try:
                item = getattr(model, "item")(k)
            except Exception:
                item = None
            if item is not None:
                try:
                    item.setEnabled(bool(enabled))
                    # Also affect selection to reflect disabled state in popup
                    item.setSelectable(bool(enabled))
                except Exception:
                    # If anything goes wrong, silently ignore; snapping logic below enforces validity
                    pass
            else:
                # Fallback: if the underlying model does not expose items (custom model),
                # skip visual disabling and rely on snapping logic to enforce correctness.
                # (Generic QAbstractItemModel does not provide a way to change flags directly.)
                pass
        # If the current end is now invalid, snap it to start
        end_idx = self.ui.comboBox_2.currentIndex()
        if 0 <= end_idx < start_idx:
            # Prevent signal loops while adjusting
            bs = self.ui.comboBox_2.blockSignals(True)
            try:
                self.ui.comboBox_2.setCurrentIndex(start_idx)
            finally:
                self.ui.comboBox_2.blockSignals(bs)

    def _on_start_changed(self, index: int) -> None:
        """When the start changes, update the end combo list and selection."""
        # Ensure end >= start
        self._apply_end_constraints()

    def _on_end_changed(self, index: int) -> None:
        """When the end changes, ensure it is not less than start."""
        start_idx = self.ui.comboBox_1.currentIndex()
        if index < start_idx:
            bs = self.ui.comboBox_2.blockSignals(True)
            try:
                self.ui.comboBox_2.setCurrentIndex(start_idx)
            finally:
                self.ui.comboBox_2.blockSignals(bs)

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
