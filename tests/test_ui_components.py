# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


import unittest
from typing import cast
from unittest.mock import MagicMock, patch

# noinspection PyPackageRequirements
from PySide6.QtGui import QColor, QPalette

from abib.services.settings import SettingsService
from abib.ui.themes import ThemeManager, ThemeState
from abib.ui.ui_helpers import NoZoomPlainTextEdit, center_on_screen, fit_to_screen


class TestSettingsService(unittest.TestCase):
    def setUp(self):
        # Mock core.config.get_default_settings to avoid actual file I/O or dependencies
        self.patcher = patch('abib.core.config.get_default_settings')
        self.mock_defaults = self.patcher.start()
        self.mock_defaults.return_value = {
            "bible_font_size": 12,
            "last_bible_position": 0,
            "main_window": {"x": 10, "y": 20, "width": 100, "height": 200},
            "reader_font_size": 12,
            "gill_hover_delay_ms": 120
        }
        # Mock sh.user_settings_dir
        self.sh_patcher = patch('abib.core.shared.user_settings_dir', '/tmp/abib_test')
        self.sh_patcher.start()
        
        self.service = SettingsService("test_settings.json")
        # Mock load/save to avoid disk I/O
        self.service.load = MagicMock(return_value=self.mock_defaults.return_value.copy())
        self.service.save = MagicMock()

    def tearDown(self):
        self.patcher.stop()
        self.sh_patcher.stop()

    def test_get_bible_font_size_default(self):
        self.assertEqual(self.service.get_bible_font_size(), 12)

    def test_update_bible_font_size(self):
        self.service.update_bible_font_size(16)
        cast(MagicMock, self.service.save).assert_called_once()
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["bible_font_size"], 16)

    def test_get_last_bible_position(self):
        self.assertEqual(self.service.get_last_bible_position(), 0)

    def test_save_last_bible_position(self):
        self.service.update_last_bible_position(100)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["last_bible_position"], 100)

    def test_save_window_geometry(self):
        self.service.save_window_geometry("main_window", 50, 60, 800, 600)
        cast(MagicMock, self.service.save).assert_called()
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["main_window"], {"x": 50, "y": 60, "width": 800, "height": 600})

    def test_save_window_geometry_preserves_state_blob(self):
        # Saving plain x/y/w/h must not wipe an existing frame-aware state blob.
        self.service._cached_settings = {"main_window": {"state": "deadbeef"}}
        self.service.save_window_geometry("main_window", 50, 60, 800, 600)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(
            saved_data["main_window"],
            {"state": "deadbeef", "x": 50, "y": 60, "width": 800, "height": 600},
        )

    def test_get_window_geometry_uses_defaults_for_malformed_values(self):
        self.service._cached_settings = {
            "main_window": {"x": "bad", "y": None, "width": "bad", "height": None}
        }

        self.assertEqual(self.service.get_window_geometry("main_window"), (10, 20, 100, 200))

    def test_get_window_geometry_uses_defaults_for_non_dict_value(self):
        self.service._cached_settings = {"main_window": "invalid"}

        self.assertEqual(self.service.get_window_geometry("main_window"), (10, 20, 100, 200))

    def test_get_window_geometry_uses_defaults_for_out_of_range_values(self):
        self.service._cached_settings = {
            "main_window": {"x": 10000, "y": -10000, "width": 0, "height": 10001}
        }

        self.assertEqual(self.service.get_window_geometry("main_window"), (10, 20, 100, 200))

    def test_save_and_get_window_state(self):
        self.service.save_window_state("main_window", "cafe")
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["main_window"]["state"], "cafe")
        # Reading back from the cached settings returns the stored blob.
        self.assertEqual(self.service.get_window_state("main_window"), "cafe")

    def test_get_window_state_defaults_to_none(self):
        self.assertIsNone(self.service.get_window_state("main_window"))

    def test_get_devotional_font_size(self):
        self.assertEqual(self.service.get_devotional_font_size(), 12)

    def test_update_devotional_font_size(self):
        self.service.update_devotional_font_size(20)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["devotional_font_size"], 20)

    def test_get_commentary_font_size(self):
        self.assertEqual(self.service.get_commentary_font_size(), 12)

    def test_update_commentary_font_size(self):
        self.service.update_commentary_font_size(18)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["gill_font_size"], 18)

    def test_get_reader_font_size(self):
        self.assertEqual(self.service.get_reader_font_size(), 12)

    def test_update_reader_font_size(self):
        self.service.update_reader_font_size(14)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["reader_font_size"], 14)

    def test_get_gill_hover_delay_ms(self):
        self.assertEqual(self.service.get_gill_hover_delay_ms(), 120)

    def test_set_gill_hover_delay_ms(self):
        self.service.set_gill_hover_delay_ms(500)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["gill_hover_delay_ms"], 500)

    def test_get_gill_hide_delay_ms(self):
        self.assertEqual(self.service.get_gill_hide_delay_ms(), 160)

    def test_set_gill_hide_delay_ms(self):
        self.service.set_gill_hide_delay_ms(300)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["gill_hide_delay_ms"], 300)

    def test_get_search_results_width_default(self):
        self.assertEqual(self.service.get_search_results_width(), 400)

    def test_update_search_results_width(self):
        self.service.update_search_results_width(650)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertEqual(saved_data["search_results_width"], 650)

    def test_update_search_results_width_ignores_invalid(self):
        self.service.update_search_results_width(0)
        cast(MagicMock, self.service.save).assert_not_called()

    def test_get_search_results_width_ignores_invalid_stored(self):
        self.service.load = MagicMock(return_value={"search_results_width": -5})
        self.service._cached_settings = None
        self.assertEqual(self.service.get_search_results_width(), 400)

    def test_get_gill_show_popups(self):
        self.assertTrue(self.service.get_gill_show_popups())

    def test_set_gill_show_popups(self):
        self.service.set_gill_show_popups(False)
        saved_data = cast(MagicMock, self.service.save).call_args[0][0]
        self.assertFalse(saved_data["gill_show_popups"])

