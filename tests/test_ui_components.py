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
