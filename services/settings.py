from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import fcs
import shared as sh
from os import PathLike


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
            fcs.setup_Abib_settings(self.paths.user_dir)
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

        # Synchronize the "show_work" map with files present in "Other Works".
        try:
            other_works_dir: Path | str | PathLike[str] = Path(sh.str_cwd) / "Other Works"
            stems_on_disk = set(
                p.stem for p in Path(other_works_dir).glob("*.txt") if p.is_file()
            )
        except Exception:
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
            # Persist the synchronized settings
            fcs.save_settings_to_file(self._settings, path_str)
        return self._settings

    def save(self, settings: Optional[Dict[str, Any]] = None) -> None:
        if settings is None:
            settings = self._settings
        if settings is None:
            settings = {}
        fcs.save_settings_to_file(settings, str(self.paths.settings_file))
        # Keep cache in sync
        self._settings = dict(settings)

    # ---- Window geometry helpers ----
    @staticmethod
    def get_window_geometry(window_name: str) -> Tuple[int, int, int, int]:
        return fcs.get_window_geometry(window_name)

    @staticmethod
    def save_window_geometry(window_name: str, x: int, y: int, width: int, height: int) -> None:
        fcs.save_window_geometry(window_name, x, y, width, height)

    # ---- Optional font helpers passthrough ----
    def get_bible_font_size(self) -> int:
        return fcs.get_bible_font_size(str(self.paths.settings_file))

    def update_bible_font_size(self, new_size: int) -> None:
        fcs.update_bible_font_size(new_size, str(self.paths.settings_file))

    def get_devotional_font_size(self) -> int:
        return fcs.get_devotional_font_size(str(self.paths.settings_file))

    def update_devotional_font_size(self, new_size: int) -> None:
        fcs.update_devotional_font_size(new_size, str(self.paths.settings_file))