class TestSearchResultsWindow(unittest.TestCase):
    @staticmethod
    def _make_window():
        from abib.ui.search_results import SearchResultsWindow
        service = MagicMock()
        window = SearchResultsWindow(None, service)
        return window, service

    def test_save_width_skips_when_hidden(self):
        # A window that was created but never shown (e.g. the user never ran a
        # search this session) reports Qt's small default width. Saving it on
        # application close must NOT overwrite the stored preference.
        window, service = self._make_window()
        try:
            self.assertFalse(window.isVisible())
            window.save_width()
            service.update_search_results_width.assert_not_called()
        finally:
            window.deleteLater()

    def test_save_width_skips_while_positioning(self):
        window, service = self._make_window()
        try:
            window.show()
            window._positioning = True
            window.save_width()
            service.update_search_results_width.assert_not_called()
        finally:
            window.close()
            window.deleteLater()

    def test_save_width_persists_when_visible(self):
        window, service = self._make_window()
        try:
            window.resize(650, 400)
            window.show()
            window.save_width()
            service.update_search_results_width.assert_called_once()
            args, _ = service.update_search_results_width.call_args
            self.assertEqual(args[0], window.width())
        finally:
            window.close()
            window.deleteLater()


class TestReaderFind(unittest.TestCase):
    """Regression tests for the Other Works reader Search (Find) dialog."""

    @staticmethod
    def _make_reader():
        from abib.ui.text_window import TextDocumentWindow
        service = SettingsService("test_reader_find_settings.json")
        window = TextDocumentWindow(settings_service=service)
        window.text_edit.setPlainText("alpha beta gamma\nbeta delta beta\nomega")
        return window

    @staticmethod
    def _reset_cursor_to_start(window):
        cursor = window.text_edit.textCursor()
        cursor.setPosition(0)
        window.text_edit.setTextCursor(cursor)

    def test_build_flags_returns_qt_find_flag(self):
        # Regression: build_flags previously returned a plain int (0), which
        # newer PySide6 rejects for QPlainTextEdit.find(), raising TypeError.
        # noinspection PyPackageRequirements
        from PySide6.QtGui import QTextDocument
        window = self._make_reader()
        try:
            window.show_find_dialog()
            dlg = window._find_dlg
            self.assertIsNotNone(dlg)
            assert dlg is not None
            flags = dlg.build_flags()
            self.assertIsInstance(flags, QTextDocument.FindFlag)
        finally:
            window.close()
            window.deleteLater()

    def test_find_next_selects_match(self):
        window = self._make_reader()
        try:
            self._reset_cursor_to_start(window)
            window.show_find_dialog()
            dlg = window._find_dlg
            assert dlg is not None
            dlg.edit.setText("beta")

            window.find_next()
            self.assertEqual(window.text_edit.textCursor().selectedText(), "beta")

            # A second Find Next advances to the following occurrence.
            first_pos = window.text_edit.textCursor().position()
            window.find_next()
            self.assertEqual(window.text_edit.textCursor().selectedText(), "beta")
            self.assertNotEqual(window.text_edit.textCursor().position(), first_pos)
        finally:
            window.close()
            window.deleteLater()

    def test_find_case_sensitive(self):
        window = self._make_reader()
        try:
            self._reset_cursor_to_start(window)
            window.show_find_dialog()
            dlg = window._find_dlg
            assert dlg is not None
            dlg.case_box.setChecked(True)
            dlg.edit.setText("BETA")
            window.find_next()
            self.assertEqual(window.text_edit.textCursor().selectedText(), "")
        finally:
            window.close()
            window.deleteLater()


