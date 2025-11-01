from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set, List
from json import load, JSONDecodeError

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap, QColor

import shared as sh
import fcs

from services.settings import SettingsService
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


def _load_bible_text_and_maps() -> None:
    # KJV text
    AbibModule.KJB_PCE_LASTLINE = 36199
    file_path = str(Path(sh.str_cwd) / "KJB_PCE.txt")
    KJV = fcs.readio('', file_path, AbibModule.KJB_PCE_LASTLINE)

    AbibModule.EOTNOC = '****END OF THE NOTICE OF COPYRIGHT****\n'
    try:
        i_ = KJV.index(AbibModule.EOTNOC)
    except ValueError:
        print('Failed to find the line ', AbibModule.EOTNOC)
        print('Cannot continue until this is put right.')
        raise SystemExit('Reinstalling the program should resolve this.')
    KJV = KJV[i_ + 1:]
    AbibModule.KJV = tuple(KJV)

    assert (len(AbibModule.KJV) == AbibModule.KJB_PCE_LASTLINE - 118)

    # Amap
    amap_path = str(Path(sh.str_cwd) / "Amap.txt")
    Amap = sh.readfile('', amap_path, sh.EOF_AMAP)
    AbibModule.Amap = Amap[17:]

    # Psalm 119 helpers
    Ps119: List[int] = [
        15907, 15915, 15923, 15931, 15939, 15947, 15955, 15963, 15971, 15979,
        15987, 15995, 16003, 16011, 16019, 16027, 16035, 16043, 16051, 16059,
        16067
    ]
    AbibModule.Ps119 = Ps119
    P119: List = []
    for _ in Ps119:
        v: Any = AbibModule.Amap[_]
        P119.append(v)
    AbibModule.P119 = P119

    # Precomputed bounds/flags used by syntax/highlighting (kept for parity)
    AbibModule.book_bounds = [
        0, 1533, 2746, 3605, 4893, 5852, 6510, 7128, 7213, 8023,
        8718, 9534, 10253, 11195, 12017, 12297, 12703, 12870,
        13940, 16 , 17316, 17538, 17655, 18947, 20311, 20465,
        21738, 22095, 22292, 22365, 22511, 22532, 22580, 22685,
        22732, 22788, 22841, 22879, 23090, 23145, 24216, 24894,
        26045, 26924, 27931, 28364, 28801, 29058, 29207, 29362,
        29466, 29561, 29650, 29697, 29810, 29893, 29939, 29964,
        30267, 30375, 30480, 30541, 30646, 30659, 30673, 30698,
        31102
    ]
    AbibModule.starts_with_italics = [6203, 13009, 14972, 15412, 22195, 28117]


def _load_search_indexes() -> None:
    # Read and process PCE-find.txt
    Rnew = fcs.readio('', str(Path(sh.base_dir / "PCE-find.txt")), sh.EOF_BIBLE_TEXT)
    AbibModule.Rnew = tuple(Rnew)
    AbibModule.Rdic = dict(enumerate(AbibModule.Rnew))

    # Read and process PCE-lower.txt
    Rlow = fcs.readio('', str(Path(sh.base_dir / "PCE-lower.txt")), sh.EOF_BIBLE_TEXT)
    AbibModule.Rlow = tuple(Rlow)
    AbibModule.Ldic = dict(enumerate(AbibModule.Rlow))

    # Read PCE-stripped.txt
    Rstp = fcs.readio('', str(Path(sh.base_dir / "PCE-stripped.txt")), sh.EOF_BIBLE_TEXT)
    AbibModule.Rstp = tuple(Rstp)

    # Read PCE-stripped_lower.txt
    Rlsp = fcs.readio('', str(Path(sh.base_dir / "PCE-stripped_lower.txt")), sh.EOF_BIBLE_TEXT)
    AbibModule.Rlsp = tuple(Rlsp)

    # Dictionaries for searching
    with open("stripped_dict.txt", encoding="utf-8") as f:
        stripped_dict: Any = load(f)
    with open("strpd_low_dict.txt", encoding="utf-8") as f:
        strpd_low_dict: Any = load(f)

    # Expose raw dictionaries as well as the set-based indices
    AbibModule.stripped_dict = stripped_dict
    AbibModule.strpd_low_dict = strpd_low_dict

    AbibModule.set_dict = fcs.load_list_set_dict("list_dict.json", stripped_dict)
    AbibModule.set_lowdict = fcs.load_list_set_dict("list_lowdict.json", strpd_low_dict)


def _load_sme_metadata() -> None:
    # These are retained for compatibility even though ReadingPlans handles SME now
    try:
        with open("morning_evening.json", "r", encoding="utf-8") as file:
            AbibModule.sme_data = load(file)  # Load JSON data (for any legacy callers)
    except JSONDecodeError as e:
        print(f"JSON file is invalid: {e}")
    AbibModule.date_file = fcs.get_date_file()


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

    _load_bible_text_and_maps()
    _load_search_indexes()
    _load_sme_metadata()

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
