# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Tuple, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QStyle
from PySide6.QtGui import QFontMetrics

from abib.ui.ui_find import UiDialog as UiDialog
from abib.services.settings import SettingsService


class FindDialog(QDialog):
    """Find a dialog extracted from Abib.py and made parent-aware.

    This version avoids referencing the global `w` by using the provided parent
    MainWindow instance for data (nwin) and actions (findf3, close_find_window).
    """

    def __init__(self, parent=None, settings_service: SettingsService | None = None) -> None:
        super().__init__(parent)
        self._main = parent  # MainWindow reference
        self.settings_service: SettingsService = settings_service if settings_service is not None else SettingsService()

        # Create an instance of the GUI
        self.ui = UiDialog()
        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)

        # Assertions for UI components defined as Optional in UiDialog
        assert self.ui.radiobutton_1 is not None
        assert self.ui.radiobutton_2 is not None
        assert self.ui.radiobutton_3 is not None
        assert self.ui.radiobutton_4 is not None
        assert self.ui.radiobutton_5 is not None
        assert self.ui.radiobutton_6 is not None
        assert self.ui.comboBox_1 is not None
        assert self.ui.comboBox_2 is not None
        assert self.ui.lineEdit_1 is not None
        assert self.ui.label is not None
        assert self.ui.checkBox is not None
        assert self.ui.pushButton_1 is not None
        assert self.ui.buttonBox is not None
        # Create local references with type hints to satisfy the static analyser.
        rb1: Any = self.ui.radiobutton_1
        rb2: Any = self.ui.radiobutton_2
        rb3: Any = self.ui.radiobutton_3
        rb4: Any = self.ui.radiobutton_4
        rb5: Any = self.ui.radiobutton_5
        rb6: Any = self.ui.radiobutton_6
        cb1: Any = self.ui.comboBox_1
        cb2: Any = self.ui.comboBox_2
        le1: Any = self.ui.lineEdit_1
        lab_buddy: Any = self.ui.label
        chk: Any = self.ui.checkBox
        pb1: Any = self.ui.pushButton_1
        bb: Any = self.ui.buttonBox

        # Robust alignment: split each radio button into a left label (on the radio)
        # and a separate right-hand QLabel for the bracketed description.
        # This guarantees perfect alignment in proportional fonts and across DPI.
        try:
            # Define left and right parts
            pairs: list[tuple[str, str]] = [
                ("Raw Search", "(Literal search)"),
                ("Whole words", "(Single word or phrase)"),
                ("All the words", "(Somewhere in the verse)"),
                ("Any of the words", "(With results sorted)"),
            ]

            radios = (rb1, rb2, rb3, rb4)

            # Apply only the left text to the radio buttons
            for rb, (left, _right) in zip(radios, pairs):
                rb.setText(left)

            # Compute the x where the right labels should start
            prop_font = self.font()
            fm = QFontMetrics(prop_font)
            max_left_px = max(fm.horizontalAdvance(left) for left, _ in pairs)
            gutter_px = max(6, fm.horizontalAdvance("  "))  # ~two-space gutter
            # Extra uniform padding to shift the right-hand labels further right
            extra_pad_px = max(12, fm.horizontalAdvance("    "))  # ~4 spaces or 12px minimum

            # Account for the radio indicator and label spacing from the current style
            style = self.style()
            indicator_w = style.pixelMetric(QStyle.PixelMetric.PM_ExclusiveIndicatorWidth, None, radios[0])
            spacing = style.pixelMetric(QStyle.PixelMetric.PM_CheckBoxLabelSpacing, None, radios[0])

            # All radios share the same x; take the first
            radios_x = min(rb.geometry().x() for rb in radios)
            text_start_x = radios_x + max(0, indicator_w) + max(0, spacing)
            column_x = int(text_start_x + max_left_px + gutter_px + extra_pad_px)

            # Create right-hand labels and position them; keep references for show/hide
            self._right_labels: list[QLabel] = []
            for rb, (_left, right) in zip(radios, pairs):
                lbl = QLabel(self)
                lbl.setText(right)
                lbl.setFont(prop_font)
                # Make clicks pass through so the radio remains clickable
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                # Place the label aligned with the radio row
                g = rb.geometry()
                # Vertically centre text inside radio row height
                label_height = g.height()
                lbl.setGeometry(column_x, g.y(), max(10, self.width() - column_x - 10), label_height)
                lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                lbl.show()
                self._right_labels.append(lbl)

            # Keep alignment on resize
            self._alignment_cache = {
                "column_x": column_x,
            }

            # Store for later recalculation (resize, font changes)
            self._pairs = pairs
            self._radios = radios

            # Connect mode toggles to also hide/show the right labels
            # Avoid shadowing the outer-scope variable name "lbl" used above
            def _show_right_labels(_b: Any) -> None:
                for label in self._right_labels:
                    label.show()
            def _hide_right_labels(_b: Any) -> None:
                for label in self._right_labels:
                    label.hide()

            rb5.clicked.connect(_show_right_labels)
            rb6.clicked.connect(_hide_right_labels)
        except (RuntimeError, AttributeError, TypeError, ValueError, IndexError):
            # If anything goes wrong, leave the default texts in place.
            self._right_labels = []
            self._pairs = []  # type: ignore[assignment]
            self._radios = ()  # type: ignore[assignment]

        # Schedule a post-layout alignment to account for any geometry changes after show
        try:
            from PySide6.QtCore import QTimer  # local import to avoid polluting the module top
            QTimer.singleShot(0, self._reposition_right_labels)
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
            pass

        # checks[0] is 1-4 for radiobuttons 1 to 4
        # checks[1] is 0-1 for checkBox
        # checks[2] is 5-6 for radiobuttons 5 & 6
        self.checks = [1, 0, 5]

        # Load window geometry from settings
        try:
            gx, gy, gw, gh = self.settings_service.get_window_geometry("find_window")
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError, AttributeError):
            self.setGeometry(700, 300, 400, 378)

        le1.setToolTip("press RETURN to find")
        le1.returnPressed.connect(self.getter)
        le1.setClearButtonEnabled(False)
        le1.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Associate label mnemonic with the line edit (moved from ui_find.py)
        lab_buddy.setBuddy(le1)

        pb1.clicked.connect(lambda _b: le1.clear())
        # Mirror Designer-time connections previously in ui_find.py
        rb5.clicked.connect(lambda _b: rb4.show())
        rb5.clicked.connect(lambda _b: rb3.show())
        rb5.clicked.connect(lambda _b: rb2.show())
        rb5.clicked.connect(lambda _b: rb1.show())
        rb6.clicked.connect(lambda _b: rb1.hide())
        rb6.clicked.connect(lambda _b: rb2.hide())
        rb6.clicked.connect(lambda _b: rb3.hide())
        rb6.clicked.connect(lambda _b: rb4.hide())

        # Populate book range comboboxes from the parent window state
        if hasattr(self._main, "nwin") and isinstance(self._main.nwin, list):
            cb1.addItems(self._main.nwin)
            cb2.addItems(self._main.nwin)
        cb1.setCurrentIndex(0)
        # Expect BOOKS_IN_THE_BIBLE - 1 as the last index
        try:
            from abib.core.shared import BOOKS_IN_THE_BIBLE  # local import to avoid heavy module import at the top
            cb2.setCurrentIndex(BOOKS_IN_THE_BIBLE - 1)
        except (ImportError, TypeError, ValueError):
            # Fallback if constant not available for any reason
            if cb2.count() > 0:
                cb2.setCurrentIndex(cb2.count() - 1)

        # Enforce range rules dynamically: start (comboBox_1) must be <= end (comboBox_2), 
        # and the end dropdown must reflect this by disabling invalid items.
        # Connect handlers and initialise once.
        cb1.currentIndexChanged.connect(self._on_start_changed)
        cb2.currentIndexChanged.connect(self._on_end_changed)
        self._apply_end_constraints()

        QOk = QDialogButtonBox.StandardButton.Ok
        bb.button(QOk).setEnabled(True)
        bb.button(QOk).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bb.button(QOk).clicked.connect(lambda _b: self.getter())
        QCancel = QDialogButtonBox.StandardButton.Cancel
        bb.button(QCancel).setEnabled(True)
        bb.button(QCancel).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Use parent's close handler
        if hasattr(self._main, "close_find_window"):
            bb.button(QCancel).clicked.connect(lambda _b: self._main.close_find_window())

        le1.setFocus()

        cb1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cb2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rb1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rb2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rb3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rb4.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rb5.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rb6.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        chk.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        le1.textChanged.connect(lambda _t: le1.setFocus())
        pb1.hide()

        # Dynamically show/hide the clear button based on text presence
        le1.textChanged.connect(lambda _t: self.toggle_clear_button())

    # --- Layout maintenance for aligned right-hand labels ---
    def _reposition_right_labels(self) -> None:
        try:
            if not getattr(self, "_right_labels", None) or not getattr(self, "_pairs", None):
                return
            radios = getattr(self, "_radios", ())
            if not radios:
                return
            prop_font = self.font()
            fm = QFontMetrics(prop_font)
            max_left_px = max(fm.horizontalAdvance(left) for left, _ in self._pairs)
            gutter_px = max(6, fm.horizontalAdvance("  "))
            extra_pad_px = max(12, fm.horizontalAdvance("    "))
            style = self.style()
            indicator_w = style.pixelMetric(QStyle.PixelMetric.PM_ExclusiveIndicatorWidth, None, radios[0])
            spacing = style.pixelMetric(QStyle.PixelMetric.PM_CheckBoxLabelSpacing, None, radios[0])
            radios_x = min(rb.geometry().x() for rb in radios)
            text_start_x = radios_x + max(0, indicator_w) + max(0, spacing)
            column_x = int(text_start_x + max_left_px + gutter_px + extra_pad_px)
            # Move labels
            for rb, lbl in zip(radios, self._right_labels):
                # Use local references with type hints to satisfy strict static analysis
                # and avoid 'Never' type narrowing in the loop.
                r_obj: Any = rb
                l_obj: Any = lbl
                g = r_obj.geometry()
                l_obj.setGeometry(column_x, g.y(), max(10, self.width() - column_x - 10), g.height())
                l_obj.setFont(prop_font)
                # Keep visibility consistent with radio
                l_obj.setVisible(r_obj.isVisible())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._reposition_right_labels()

    def toggle_clear_button(self) -> None:
        assert self.ui.lineEdit_1 is not None
        assert self.ui.pushButton_1 is not None
        le1: Any = self.ui.lineEdit_1
        pb1: Any = self.ui.pushButton_1
        if le1.text():
            pb1.show()
            le1.setFocus()
        else:
            pb1.hide()
            le1.setFocus()

    def getter(self) -> None:
        """Get values from the find window and transfer to findf3 on the parent."""
        assert self.ui.lineEdit_1 is not None
        le1: Any = self.ui.lineEdit_1
        key = le1.text()
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
        assert self.ui.comboBox_1 is not None
        assert self.ui.comboBox_2 is not None
        cb1: Any = self.ui.comboBox_1
        cb2: Any = self.ui.comboBox_2
        i: int = cb1.currentIndex()
        j: int = cb2.currentIndex()
        if i > j:
            i, j = j, i
            cb1.setCurrentIndex(i)
            cb2.setCurrentIndex(j)
        return i, j

    # ---- Range constraints helpers ----
    def _apply_end_constraints(self) -> None:
        """Disable items in the end combo that are before the current start index.

        This makes the rule (start <= end) visible in the dropdown list.
        """
        assert self.ui.comboBox_1 is not None
        assert self.ui.comboBox_2 is not None
        cb1: Any = self.ui.comboBox_1
        cb2: Any = self.ui.comboBox_2

        start_idx = max(0, cb1.currentIndex())
        count = cb2.count()
        model = cb2.model()
        for k in range(count):
            enabled = k >= start_idx
            # Prefer QStandardItemModel-style enable/disable if available
            try:
                item = getattr(model, "item")(k)
            except (AttributeError, TypeError):
                item = None
            if item is not None:
                item_obj: Any = item
                try:
                    item_obj.setEnabled(bool(enabled))
                    # Also affect selection to reflect the disabled state in the popup
                    item_obj.setSelectable(bool(enabled))
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    # If anything goes wrong, silently ignore; snapping logic below enforces validity
                    pass
            else:
                # Fallback: if the underlying model does not expose items (custom model),
                # skip visual disabling and rely on snapping logic to enforce correctness.
                # (Generic QAbstractItemModel does not provide a way to change flags directly.)
                pass
        # If the current end is now invalid, snap it to start
        end_idx = cb2.currentIndex()
        if 0 <= end_idx < start_idx:
            # Prevent signal loops while adjusting
            bs = cb2.blockSignals(True)
            try:
                cb2.setCurrentIndex(start_idx)
            finally:
                cb2.blockSignals(bs)

    def _on_start_changed(self, _index: int) -> None:
        """When the start changes, update the end combo list and selection."""
        # Ensure end >= start
        self._apply_end_constraints()

    def _on_end_changed(self, index: int) -> None:
        """When the end changes, ensure it is not less than the start."""
        assert self.ui.comboBox_1 is not None
        assert self.ui.comboBox_2 is not None
        cb1: Any = self.ui.comboBox_1
        cb2: Any = self.ui.comboBox_2

        start_idx = cb1.currentIndex()
        if index < start_idx:
            bs = cb2.blockSignals(True)
            try:
                cb2.setCurrentIndex(start_idx)
            finally:
                cb2.blockSignals(bs)

    def check_changed(self) -> None:
        """Ensure that the checkBox is correct."""
        assert self.ui.checkBox is not None
        chk: Any = self.ui.checkBox
        self.checks[1] = 1 if chk.isChecked() else 0

    def radiobutton1_4_changed(self) -> None:
        """Ensure that radiobuttons 1 to 4 are correct."""
        assert self.ui.radiobutton_1 is not None
        assert self.ui.radiobutton_2 is not None
        assert self.ui.radiobutton_3 is not None
        assert self.ui.radiobutton_4 is not None
        rb1: Any = self.ui.radiobutton_1
        rb2: Any = self.ui.radiobutton_2
        rb3: Any = self.ui.radiobutton_3
        rb4: Any = self.ui.radiobutton_4

        if rb1.isChecked():
            self.checks[0] = 1
        elif rb2.isChecked():
            self.checks[0] = 2
        elif rb3.isChecked():
            self.checks[0] = 3
        elif rb4.isChecked():
            self.checks[0] = 4

    def radiobutton5_6_changed(self) -> None:
        """Ensure that radiobuttons 5 & 6 are correct."""
        assert self.ui.radiobutton_1 is not None
        assert self.ui.radiobutton_6 is not None
        rb1: Any = self.ui.radiobutton_1
        rb6: Any = self.ui.radiobutton_6

        if rb6.isChecked():
            self.checks[2] = 6
            rb1.setChecked(True)
            self.checks[0] = 1
        else:
            self.checks[2] = 5

    def get_checks(self) -> None:
        """Store the states of the checkboxes in the list checks."""
        self.checks = [1, 0, 5]
        self.check_changed()
        self.radiobutton1_4_changed()
        self.radiobutton5_6_changed()

    def closeEvent(self, event):
        """Handle window close event - save geometry"""
        try:
            geometry = self.geometry()
            self.settings_service.save_window_geometry(
                "find_window",
                geometry.x(),
                geometry.y(),
                geometry.width(),
                geometry.height(),
            )
        except (RuntimeError, TypeError, ValueError, AttributeError):
            pass
        super().closeEvent(event)