class TestThemes(unittest.TestCase):
    def test_theme_manager_toggle(self):
        state = ThemeState(is_dark_mode=False)
        tm = ThemeManager(state)
        new_state = tm.toggle()
        self.assertTrue(new_state)
        self.assertTrue(tm.state.is_dark_mode)
        
        new_state = tm.toggle()
        self.assertFalse(new_state)
        self.assertFalse(tm.state.is_dark_mode)

    def test_theme_manager_build_palettes(self):
        tm = ThemeManager()
        dark_pal = tm._build_dark_palette()
        light_pal = tm._build_light_palette()
        self.assertIsInstance(dark_pal, QPalette)
        self.assertIsInstance(light_pal, QPalette)

        # Verify the key colours match the documented theme values
        self.assertEqual(dark_pal.color(QPalette.ColorRole.Window), QColor(18, 18, 18))
        self.assertEqual(dark_pal.color(QPalette.ColorRole.WindowText), QColor(240, 240, 240))
        self.assertEqual(light_pal.color(QPalette.ColorRole.Window), QColor(255, 255, 255))
        self.assertEqual(light_pal.color(QPalette.ColorRole.Text), QColor(0, 0, 0))

    def test_apply_to_editor_light(self):
        tm = ThemeManager(ThemeState(is_dark_mode=False))
        editor = MagicMock()
        tm.apply_to_editor(editor)
        editor.setStyleSheet.assert_called()
        args, _ = editor.setStyleSheet.call_args
        self.assertIn("background-color: #ffffff", args[0])

    def test_apply_to_editor_dark(self):
        tm = ThemeManager(ThemeState(is_dark_mode=True))
        editor = MagicMock()
        tm.apply_to_editor(editor)
        editor.setStyleSheet.assert_called()
        args, _ = editor.setStyleSheet.call_args
        self.assertIn("background-color: #121212", args[0])

