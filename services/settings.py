# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import fcs
import shared as sh

__all__ = ["SettingsPaths", "SettingsService"]


@dataclass
class SettingsPaths:
    user_dir: Path
    settings_file: Path


class SettingsService:
    """Encapsulate reading/writing user settings and window geometry.

    This service delegates to existing `fcs` helpers but provides a single
    place to manage the user settings path and the in-memory settings dict.
    """

    def __init__(self, user_dir: Optional[Path] = None, filename: str = "settings.json") -> None:
        self.paths = SettingsPaths(
            user_dir=user_dir or sh.user_settings_dir,
            settings_file=(user_dir or sh.user_settings_dir) / filename,
        )
        # Ensure settings exist on disk
        if not self.paths.settings_file.exists():
            assert self.paths.user_dir is not None
            u_dir: Path = self.paths.user_dir
            fcs.setup_Abib_settings(u_dir)
        # Cached settings dict
        self._settings: Dict[str, Any] = {}

    # ---- Basic properties ----
    @property
    def user_settings_path(self) -> Path:
        return self.paths.settings_file

    @property
    def settings(self) -> Dict[str, Any]:
        # Lazy load on first access
        if not self._settings:
            self._settings = self.load()
        return self._settings

    # ---- Operations ----
    def load(self) -> Dict[str, Any]:
        path_str = str(self.paths.settings_file)
        self._settings = fcs.load_settings_from_file(path_str)

        # Synchronise the "show_work" map with files present in "Other Works".
        try:
            other_works_dir: Path = Path(sh.str_cwd) / "Other Works"
            stems_on_disk = set(
                p.stem for p in other_works_dir.glob("*.txt") if p.is_file()
            )
        except (OSError, TypeError, ValueError):
            stems_on_disk = set()

        show_map: Dict[str, Any] = dict(self._settings.get("show_work") or {})
        changed = False

        # Add new entries defaulting to "true" so all works are visible by default.
        # Users can hide individual items later via the Settings submenu.
        for stem in stems_on_disk:
            if stem not in show_map:
                show_map[stem] = "true"
                changed = True

        # Remove entries no longer present on disk
        for stale in list(show_map.keys() - stems_on_disk):
            show_map.pop(stale, None)
            changed = True

        if changed:
            self._settings["show_work"] = show_map
            # Persist the synchronised settings
            fcs.save_settings_to_file(self._settings, path_str)
        return self._settings

    def save(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Persist settings to disk using a robust merge to avoid data loss."""
        # Use the provided settings dict or fall back to the cached internal one
        source = settings if settings is not None else self._settings
        if source is None:
            source = {}

        # Robust merge: reload from disk and update with current changes
        try:
            on_disk = fcs.load_settings_from_file(str(self.paths.settings_file))
            on_disk.update(source)
            final_to_save = on_disk
        except (OSError, ValueError):
            final_to_save = source

        fcs.save_settings_to_file(final_to_save, str(self.paths.settings_file))

        # Synchronise the internal cache IN-PLACE.
        # This ensures that all UI components holding a reference to self.settings (via SettingsService.settings)
        # immediately see the merged, up-to-date values.
        if final_to_save is not self._settings:
            self._settings.update(final_to_save)

    # ---- Window geometry helpers ----
    def get_window_geometry(self, window_name: str) -> Tuple[int, int, int, int]:
        return fcs.get_window_geometry(window_name, str(self.paths.settings_file))

    def save_window_geometry(self, window_name: str, x: int, y: int, width: int, height: int) -> None:
        if window_name not in self.settings:
            self.settings[window_name] = {}
        self.settings[window_name].update({
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height)
        })
        self.save()

    # ---- Optional font helpers passthrough ----
    def get_bible_font_size(self) -> int:
        return int(self.settings.get("bible_font_size", 12))

    def update_bible_font_size(self, new_size: int) -> None:
        self.settings["bible_font_size"] = int(new_size)
        self._update_all_fonts_if_unified(new_size)
        self.save()

    def get_devotional_font_size(self) -> int:
        return int(self.settings.get("devotional_font_size", 14))

    def update_devotional_font_size(self, new_size: int) -> None:
        self.settings["devotional_font_size"] = int(new_size)
        self._update_all_fonts_if_unified(new_size)
        self.save()

    def get_reader_font_size(self) -> int:
        return int(self.settings.get("reader_font_size", 12))

    def update_reader_font_size(self, new_size: int) -> None:
        self.settings["reader_font_size"] = int(new_size)
        self._update_all_fonts_if_unified(new_size)
        self.save()

    def get_last_bible_position(self) -> int:
        return int(self.settings.get("last_bible_position", 0))

    def update_last_bible_position(self, pos: int) -> None:
        self.settings["last_bible_position"] = int(pos)
        self.save()

    # ---- Gill Commentary font helpers ----
    def get_commentary_font_size(self) -> int:
        val = self.settings.get("gill_font_size")
        if val is None:
            val = self.settings.get("gill_commentary_font_size", 12)
        # Type narrowing for static analysis using local reference pattern
        v: Any = val
        return int(v)

    def update_commentary_font_size(self, new_size: int) -> None:
        self.settings["gill_font_size"] = int(new_size)
        # Clean up legacy key if present
        self.settings.pop("gill_commentary_font_size", None)
        self._update_all_fonts_if_unified(new_size)
        self.save()

    def _update_all_fonts_if_unified(self, new_size: int) -> None:
        if bool(self.settings.get("unified_font_size", False)):
            size = int(new_size)
            self.settings["bible_font_size"] = size
            self.settings["reader_font_size"] = size
            self.settings["devotional_font_size"] = size
            self.settings["gill_font_size"] = size
            self.settings.pop("gill_commentary_font_size", None)

    # ---- Gill Commentary behaviour toggles ----
    # Auto-follow support removed.

    # ---- Gill Commentary: popups master toggle ----
    def get_gill_show_popups(self) -> bool:
        """Return whether Gill scripture popups are enabled. Defaults to True."""
        try:
            val = self.settings.get("gill_show_popups", True)
            if isinstance(val, bool):
                return val
            # Accept common truthy strings
            return str(val).lower() not in ("false", "0", "no", "off")
        except (AttributeError, TypeError, ValueError):
            return True

    def set_gill_show_popups(self, enabled: bool) -> None:
        try:
            self.settings["gill_show_popups"] = bool(enabled)
            self.save(self.settings)
        except (RuntimeError, TypeError, ValueError, OSError, PermissionError):
            pass

    # ---- Gill Commentary popup timing ----
    def get_gill_hover_delay_ms(self) -> int:
        """Return hover delay in milliseconds for Gill popups.
        Defaults to 120 ms if not set or invalid.
        """
        try:
            val = int(self.settings.get("gill_hover_delay_ms", 120))
        except (TypeError, ValueError):
            val = 120
        # Clamp to reasonable bounds
        if val < 0:
            val = 0
        if val > 5000:
            val = 5000
        return val

    def set_gill_hover_delay_ms(self, delay_ms: int) -> None:
        try:
            d = int(delay_ms)
        except (TypeError, ValueError):
            d = 120
        if d < 0:
            d = 0
        if d > 5000:
            d = 5000
        try:
            self.settings["gill_hover_delay_ms"] = d
            self.save(self.settings)
        except (RuntimeError, TypeError, ValueError, OSError, PermissionError):
            pass

    def get_gill_hide_delay_ms(self) -> int:
        """Return hide delay in milliseconds for Gill popups.
        Defaults to 160 ms if not set or invalid.
        """
        try:
            val = int(self.settings.get("gill_hide_delay_ms", 160))
        except (TypeError, ValueError):
            val = 160
        if val < 0:
            val = 0
        if val > 5000:
            val = 5000
        return val

    def set_gill_hide_delay_ms(self, delay_ms: int) -> None:
        try:
            d = int(delay_ms)
        except (TypeError, ValueError):
            d = 160
        if d < 0:
            d = 0
        if d > 5000:
            d = 5000
        try:
            self.settings["gill_hide_delay_ms"] = d
            self.save(self.settings)
        except (RuntimeError, TypeError, ValueError, OSError, PermissionError):
            pass
