from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set, List
from json import load, JSONDecodeError

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap, QColor

import shared as sh
import fcs

from services.settings import SettingsService
from services.data_loader import DataLoader
from updater import update_abib

# We purposefully import the Abib module so we can assign globals
# that its functions expect (e.g., KJV, Amap, EOTNOC, etc.).
import Abib as AbibModule
from Abib import MainWindow


def _show_splash_if_enabled(settings: Dict[str, Any]) -> None:
    splash_path = sh.current_directory / "images" / "Abib_barley.png"
    if settings.get("show_splash", False):  # Default to False if the key is missing.
        splash = QSplashScreen(QPixmap(splash_path))
        splash.show()


def _init_screen_metrics(app: QApplication) -> None:
    # Set global width/height used by Abib.sizer
    width, height = app.primaryScreen().size().toTuple()
    print(f"Screen size: {width}x{height}")
    # Expose to Abib module for sizer()
    AbibModule.width = width
    AbibModule.height = height
    AbibModule.half_width = width / 2
    AbibModule.half_height = height / 2


def _load_bible_text_and_maps(loader: DataLoader) -> None:
    data = loader.load_bible()
    AbibModule.KJB_PCE_LASTLINE = data.KJB_PCE_LASTLINE
    AbibModule.EOTNOC = data.EOTNOC
    AbibModule.KJV = data.KJV
    AbibModule.Amap = data.Amap
    AbibModule.Ps119 = data.Ps119
    AbibModule.P119 = data.P119
    AbibModule.book_bounds = data.book_bounds
    AbibModule.starts_with_italics = data.starts_with_italics


def _load_search_indexes(loader: DataLoader) -> None:
    s = loader.load_search()
    AbibModule.Rnew = s.Rnew
    AbibModule.Rdic = s.Rdic
    AbibModule.Rlow = s.Rlow
    AbibModule.Ldic = s.Ldic
    AbibModule.Rstp = s.Rstp
    AbibModule.Rlsp = s.Rlsp
    AbibModule.stripped_dict = s.stripped_dict
    AbibModule.strpd_low_dict = s.strpd_low_dict
    AbibModule.set_dict = s.set_dict
    AbibModule.set_lowdict = s.set_lowdict


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

    # Initialize settings service and load settings
    settings_service = SettingsService()
    settings: Dict[str, Any] = settings_service.settings

    _show_splash_if_enabled(settings)

    if sh.system() == 'Windows':
        app.processEvents()

    _init_screen_metrics(app)

    # Create main window
    w: MainWindow = MainWindow()

    # Provide the settings path to windows that need to persist user settings
    w.user_settings_path = str(settings_service.user_settings_path)

    # Expose the window instance at module level for helpers
    AbibModule.w = w

    # Update and load data files
    update_abib()

    # Use centralized DataLoader
    loader = DataLoader()
    _load_bible_text_and_maps(loader)
    _load_search_indexes(loader)
    _load_sme_metadata(loader)

    # Open Bible text into the editor
    w.file_open(str(sh.base_dir / "KJB_PCE.txt"))

    # Initialise runtime state on the window
    _init_window_runtime_state(w)

    # Set the application icon (optional but preserved)
    app_icon: QIcon = QIcon(str(sh.icon_path))
    app.setWindowIcon(app_icon)

    w.show()

    # Start the event loop
    from sys import exit as _exit
    _exit(app.exec())


if __name__ == "__main__":
    run()