class TestUIHelpers(unittest.TestCase):
    def test_center_on_screen(self):
        from abib import utils
        orig_get_screen_size = utils.get_screen_size
        utils.get_screen_size = lambda: (1920, 1080)
        try:
            x, y = center_on_screen(1000, 500)
            self.assertEqual(x, (1920 - 1000) // 2)
            self.assertEqual(y, (1080 - 500) // 2)
        finally:
            utils.get_screen_size = orig_get_screen_size

    def test_fit_to_screen(self):
        from abib import utils
        orig_get_screen_size = utils.get_screen_size
        utils.get_screen_size = lambda: (800, 600)
        try:
            # Too big
            w, h = fit_to_screen(1000, 1000)
            self.assertEqual(w, int(800 * 0.95))
            self.assertEqual(h, int(600 * 0.95))
            
            # Fits
            w, h = fit_to_screen(400, 400)
            self.assertEqual(w, 400)
            self.assertEqual(h, 400)
        finally:
            utils.get_screen_size = orig_get_screen_size

    def test_no_zoom_plain_text_edit_ignores_ctrl_wheel(self):
        # noinspection PyPackageRequirements
        from PySide6.QtCore import Qt

        # The code uses: Qt.KeyboardModifier.ControlModifier in event.modifiers()
        event = MagicMock()
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        edit = NoZoomPlainTextEdit()
        edit.wheelEvent(event)

        event.ignore.assert_called_once()

    def test_no_zoom_plain_text_edit_allows_normal_wheel(self):
        # noinspection PyPackageRequirements
        from PySide6.QtCore import Qt

        # noinspection PyPackageRequirements
        from PySide6.QtWidgets import QPlainTextEdit

        event = MagicMock()
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        edit = NoZoomPlainTextEdit()
        # Without Ctrl, the event must be passed on to the base class handler
        with patch.object(QPlainTextEdit, 'wheelEvent') as super_wheel:
            edit.wheelEvent(event)

        super_wheel.assert_called_once_with(event)
        self.assertFalse(event.ignore.called)

    def test_simple_scripture_popup_theme(self):
        from abib.ui.ui_helpers import SimpleScripturePopup
        popup = SimpleScripturePopup()
        
        # Mock the widgets
        popup._widget = MagicMock()
        popup._text = MagicMock()
        
        popup.apply_theme(is_dark=True)
        cast(MagicMock, popup._widget).setStyleSheet.assert_called()
        args, _ = cast(MagicMock, popup._widget).setStyleSheet.call_args
        self.assertIn("background-color: #121212", args[0])
        
        popup.apply_theme(is_dark=False)
        args, _ = cast(MagicMock, popup._widget).setStyleSheet.call_args
        self.assertIn("background-color: #ffffff", args[0])


    def test_simple_scripture_popup_parented_to_host_window(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QPlainTextEdit

        from abib.ui.ui_helpers import SimpleScripturePopup

        parent_window = QDialog()
        editor = QPlainTextEdit(parent_window)
        popup = SimpleScripturePopup()
        popup.ensure_created(editor)

        assert popup._widget is not None
        self.assertEqual(popup._widget.parentWidget(), parent_window)
        self.assertEqual(popup._widget.focusPolicy(), Qt.FocusPolicy.NoFocus)
        self.assertTrue(popup._widget.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))

    def test_simple_scripture_popup_reparents_when_host_changes(self):
        from PySide6.QtWidgets import QDialog, QPlainTextEdit

        from abib.ui.ui_helpers import SimpleScripturePopup

        first_window = QDialog()
        first_editor = QPlainTextEdit(first_window)
        second_window = QDialog()
        second_editor = QPlainTextEdit(second_window)
        popup = SimpleScripturePopup()

        popup.ensure_created(first_editor)
        assert popup._widget is not None
        self.assertEqual(popup._widget.parentWidget(), first_window)

        popup.ensure_created(second_editor)
        self.assertEqual(popup._widget.parentWidget(), second_window)

    def test_simple_scripture_popup_uses_host_screen_for_sizing(self):
        from PySide6.QtCore import QPoint, QSize
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QDialog, QPlainTextEdit

        from abib.ui.ui_helpers import SimpleScripturePopup

        parent_window = QDialog()
        parent_window.resize(600, 800)
        editor = QPlainTextEdit(parent_window)
        editor.setPlainText("In the beginning God created the heaven and the earth.\nGenesis 1:1")
        editor.resize(500, 700)

        mock_screen = MagicMock()
        mock_screen.size.return_value = QSize(1440, 900)
        editor.screen = MagicMock(return_value=mock_screen)

        popup = SimpleScripturePopup()
        _x, _y, width, height = popup.predict_geometry(
            editor, "Genesis 1:1 KJV\nIn the beginning", QPoint(10, 10), QFont()
        )
        self.assertEqual(width, 500)
        self.assertGreater(height, 0)
        self.assertLessEqual(height, int(900 * 0.6))
        assert popup._widget is not None
        self.assertEqual(popup._widget.parentWidget(), parent_window)

        popup.show(editor, "Genesis 1:1 KJV\nIn the beginning", QPoint(10, 10), QFont(), is_dark=False)
        self.assertEqual(popup._widget.parentWidget(), parent_window)
        self.assertEqual(popup._widget.width(), 500)
        self.assertLessEqual(popup._widget.height(), int(900 * 0.6))


class TestWindowGeometryPersistence(unittest.TestCase):
    def test_gill_window_geometry_persistence(self):
        from pathlib import Path

        from abib.ui.gill_window import GillCommentaryWindow

        settings_service = MagicMock()
        settings_service.get_window_geometry.return_value = (170, 180, 820, 640)
        settings_service.get_commentary_font_size.return_value = 12
        window = GillCommentaryWindow(Path("unused.sqlite"), settings_service=settings_service)
        try:
            settings_service.get_window_geometry.assert_called_with("gill_commentary_window")
            self.assertEqual((window.x(), window.y(), window.width(), window.height()), (170, 180, 820, 640))

            window._persist_geometry()
            settings_service.save_window_geometry.assert_called_with(
                "gill_commentary_window",
                window.geometry().x(),
                window.geometry().y(),
                window.geometry().width(),
                window.geometry().height(),
            )
        finally:
            window.close()
            window.deleteLater()

    def test_concordance_window_geometry_persistence(self):
        from abib.ui.concordance_window import ConcordanceWindow

        concordance_service = MagicMock()
        concordance_service.entries.return_value = ()
        settings_service = MagicMock()
        settings_service.get_window_geometry.return_value = (150, 160, 700, 550)

        window = ConcordanceWindow(concordance_service, settings_service=settings_service)
        try:
            settings_service.get_window_geometry.assert_called_with("concordance_window")
            self.assertEqual((window.x(), window.y(), window.width(), window.height()), (150, 160, 700, 550))

            window._persist_geometry()
            settings_service.save_window_geometry.assert_called_with(
                "concordance_window",
                window.geometry().x(),
                window.geometry().y(),
                window.geometry().width(),
                window.geometry().height(),
            )
        finally:
            window.close()
            window.deleteLater()

    def test_other_works_references_window_geometry_persistence(self):
        from abib.ui.other_works_references_window import OtherWorksReferencesWindow

        settings_service = MagicMock()
        settings_service.get_window_geometry.return_value = (110, 120, 550, 380)
        window = OtherWorksReferencesWindow(MagicMock(), settings_service=settings_service)
        try:
            settings_service.get_window_geometry.assert_called_with("other_works_references_window")
            self.assertEqual((window.x(), window.y(), window.width(), window.height()), (110, 120, 550, 380))

            window._persist_geometry()
            settings_service.save_window_geometry.assert_called_with(
                "other_works_references_window",
                window.geometry().x(),
                window.geometry().y(),
                window.geometry().width(),
                window.geometry().height(),
            )
        finally:
            window.close()
            window.deleteLater()

    def test_other_works_text_search_window_geometry_persistence(self):
        from abib.ui.other_works_text_search_window import OtherWorksTextSearchWindow

        settings_service = MagicMock()
        settings_service.get_window_geometry.return_value = (130, 140, 560, 390)
        window = OtherWorksTextSearchWindow(MagicMock(), settings_service=settings_service)
        try:
            settings_service.get_window_geometry.assert_called_with("other_works_text_search_window")
            self.assertEqual((window.x(), window.y(), window.width(), window.height()), (130, 140, 560, 390))

            window._persist_geometry()
            settings_service.save_window_geometry.assert_called_with(
                "other_works_text_search_window",
                window.geometry().x(),
                window.geometry().y(),
                window.geometry().width(),
                window.geometry().height(),
            )
        finally:
            window.close()
            window.deleteLater()


class TestScriptureLogic(unittest.TestCase):
    def test_lookup_scripture_dangling_hyphen(self):
        from abib.core.scripture import lookup_scripture
        bible_data = {
            "Genesis": {
                "1": {
                    "1": "In the beginning...",
                    "2": "And the earth..."
                }
            }
        }
        # "1--" should be treated as just verse 1
        res = lookup_scripture(bible_data, "Genesis", 1, "1--")
        self.assertEqual(res, "1 In the beginning...")

    def test_lookup_scripture_range(self):
        from abib.core.scripture import lookup_scripture
        bible_data = {
            "Genesis": {
                "1": {
                    "1": "v1",
                    "2": "v2",
                    "3": "v3"
                }
            }
        }
        res = lookup_scripture(bible_data, "Genesis", 1, "1-2")
        self.assertEqual(res, "1 v1\n2 v2")

    def test_lookup_scripture_list(self):
        from abib.core.scripture import lookup_scripture
        bible_data = {
            "Genesis": {
                "1": {
                    "1": "v1",
                    "2": "v2",
                    "3": "v3"
                }
            }
        }
        res = lookup_scripture(bible_data, "Genesis", 1, "1, 3")
        self.assertEqual(res, "1 v1\n3 v3")

if __name__ == "__main__":
    unittest.main()
