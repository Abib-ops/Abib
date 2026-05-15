# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any, Optional
from pathlib import Path
import json
from abib.core import shared as sh

class SettingsService:
    """Service to handle application settings persistence and migration."""
    
    def __init__(self, filename: str = "settings.json") -> None:
        self.filename = filename
        self.settings_dir = Path(sh.user_settings_dir)
        self.user_settings_path = self.settings_dir / self.filename
        self._ensure_dir()
        self._cached_settings: Optional[dict[str, Any]] = None

    def _ensure_dir(self) -> None:
        self.user_settings_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def settings(self) -> dict[str, Any]:
        """Lazy-loaded settings property."""
        if self._cached_settings is None:
            self._cached_settings = self.load()
        assert self._cached_settings is not None
        return self._cached_settings

    @staticmethod
    def get_default_settings() -> dict[str, Any]:
        """Returns the default settings dictionary."""
        from abib.core import config
        return config.get_default_settings()

    def load(self) -> dict[str, Any]:
        """Load settings from the file with fallback to defaults."""
        defaults = SettingsService.get_default_settings()
        
        if not self.user_settings_path.exists():
            print("Settings file does not exist. Using default settings.")
            return defaults

        try:
            with open(self.user_settings_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    print("Settings file is empty. Falling back to default settings.")
                    return defaults
                data = json.loads(content)
                
                # Merge defaults into loaded data
                SettingsService._merge_defaults(data, defaults)
                
                # Migrate and clean-up if needed
                if SettingsService._migrate(data):
                    self.save(data)
                    
                return data
        except json.JSONDecodeError:
            print("Settings file is malformed. Overwriting with default settings.")
            return defaults
        except (OSError, UnicodeDecodeError, PermissionError) as err:
            print(f"Error loading settings: {err}. Using default settings.")
            return defaults

    def save(self, settings: dict[str, Any]) -> None:
        """Save settings to a file."""
        try:
            with open(self.user_settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            self._cached_settings = settings
        except OSError as e1:
            print(f"Error saving settings to file: {e1}")

    @staticmethod
    def _merge_defaults(data: dict[str, Any], defaults: dict[str, Any]) -> None:
        for key, value in defaults.items():
            if isinstance(value, dict):
                if key not in data:
                    data[key] = value
                else:
                    for sub_key, sub_value in value.items():
                        data[key].setdefault(sub_key, sub_value)
            else:
                data.setdefault(key, value)

    @staticmethod
    def _migrate(data: dict[str, Any]) -> bool:
        """Handles settings migrations. Returns True if data was modified."""
        changed = False
        if "pilgrims_progress_window" in data:
            del data["pilgrims_progress_window"]
            changed = True
            
        if "gill_commentary_font_size" in data:
            if "gill_font_size" not in data:
                data["gill_font_size"] = data["gill_commentary_font_size"]
            del data["gill_commentary_font_size"]
            changed = True
            
        return changed

    def get_window_geometry(self, window_name: str) -> tuple[int, int, int, int]:
        """Helper to get window geometry with sensible defaults and multi-monitor aware clamping."""
        data = self.settings
        win = data.get(window_name, {})
        
        rx = win.get("x", 100)
        ry = win.get("y", 100)
        rw = win.get("width", 737)
        rh = win.get("height", 518)

        # Relaxed multi-monitor aware clamping (from fcs.py):
        # 1. Allow negative X/Y (secondary monitors to the left/top)
        # 2. Allow X/Y beyond primary width/height (secondary monitors to the right/bottom)
        # 3. Only clamp if the window is likely completely off-screen or excessively far.
        VIRTUAL_LIMIT = 10000 
        
        if not (-VIRTUAL_LIMIT < rx < VIRTUAL_LIMIT):
            rx = 100
        if not (-VIRTUAL_LIMIT < ry < VIRTUAL_LIMIT):
            ry = 100
        if rw <= 0 or rw > VIRTUAL_LIMIT:
            rw = 737
        if rh <= 0 or rh > VIRTUAL_LIMIT:
            rh = 518
            
        return rx, ry, rw, rh

    def save_window_geometry(self, window_name: str, x: int, y: int, width: int, height: int) -> None:
        """Save window geometry to settings."""
        data = self.load()
        data[window_name] = {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        self.save(data)

    def get_last_bible_position(self) -> int:
        """Get the last bible position from settings."""
        return self.settings.get("last_bible_position", 0)

    def update_last_bible_position(self, position: int) -> None:
        """Save the last bible position to settings."""
        data = self.load() # Use load to get fresh data before updating and saving
        data["last_bible_position"] = position
        self.save(data)

    def get_bible_font_size(self) -> int:
        """Get the bible font size from settings."""
        return self.settings.get("bible_font_size", 12)

    def update_bible_font_size(self, size: int) -> None:
        """Update the bible font size in settings."""
        data = self.load()
        data["bible_font_size"] = size
        self.save(data)

    def get_devotional_font_size(self) -> int:
        """Get the devotional font size from settings."""
        return self.settings.get("devotional_font_size", 12)

    def update_devotional_font_size(self, size: int) -> None:
        """Update the devotional font size in settings."""
        data = self.load()
        data["devotional_font_size"] = size
        self.save(data)

    def get_commentary_font_size(self) -> int:
        """Get the commentary font size from settings."""
        return self.settings.get("gill_font_size", 12)

    def update_commentary_font_size(self, size: int) -> None:
        """Update the commentary font size in settings."""
        data = self.load()
        data["gill_font_size"] = size
        self.save(data)

    def get_reader_font_size(self) -> int:
        """Get the reader font size from settings."""
        return self.settings.get("reader_font_size", 12)

    def update_reader_font_size(self, size: int) -> None:
        """Update the reader font size in settings."""
        data = self.load()
        data["reader_font_size"] = size
        self.save(data)

    def get_gill_hover_delay_ms(self) -> int:
        """Get the Gill hover delay in milliseconds."""
        return self.settings.get("gill_hover_delay_ms", 120)

    def set_gill_hover_delay_ms(self, delay: int) -> None:
        """Set the Gill hover delay in milliseconds."""
        data = self.load()
        data["gill_hover_delay_ms"] = delay
        self.save(data)

    def get_gill_hide_delay_ms(self) -> int:
        """Get the Gill hide delay in milliseconds."""
        return self.settings.get("gill_hide_delay_ms", 160)

    def set_gill_hide_delay_ms(self, delay: int) -> None:
        """Set the Gill hide delay in milliseconds."""
        data = self.load()
        data["gill_hide_delay_ms"] = delay
        self.save(data)

    def get_gill_show_popups(self) -> bool:
        """Get whether Gill popups should be shown."""
        return bool(self.settings.get("gill_show_popups", True))

    def set_gill_show_popups(self, enabled: bool) -> None:
        """Set whether Gill popups should be shown."""
        data = self.load()
        data["gill_show_popups"] = enabled
        self.save(data)
