# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abib.core import shared as sh

# Prefer Qt's own lightweight audio for short UI sounds
try:  # pragma: no cover - import guarded for environments without Qt
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover
    QSoundEffect = None  # type: ignore
    QUrl = None  # type: ignore


@dataclass
class AudioConfig:
    sound_filename: str = "sound.wav"  # Use a small WAV for best cross-platform reliability
    volume: float = 0.5  # 0.0–1.0


class AudioService:
    """Play a short UI sound using Qt’s audio stack (QSoundEffect).

    - No external dependencies beyond PySide6.
    - Lazily loads the sound and keeps a persistent effect instance.
    - Fails gracefully if multimedia backends are unavailable.
    """

    def __init__(self, config: AudioConfig | None = None) -> None:
        self.config = config or AudioConfig()
        self._effect: Any = None
        self._load_failed: bool = False
        # Lazy load on first play

    def _ensure_loaded(self) -> None:
        if self._load_failed or self._effect is not None:
            return
        # If Qt Multimedia is not available, disable audio gracefully
        if QSoundEffect is None or QUrl is None:
            self._load_failed = True
            return
        try:
            effect = QSoundEffect()
            # Build file URL
            sound_path = Path(sh.base_dir) / self.config.sound_filename
            url = QUrl.fromLocalFile(str(sound_path))
            effect.setSource(url)
            # Volume range is 0.0–1.0
            try:
                effect.setVolume(float(self.config.volume))
            except (TypeError, ValueError, AttributeError):
                # Older bindings may use int 0–100; attempt fallback
                try:
                    effect.setVolume(int(self.config.volume * 100))  # type: ignore[arg-type]
                except (TypeError, ValueError, AttributeError):
                    pass
            # Keep a persistent instance so the backend stays initialised
            self._effect = effect
        except (RuntimeError, AttributeError, OSError):
            # Any failure here disables audio but must never crash the app
            self._effect = None
            self._load_failed = True

    def play_error(self) -> None:
        """Play the error/beep sound if available. Non-blocking, no exceptions."""
        self._ensure_loaded()
        try:
            if self._effect is not None:
                # Restart the effect if it is already playing to ensure a fresh clicky beep
                try:
                    if getattr(self._effect, "isPlaying", None) and self._effect.isPlaying():  # type: ignore[func-returns-value]
                        self._effect.stop()
                except (AttributeError, RuntimeError, TypeError):
                    # isPlaying() may not be present or may throw if the backend is missing
                    pass
                self._effect.play()
        except (RuntimeError, AttributeError):
            # Be tolerant: no audio should not impact UX
            pass
