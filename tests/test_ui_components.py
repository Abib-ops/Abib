# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock PySide6 BEFORE importing anything that uses it
mock_qt = MagicMock()
sys.modules['PySide6'] = mock_qt
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()

# Ensure QPlainTextEdit is a class we can instantiate
class MockQPlainTextEdit:
    def __init__(self, *args, **kwargs): pass
    def wheelEvent(self, event): pass
    def setStyleSheet(self, style): pass

sys.modules['PySide6.QtWidgets'].QPlainTextEdit = MockQPlainTextEdit

from ui.themes import ThemeManager, ThemeState
from ui_helpers import NoZoomPlainTextEdit, NoZoomDialog, center_on_screen, fit_to_screen
from services.settings import SettingsService

class TestSettingsService(unittest.TestCase):
    def setUp(self):
        # Mock fcs.get_default_settings to avoid actual file I/O or dependencies
        self.patcher = patch('fcs.get_default_settings')
        self.mock_defaults = self.patcher.start()
        self.mock_defaults.return_value = {
            "bible_font_size": 12,
            "last_bible_position": 0,
            "main_window": {"x": 10, "y": 20, "width": 100, "height": 200},
            "reader_font_size": 12,
            "gill_hover_delay_ms": 120
        }
        # Mock sh.user_settings_dir
        self.sh_patcher = patch('shared.user_settings_dir', '/tmp/abib_test')
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
        self.service.save.assert_called_once()
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["bible_font_size"], 16)

    def test_get_last_bible_position(self):
        self.assertEqual(self.service.get_last_bible_position(), 0)

    def test_save_last_bible_position(self):
        self.service.update_last_bible_position(100)
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["last_bible_position"], 100)

    def test_save_window_geometry(self):
        self.service.save_window_geometry("main_window", 50, 60, 800, 600)
        self.service.save.assert_called()
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["main_window"], {"x": 50, "y": 60, "width": 800, "height": 600})

    def test_get_devotional_font_size(self):
        self.assertEqual(self.service.get_devotional_font_size(), 12)

    def test_update_devotional_font_size(self):
        self.service.update_devotional_font_size(20)
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["devotional_font_size"], 20)

    def test_get_commentary_font_size(self):
        self.assertEqual(self.service.get_commentary_font_size(), 12)

    def test_update_commentary_font_size(self):
        self.service.update_commentary_font_size(18)
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["gill_font_size"], 18)

    def test_get_reader_font_size(self):
        self.assertEqual(self.service.get_reader_font_size(), 12)

    def test_update_reader_font_size(self):
        self.service.update_reader_font_size(14)
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["reader_font_size"], 14)

    def test_get_gill_hover_delay_ms(self):
        self.assertEqual(self.service.get_gill_hover_delay_ms(), 120)

    def test_set_gill_hover_delay_ms(self):
        self.service.set_gill_hover_delay_ms(500)
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["gill_hover_delay_ms"], 500)

    def test_get_gill_hide_delay_ms(self):
        self.assertEqual(self.service.get_gill_hide_delay_ms(), 160)

    def test_set_gill_hide_delay_ms(self):
        self.service.set_gill_hide_delay_ms(300)
        saved_data = self.service.save.call_args[0][0]
        self.assertEqual(saved_data["gill_hide_delay_ms"], 300)

    def test_get_gill_show_popups(self):
        self.assertTrue(self.service.get_gill_show_popups())

    def test_set_gill_show_popups(self):
        self.service.set_gill_show_popups(False)
        saved_data = self.service.save.call_args[0][0]
        self.assertFalse(saved_data["gill_show_popups"])

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
        # These should return objects (which are mocks in this test)
        dark_pal = tm._build_dark_palette()
        light_pal = tm._build_light_palette()
        self.assertIsNotNone(dark_pal)
        self.assertIsNotNone(light_pal)
        
        # Verify setColor was called (even if on mocks)
        self.assertTrue(dark_pal.setColor.called)
        self.assertTrue(light_pal.setColor.called)

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
        import fcs
        orig_get_screen_size = fcs.get_screen_size
        fcs.get_screen_size = lambda: (1920, 1080)
        try:
            x, y = center_on_screen(1000, 500)
            self.assertEqual(x, (1920 - 1000) // 2)
            self.assertEqual(y, (1080 - 500) // 2)
        finally:
            fcs.get_screen_size = orig_get_screen_size

    def test_fit_to_screen(self):
        import fcs
        orig_get_screen_size = fcs.get_screen_size
        fcs.get_screen_size = lambda: (800, 600)
        try:
            # Too big
            h, w = fit_to_screen(1000, 1000)
            self.assertEqual(h, int(600 * 0.95))
            self.assertEqual(w, int(800 * 0.95))
            
            # Fits
            h, w = fit_to_screen(400, 400)
            self.assertEqual(h, 400)
            self.assertEqual(w, 400)
        finally:
            fcs.get_screen_size = orig_get_screen_size

    def test_no_zoom_plain_text_edit_ignores_ctrl_wheel(self):
        # We need to mock the event
        event = MagicMock()
        # Mock modifiers to contain ControlModifier
        # In PySide6, modifiers() returns a Flag object. 
        # Since we mocked Qt, we need to make sure the 'in' check works or we mock it appropriately.
        # The code uses: Qt.KeyboardModifier.ControlModifier in event.modifiers()
        
        # Setup the mock for event.modifiers()
        modifiers = MagicMock()
        # Make 'ControlModifier in modifiers' return True
        # Since Qt is mocked, Qt.KeyboardModifier.ControlModifier is a mock.
        # modifiers.__contains__ should return True when called with that mock.
        modifiers.__contains__.return_value = True
        event.modifiers.return_value = modifiers
        
        edit = NoZoomPlainTextEdit()
        edit.wheelEvent(event)
        
        event.ignore.assert_called_once()
        # Should NOT call super().wheelEvent(event). 
        # But wait, we can't easily check super() call on a mock subclass without more setup.
        # At least we know ignore() was called.

    def test_no_zoom_plain_text_edit_allows_normal_wheel(self):
        event = MagicMock()
        modifiers = MagicMock()
        modifiers.__contains__.return_value = False
        event.modifiers.return_value = modifiers
        
        edit = NoZoomPlainTextEdit()
        # Mocking super().wheelEvent is tricky. 
        # Let's just ensure ignore() is NOT called.
        edit.wheelEvent(event)
        self.assertFalse(event.ignore.called)

    def test_simple_scripture_popup_theme(self):
        from ui_helpers import SimpleScripturePopup
        popup = SimpleScripturePopup()
        
        # Mock the widgets
        popup._widget = MagicMock()
        popup._text = MagicMock()
        
        popup.apply_theme(is_dark=True)
        popup._widget.setStyleSheet.assert_called()
        args, _ = popup._widget.setStyleSheet.call_args
        self.assertIn("background-color: #121212", args[0])
        
        popup.apply_theme(is_dark=False)
        args, _ = popup._widget.setStyleSheet.call_args
        self.assertIn("background-color: #ffffff", args[0])

class TestScriptureLogic(unittest.TestCase):
    def test_lookup_scripture_dangling_hyphen(self):
        from scripture import lookup_scripture
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
        from scripture import lookup_scripture
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
        from scripture import lookup_scripture
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
