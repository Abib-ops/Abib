# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt, QThreadPool, QRunnable, QObject, Signal

from abib.core import shared as sh

from abib.services.settings import SettingsService
from abib.services.data_loader import DataLoader


# We purposefully import the Abib module so we can assign globals
# that its functions expect (e.g. KJV, Amap, EOTNOC, etc.).
from abib import Abib as AbibModule
from abib.Abib import MainWindow


def _show_splash_if_enabled(settings: Dict[str, Any]) -> QSplashScreen | None:
    """Create and show the splash screen if enabled in settings, returning it to keep it alive.
    The caller is responsible for finishing/closing it once the main window is ready.
    """
    if not settings.get("show_splash", False):
        return None
    splash_path = sh.images_dir / "Abib_barley.png"
    pix = QPixmap(str(splash_path))
    # Use size().isEmpty() to test validity to avoid stub/type warnings on isNull()
    splash = QSplashScreen(pix) if not pix.size().isEmpty() else QSplashScreen()
    # Allow clicks to pass through so the user can interact with the main window beneath
    try:
        splash.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    except (AttributeError, TypeError, RuntimeError):
        # Ignore if the attribute is unavailable or not supported on this platform/Qt version
        pass
    splash.show()
    return splash


def _init_screen_metrics(app: QApplication) -> None:
    # Set global width/height used by Abib.sizer
    width, height = app.primaryScreen().size().toTuple()
    # print(f"DEBUG: Screen size: {width}x{height}")
    # Expose to Abib module for sizer()
    AbibModule.width = width
    AbibModule.height = height
    AbibModule.half_width = width / 2
    AbibModule.half_height = height / 2


def _assign_attrs(module: Any, source: Any, names: list[str]) -> None:
    """Assign a list of attribute names from the source onto the module."""
    for name in names:
        setattr(module, name, getattr(source, name))


class _LoadSearchSignals(QObject):
    """Signals for background search index loading."""
    loaded = Signal(object)
    failed = Signal(str)


class _LoadSearchTask(QRunnable):
    """Background task to load search indexes without blocking the UI."""
    def __init__(self, loader: 'DataLoader') -> None:
        super().__init__()
        self.loader = loader
        self.signals = _LoadSearchSignals()

    def run(self) -> None:
        try:
            s = self.loader.load_search()
            self.signals.loaded.emit(s)
        except Exception as e:  # pragma: no cover - background error path
            try:
                self.signals.failed.emit(str(e))
            except (RuntimeError, TypeError):
                pass




def _load_bible_text_and_maps(loader: DataLoader) -> None:
    data = loader.load_bible()
    _assign_attrs(
        AbibModule,
        data,
        [
            "KJB_PCE_LASTLINE",
            "EOTNOC",
            "KJV",
            "Amap", "Amap_rev",
            "Ps119",
            "P119",
            "book_bounds",
            "starts_with_italics",
        ],
    )


def _load_search_indexes(loader: DataLoader) -> None:
    s = loader.load_search()
    _assign_attrs(
        AbibModule,
        s,
        [
            "Rnew",
            
            "Rlow",
            
            "Rstp",
            "Rlsp",
            "stripped_dict",
            "strpd_low_dict",
            "set_dict",
            "set_lowdict",
        ],
    )


def _load_sme_metadata(loader: DataLoader) -> None:
    # Retained for compatibility even though ReadingPlans handles SME now
    sme = loader.load_sme()
    AbibModule.sme_data = sme.data
    AbibModule.date_file = sme.date_file


def _init_window_runtime_state(w: MainWindow) -> None:
    # integers and runtime state used in highlighting and navigation
    w.y = 0
    w.hiLita.lineinc = 0
    w.hiLita.keyinc = 0
    w.hiLita.length = 1
    w.no_f3_yet = 0
    w.yend = 0
    w.finding = 0
    w.verse = 0
    w.occurring = 0
    w.occurrence = 0
    w.occur = []
    w.occurs = []
    w.count = []
    w.PCE_text = []
    w.key = ' '
    w.keym = ''
    w.message = ''
    w.store = ' '
    w.gent = None
    w.otherFileFlag = True

    # Colours
    AbibModule.linehighlightcolor = QColor("#0138b7")
    AbibModule.linetextcolor = QColor("#ffffff")


def run() -> None:
    app: QApplication = QApplication()
    app.setApplicationName("Abib")

    # Initialise settings service and load settings
    settings_service = SettingsService()
    settings: Dict[str, Any] = settings_service.settings

    splash = _show_splash_if_enabled(settings)
    # Expose splash so other modules (e.g. Settings) can control its lifetime
    AbibModule.splash = splash

    if sh.system() == 'Windows':
        app.processEvents()

    _init_screen_metrics(app)

    # Create the main window
    w: MainWindow = MainWindow()

    # Provide the settings path to windows that need to persist user settings
    w.user_settings_path = str(settings_service.user_settings_path)

    # Expose the window instance at module level for helpers
    AbibModule.w = w

    # Use centralised DataLoader
    loader = DataLoader()
    _load_bible_text_and_maps(loader)
    # Defer loading of heavy search indexes to a background thread (Step 1)
    # Keep SME metadata loading as-is (it's lightweight compared to search)
    _load_sme_metadata(loader)

    # Initialise runtime state on the window
    _init_window_runtime_state(w)

    # Open Bible text with the editor
    w.file_open(str(sh.base_dir / "KJB_PCE.txt"))

    # Set the application icon (optional but preserved)
    app_icon: QIcon = QIcon(str(sh.icon_path))
    app.setWindowIcon(app_icon)

    w.show()

    # Disable search in Other Works until indexes are ready, then load in the background
    try:
        w.update_other_works_search_button(False)
    except (RuntimeError, AttributeError, TypeError):
        pass

    pool = QThreadPool.globalInstance()
    task = _LoadSearchTask(loader)

    def _on_search_loaded(s: object) -> None:
        # Assign loaded search structures into the Abib module
        _assign_attrs(
            AbibModule,
            s,
            [
                "Rnew",
                
                "Rlow",
                
                "Rstp",
                "Rlsp",
                "stripped_dict",
                "strpd_low_dict",
                "set_dict",
                "set_lowdict",
            ],
        )
        # Enable the search controls now that indexes are ready
        try:
            w.update_other_works_search_button(True)
        except (RuntimeError, AttributeError, TypeError):
            pass

    # Optionally, you could connect failed to a logger/print; keep silent for minimal change
    task.signals.loaded.connect(_on_search_loaded)
    pool.start(task)

    # Keep the splash visible until the user disables it in Settings.
    # Do not auto-finish here.

    # Start the event loop
    from sys import exit as _exit
    _exit(app.exec())


if __name__ == "__main__":
    run()
