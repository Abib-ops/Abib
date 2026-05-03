# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any, Optional
from pathlib import Path
import json
import shared as sh

class SettingsService:
    """Service to handle application settings persistence and migration."""
    
    def __init__(self, filename: str = "settings.json") -> None:
        self.filename = filename
        self.settings_dir = Path(sh.user_settings_dir)
        self.full_path = self.settings_dir / self.filename
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self.full_path.parent.mkdir(parents=True, exist_ok=True)

    def get_default_settings(self) -> dict[str, Any]:
        """Returns the default settings dictionary."""
        # This currently lives in fcs.py, but we'll eventually move it here or to a config module.
        import fcs
        return fcs.get_default_settings()

    def load(self) -> dict[str, Any]:
        """Load settings from file with fallback to defaults."""
        defaults = self.get_default_settings()
        
        if not self.full_path.exists():
            return defaults

        try:
            with open(self.full_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return defaults
                data = json.loads(content)
                
                # Merge defaults into loaded data
                self._merge_defaults(data, defaults)
                
                # Migrate and cleanup if needed
                if self._migrate(data):
                    self.save(data)
                    
                return data
        except (json.JSONDecodeError, OSError, UnicodeDecodeError, PermissionError):
            return defaults

    def save(self, settings: dict[str, Any]) -> None:
        """Save settings to file."""
        try:
            with open(self.full_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except OSError:
            pass

    def _merge_defaults(self, data: dict[str, Any], defaults: dict[str, Any]) -> None:
        for key, value in defaults.items():
            if isinstance(value, dict):
                if key not in data:
                    data[key] = value
                else:
                    for sub_key, sub_value in value.items():
                        data[key].setdefault(sub_key, sub_value)
            else:
                data.setdefault(key, value)

    def _migrate(self, data: dict[str, Any]) -> bool:
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
        """Helper to get window geometry with sensible defaults."""
        data = self.load()
        win = data.get(window_name, {})
        return (
            win.get("x", 100),
            win.get("y", 100),
            win.get("width", 737),
            win.get("height", 518)
        )

    def get_last_bible_position(self) -> int:
        """Get the last bible position from settings."""
        data = self.load()
        return data.get("last_bible_position", 0)

    def save_last_bible_position(self, position: int) -> None:
        """Save the last bible position to settings."""
        data = self.load()
        data["last_bible_position"] = position
        self.save(data)
