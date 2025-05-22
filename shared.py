# -*- coding: utf-8 -*-

################################################################################
## Module containing objects shared by Abib.py and fcs.py
##
## Used by Abib.py (CURRENT_VERSION) =>
################################################################################

from pathlib import Path
from os import getenv
from json import loads
from platform import system

CURRENT_VERSION = "412.8"

current_directory: Path = Path.cwd()
str_cwd: str = str(current_directory)
# settings_file: Path = current_directory / 'settings.json'
user_settings_dir: Path = Path.cwd()  # Initialise with the current working directory as a placeholder value.

if system() == 'Windows':
    user_settings_dir = Path(getenv("APPDATA")) / "Abib"  # User's directory.
elif system() == 'Darwin':
    user_settings_dir = Path.home() / "Library" / "Application Support" / "Abib"
elif system() == 'Linux':
    user_settings_dir = Path.home() / ".config" / "Abib"
else:
    print("Unknown operating system.")
    exit()

# Construct the path to the icon regardless of the operating system.
icon_path: Path = current_directory / "images" / "abib_icon0.ico"
if not icon_path.is_file():
    raise FileNotFoundError(f"Icon file not found: {icon_path}")

# Create the base directory as a Path object
base_dir = Path(str_cwd)

MAX_VERSES_PER_CHAPTER = 176
MAX_CHAPTER_COUNT = 150
BOOKS_IN_THE_BIBLE = 66
CHAPTERS_IN_THE_BIBLE = 1189
LAST_VERSE_IN_BIBLE = 31101  # The first verse being zero.
EOF_BIBLE_TEXT = LAST_VERSE_IN_BIBLE + 1
EOF_AMAP = EOF_INFO = EOF_BIBLE_TEXT + 17

