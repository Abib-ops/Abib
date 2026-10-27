# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abib.core import shared as sh
from abib.utils import platform as plat

# Prefer Qt's own lightweight audio for short UI sounds
try:  # pragma: no cover - import guarded for environments without Qt
    # noinspection PyPackageRequirements
    from PySide6.QtCore import QUrl

    # noinspection PyPackageRequirements
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

    @property
    def _sound_path(self) -> Path:
        return Path(sh.base_dir) / self.config.sound_filename

    def _ensure_loaded(self) -> None:
        if self._load_failed or self._effect is not None:
            return
        # If Qt Multimedia is not available, disable the QSoundEffect backend.
        # A platform fallback (see _play_fallback) is still used, so the app
        # remains audible even without PySide6.QtMultimedia.
        if QSoundEffect is None or QUrl is None:
            self._load_failed = True
            return
        try:
            # QSoundEffect is guaranteed non-None here (guarded above), but the
            # module-level fallback assignment (QSoundEffect = None) makes static
            # checkers treat it as possibly None, so suppress the false positive.
            # noinspection PyCallingNonCallable
            effect = QSoundEffect()
            # Build file URL
            url = QUrl.fromLocalFile(str(self._sound_path))
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
        except (RuntimeError, AttributeError, OSError, TypeError):
            # Any failure here disables audio but must never crash the app.
            # TypeError guards against QSoundEffect being unexpectedly None
            # ("'NoneType' object is not callable") in broken/partial installs.
            self._effect = None
            self._load_failed = True

    def play_error(self) -> None:
        """Play the error/beep sound if available. Non-blocking, no exceptions."""
        try:
            self._ensure_loaded()
        except (RuntimeError, AttributeError, OSError, TypeError):
            # Loading must never crash the app; disable the backend and fall back.
            self._effect = None
            self._load_failed = True
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
                return
        except (RuntimeError, AttributeError, TypeError):
            # Be tolerant: no audio should not impact UX
            pass
        # QSoundEffect backend unavailable (e.g. PySide6.QtMultimedia is not
        # installed): fall back to a platform-native beep so there is still sound.
        self._play_fallback()

    def _play_fallback(self) -> None:
        """Best-effort, non-blocking sound without PySide6.QtMultimedia."""
        # On Windows, play the bundled WAV asynchronously via winsound.
        if plat.is_windows():
            try:
                import winsound
                sound_path = self._sound_path
                if sound_path.is_file():
                    winsound.PlaySound(
                        str(sound_path),
                        winsound.SND_FILENAME | winsound.SND_ASYNC,
                    )
                    return
                winsound.MessageBeep(winsound.MB_ICONHAND)
                return
            except (RuntimeError, OSError, ImportError):
                pass
        # Cross-platform fallback: use Qt's application-level beep if possible.
        try:
            # noinspection PyPackageRequirements
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                # beep() is a static method on QApplication; call it on the
                # class so static checkers don't flag QCoreApplication, which
                # QApplication.instance() is typed to return.
                QApplication.beep()
        except (ImportError, RuntimeError, AttributeError):
            pass
