from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import shared as sh

try:
    # Import lazily available pygame mixer
    from pygame import mixer as _mixer  # type: ignore
except Exception:  # pragma: no cover
    _mixer = None  # type: ignore


@dataclass
class AudioConfig:
    sound_filename: str = "sound.mp3"
    volume: float = 0.5  # 50%


class AudioService:
    """Tiny wrapper around pygame.mixer to play short UI sounds.

    - Lazy-initializes the mixer on first use.
    - Loads the sound file from the application base directory.
    - Fails gracefully if pygame or the sound file is unavailable.
    """

    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or AudioConfig()
        self._initialized = False
        self._load_failed = False
        self._sound = None

    def _init(self) -> None:
        if self._initialized or self._load_failed:
            return
        if _mixer is None:
            self._load_failed = True
            return
        try:
            _mixer.init()
            self._initialized = True
        except Exception:
            self._load_failed = True

    def _ensure_sound_loaded(self) -> None:
        if self._load_failed:
            return
        if not self._initialized:
            self._init()
        if self._load_failed or not self._initialized or self._sound is not None:
            return
        try:
            sound_path = Path(sh.base_dir) / self.config.sound_filename
            self._sound = _mixer.Sound(str(sound_path))  # type: ignore[attr-defined]
            self._sound.set_volume(self.config.volume)
        except Exception:
            self._load_failed = True
            self._sound = None

    def play_error(self) -> None:
        """Play the error/beep sound if available. Non-blocking, no exceptions."""
        self._ensure_sound_loaded()
        try:
            if self._sound is not None:
                self._sound.play()
        except Exception:
            # Swallow all audio errors to not impact UX
            pass