bibledict: dict[str, int] = {
        'genesis': 1, 'ge': 1, 'gen': 1, 'g': 1, 'gene': 1, 'ot': 1,
        'exodus': 2, 'ex': 2, 'exo': 2, 'e': 2, 'exod': 2,
        'leviticus': 3, 'le': 3, 'lev': 3, 'levi': 3, 'l': 3, 'levt': 3, 'levtics': 3,
        'numbers': 4, 'nu': 4, 'num': 4, 'number': 4, 'n': 4, 'numb': 4,
        'deuteronomy': 5, 'de': 5, 'deut': 5, 'deu': 5, 'd': 5,
        'joshua': 6, 'jos': 6, 'josh': 6, 'j': 6,
        'judges': 7, 'jdg': 7, 'ju': 7, 'jud': 7, 'judg': 7, 'judge': 7,
        'ruth': 8, 'ru': 8, 'rut': 8, 'r': 8,
        '1samuel': 9, '1s': 9, '1sa': 9, '1sam': 9, '1bk': 9, 'ibk': 9,
        'Isamuel': 9, 'Isam': 9,
        'isamuel': 9, 'isam': 9,
        '2samuel': 10, '2s': 10, '2sa': 10, '2sam': 10, '2bk': 10, 'iibk': 10,
        'iisamuel': 10, 'iis': 10, 'iisa': 10, 'iisam': 10,
        '1kings': 11, '1k': 11, '1ki': 11, '1kin': 11, '1king': 11, '3bk': 11,
        'ikings': 11, 'ik': 11, 'iki': 11, 'ikin': 11, 'iking': 11, 'iiibk': 11, 'iiikings': 11,
        '2kings': 12, '2k': 12, '2ki': 12, '2kin': 12, '2king': 12, '4bk': 12,
        'iikings': 12, 'iik': 12, 'iiki': 12, 'iikin': 12, 'iiking': 12, 'ivbk': 12, 'iiiibk': 12, 'ivkings': 12,
        '1chronicles': 13, '1ch': 13, '1chr': 13, '1chronicle': 13, '1c': 13,
        '1chro': 13, '1chron': 13, '1chroni': 13, '1chronic': 13, '1cr': 13,
        'ichro': 13, 'ichron': 13, 'ichroni': 13, 'ichronic': 13, 'icr': 13,
        'ichronicles': 13, 'ich': 13, 'ichr': 13, 'ichronicle': 13, 'ic': 13,
        '2chronicles': 14, '2ch': 14, '2chr': 14, '2chronicle': 14, '2c': 14,
        'iichronicles': 14, 'iich': 14, 'iichr': 14, 'iichronicle': 14, 'iic': 14,
        'ezra': 15, 'ezr': 15, 'ez': 15,
        'nehemiah': 16, 'ne': 16, 'neh': 16, 'nehe': 16, 'neem': 16,
        'esther': 17, 'es': 17, 'est': 17, 'esth': 17, 'esthe': 17, 'esta': 17,
        'job': 18, 'jb': 18,
        'psalms': 19, 'psalm': 19, 'ps': 19, 'psa': 19, 'p': 19,
        'proverbs': 20, 'pr': 20, 'pro': 20, 'prov': 20, 'proverb': 20,
        'ecclesiastes': 21, 'ec': 21, 'ecc': 21, 'eccl': 21, 'ecclesiaste': 21, 'eccles': 21,
        'songofsolomon': 22, 'songofsongs': 22, 'so': 22, 'son': 22, 'song': 22,
        'sos': 22, 'songs': 22, 's': 22, 'ss': 22, 'ca': 22, 'canticles': 22, 'sng': 22,
        'isaiah': 23, 'isai': 23, 'esaias': 23, 'i': 23, 'is': 23, 'isa': 23, 'ish': 23,
        'jeremiah': 24, 'je': 24, 'jer': 24, 'jeremy': 24,
        'lamentations': 25, 'la': 25, 'lam': 25, 'lamentation': 25, 'lame': 25,
        'ezekiel': 26, 'eze': 26, 'ezek': 26, 'ezk': 26, 'zek': 26,
        'daniel': 27, 'da': 27, 'dan': 27, 'dani': 27,
        'hosea': 28, 'ho': 28, 'hos': 28, 'h': 28, 'hose': 28,
        'joel': 29, 'joe': 29, 'jol': 29,
        'amos': 30, 'am': 30, 'amo': 30, 'a': 30,
        'obadiah': 31, 'ob': 31, 'oba': 31, 'obad': 31, 'o': 31,
        'jonah': 32, 'jon': 32, 'jona': 32,
        'micah': 33, 'mi': 33, 'mic': 33, 'm': 33, 'mica': 33,
        'nahum': 34, 'na': 34, 'nah': 34, 'nam': 34,
        'habakkuk': 35, 'hab': 35, 'haba': 35, 'habak': 35, 'ha': 35, 'hb': 35,
        'zephaniah': 36, 'zp': 36, 'zep': 36, 'zeph': 36, 'z': 36, 'ze': 36,
        'haggai': 37, 'hag': 37, 'hagg': 37, 'hg': 37, 'haggi': 37,
        'zechariah': 38, 'zc': 38, 'zec': 38, 'zech': 38,
        'malachi': 39, 'mal': 39, 'mala': 39, 'malac': 39, 'ma': 39,
        'matthew': 40, 'mt': 40, 'mat': 40, 'matt': 40, 'nt': 40,
        'mark': 41, 'mr': 41, 'mk': 41, 'mar': 41, 'mrk': 41,
        'luke': 42, 'lu': 42, 'lk': 42, 'luk': 42,
        'john': 43, 'joh': 43, 'jn': 43, 'jno': 43, 'jo': 43, 'jhn': 43, 'jh': 43,
        'acts': 44, 'ac': 44, 'act': 44,
        'romans': 45, 'ro': 45, 'rom': 45, 'roman': 45, 'roma': 45,
        '1corinthians': 46, '1co': 46, '1cor': 46, '1corinthian': 46,
        'icorinthians': 46, 'ico': 46, 'icor': 46, 'icorinthian': 46,
        '2corinthians': 47, '2co': 47, '2cor': 47, '2corinthian': 47,
        'iicorinthians': 47, 'iico': 47, 'iicor': 47, 'iicorinthian': 47,
        'galatians': 48, 'ga': 48, 'gal': 48, 'galatian': 48, 'gala': 48,
        'ephesians': 49, 'ep': 49, 'eph': 49, 'ephesian': 49, 'ephe': 49,
        'philippians': 50, 'php': 50, 'philip': 50, 'phil': 50, 'ph': 50, 'phili': 50,
        'colossians': 51, 'co': 51, 'col': 51, 'colossian': 51, 'c': 51,
        '1thessalonians': 52, '1th': 52, '1the': 52, '1thess': 52,
        '1thessalonian': 52, '1t': 52, '1thes': 52,
        'ithessalonians': 52, 'ith': 52, 'ithe': 52, 'ithess': 52,
        'ithessalonian': 52, 'it': 52, 'ithes': 52,
        '2thessalonians': 53, '2th': 53, '2the': 52, '2thess': 53,
        '2thessalonian': 53, '2t': 53, '2thes': 53,
        'iithessalonians': 53, 'iith': 53, 'iithe': 52, 'iithess': 53,
        'iithessalonian': 53, 'iit': 53, 'iithes': 53,
        '1timothy': 54, '1ti': 54, '1tim': 54,
        'itimothy': 54, 'iti': 54, 'itim': 54,
        '2timothy': 55, '2ti': 55, '2tim': 55,
        'iitimothy': 55, 'iiti': 55, 'iitim': 55,
        'titus': 56, 'ti': 56, 'tit': 56, 't': 56,
        'philemon': 57, 'phm': 57, 'phi': 57, 'phl': 57, 'phile': 57, 'philo': 57, "phlm": 57,
        'hebrews': 58, 'he': 58, 'heb': 58, 'hebrew': 58, 'hebr': 58,
        'james': 59, 'ja': 59, 'jas': 59, 'jam': 59, 'jame': 59, 'jim': 59, 'jamo': 59,
        '1peter': 60, '1p': 60, '1pe': 60, '1pet': 60, '1pete': 60,
        'Ipeter': 60, 'Ip': 60, 'Ipe': 60, 'Ipet': 60, 'Ipete': 60,
        'ipeter': 60, 'ip': 60, 'ipe': 60, 'ipet': 60, 'ipete': 60,
        '2peter': 61, '2p': 61, '2pe': 61, '2pet': 61, '2pete': 61,
        'IIpeter': 61, 'IIp': 61, 'IIpe': 61, 'IIpet': 61, 'IIpete': 61,
        'iipeter': 61, 'iip': 61, 'iipe': 61, 'iipet': 61, 'iipete': 61,
        '1john': 62, '1j': 62, '1jo': 62, '1joh': 62, '1jn': 62, '1jno': 62, '1 john': 62,
        'ijohn': 62, 'ij': 62, 'ijo': 62, 'ijoh': 62, 'ijn': 62, 'ijno': 62,
        '2john': 63, '2j': 63, '2jo': 63, '2joh': 63, '2jn': 63, '2jno': 63, '2 john': 63,
        'iijohn': 63, 'iij': 63, 'iijo': 63, 'iijoh': 63, 'iijn': 63, 'iijno': 63,
        '3john': 64, '3j': 64, '3jo': 64, '3joh': 64, '3jn': 64, '3jno': 64, '3 John': 64,
        'iiijohn': 64, 'iiij': 64, 'iiijo': 64, 'iiijoh': 64, 'iiijn': 64, 'iiijno': 64,
        'jude': 65, 'jd': 65, 'jde': 65,
        'revelation': 66, 'revelationofjohn': 66, 're': 66, 'rev': 66, 'theapocalypseofjohn': 66,
        'revelations': 66, 'reve': 66, 'apocalypse': 66, 'apocalypseofjohn': 66,
    }

onechapterbooks: tuple[int, int, int, int, int] = (30, 56, 62, 63, 64)

def readfile(input_path: str, input_filename: str, file_length: int) -> list:
    """File reading routine — reads a text file into a list."""

    err = "Abib is not in the same directory as its files and folders.\n"
    output_listname = []
    try:
        with open(f'{input_path}{input_filename}', 'r') as f_read:
            for _ in range(file_length):
                x5 = f_read.readline()
                try:
                    i_line = int(x5.splitlines()[0])  # Convert to int if possible
                except ValueError:
                    i_line = x5.splitlines()[0]  # Keep as string if conversion fails
                output_listname.append(i_line)
    except FileNotFoundError:
        exit(err)  # Exit the program with an error message

    return output_listname

# Read Info.txt
Info = []
Inf: list = readfile('', str(Path(base_dir / "Info.txt")), EOF_INFO)
Inf = Inf[17:]  # Skip the first 17 elements
for _ in range(LAST_VERSE_IN_BIBLE + 1):
    Info.append(loads(Inf[_]))
Info = tuple(Info)
