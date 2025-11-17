# -*- coding: utf-8 -*-

################################################################################
## Module containing various functions.
##
## Used by Abib.py (sh.CURRENT_VERSION) =>
################################################################################

from json import load, loads, JSONDecodeError, dump
from typing import Any
from string import ascii_letters, digits
from roman import fromRoman, InvalidRomanNumeralError
import shared as sh
from datetime import datetime, timedelta
from os import path
from pathlib import Path
from PySide6.QtWidgets import QApplication
from typing import cast

import re


def get_default_settings() -> Any:
    """Return a fresh copy of Abib's default settings dictionary.
    This centralises defaults so other components (e.g. Settings dialog reset)
    can align with the same values used by load_settings_from_file.
    """
    return {
        "theme": "Light",
        "show_splash": "false",
        "devotional_font_size": 12,
        "bible_font_size": 12,
        "main_window": {
            "x": 25,
            "y": 41,
            "width": 555,
            "height": 599
        },
        "devotional_window": {
            "x": 160,
            "y": 50,
            "width": 350,
            "height": 599
        },
        "reader_window": {
            "x": 100,
            "y": 100,
            "width": 736,
            "height": 599,
        },
        # Map of the 'Other Works' file stems to string booleans "true"/"false" indicating
        # whether they should be shown in the reader window combo box.
        # This map is generated and kept in sync at the application startup based on
        # the contents of the "Other Works" folder.
        # Defaults are "false".
        "show_work":{},
        "_comment": "This is a comment. It will be ignored by the program...",
        "last_other_work": "Pilgrims-Progress",
        "last_read_positions": {
            "Pilgrims-Progress": [624, 50, 70, 736, 599],
            "Institutes": [0, 50, 70, 736, 599],
            "Naves Topical Bible": [0, 50, 70, 736, 599],
            "Calvin - Commentaries": [0, 50, 70, 736, 599],
            "Catechisms John Owen": [0, 50, 70, 736, 599],
            "Commentary on Galatians Luther": [0, 50, 70, 736, 599],
            "Election A. W. Pink": [0, 50, 70, 1232, 599],
            "Election C. D. Cole": [0, 50, 70, 736, 599],
            "Of Prayer - Calvin": [0, 50, 70, 736, 599],
            "Pneumatologia": [0, 50, 70, 736, 599],
            "Puritan Catechism": [0, 50, 70, 736, 599],
            "Sermons on Proverbs": [0, 50, 70, 736, 599],
            "Small Catechism Luther": [0, 50, 70, 736, 599],
            "Systematic Theology - Vol. I": [0, 50, 70, 736, 599],
            "Systematic Theology - Vol. II": [0, 50, 70, 736, 599],
            "Systematic Theology - Vol. III": [0, 50, 70, 736, 599],
            "The Holy War": [0, 50, 70, 736, 599],
            "calcom01": [15, 50, 70, 736, 599],
            "calcom02": [15, 50, 70, 736, 599],
            "calcom03": [15, 50, 70, 736, 599],
            "calcom04": [15, 50, 70, 736, 599],
            "calcom05": [15, 50, 70, 736, 599],
            "calcom06": [15, 50, 70, 736, 599],
            "calcom07": [15, 50, 70, 736, 599],
            "calcom08": [15, 50, 70, 736, 599],
            "calcom09": [15, 50, 70, 736, 599],
            "calcom10": [15, 50, 70, 736, 599],
            "calcom11": [15, 50, 70, 736, 599],
            "calcom12": [30, 50, 70, 736, 599],
            "calcom13": [30, 50, 70, 736, 599],
            "calcom14": [30, 50, 70, 736, 599],
            "calcom15": [30, 50, 70, 736, 599],
            "calcom16": [30, 50, 70, 736, 599],
            "calcom17": [36, 50, 70, 736, 599],
            "calcom18": [36, 50, 70, 736, 599],
            "calcom19": [36, 50, 70, 736, 599],
            "calcom20": [36, 50, 70, 736, 599],
            "calcom21": [15, 50, 70, 736, 599],
            "calcom22": [15, 50, 70, 736, 599],
            "calcom23": [15, 50, 70, 736, 599],
            "calcom24": [15, 50, 70, 736, 599],
            "calcom25": [15, 50, 70, 736, 599],
            "calcom26": [15, 50, 70, 736, 599],
            "calcom27": [15, 50, 70, 736, 599],
            "calcom28": [15, 50, 70, 736, 599],
            "calcom29": [15, 50, 70, 736, 599],
            "calcom30": [15, 50, 70, 736, 599],
            "calcom31": [15, 50, 70, 736, 599],
            "calcom32": [15, 50, 70, 736, 599],
            "calcom33": [15, 50, 70, 736, 599],
            "calcom34": [15, 50, 70, 736, 599],
            "calcom35": [15, 50, 70, 736, 599],
            "calcom36": [15, 50, 70, 736, 599],
            "calcom37": [15, 50, 70, 736, 599],
            "calcom38": [15, 50, 70, 736, 599],
            "calcom39": [15, 50, 70, 736, 599],
            "calcom40": [0, 50, 70, 736, 599],
            "calcom41": [15, 50, 70, 736, 599],
            "calcom42": [15, 50, 70, 736, 599],
            "calcom43": [15, 50, 70, 736, 599],
            "calcom44": [15, 50, 70, 736, 599],
            "calcom45": [15, 50, 70, 736, 599],
        }
    }


def get_screen_size() -> tuple[int, int]:
    """Get the primary screen dimensions."""

    app_instance = QApplication.instance()
    if app_instance is None:
        # If no QApplication exists, create a temporary one
        temp_app = QApplication([])
        width, height = temp_app.primaryScreen().size().toTuple()
        temp_app.quit()
        return width, height
    else:
        # Cast to QApplication to access primaryScreen()
        app = cast(QApplication, app_instance)
        width, height = app.primaryScreen().size().toTuple()
        return width, height


def split_strip(_key: str) -> tuple[int, str]:
    """Remove whitespace from '_key' entered as passage reference."""

    p = " ()[];:'!<>,.-?"       # Characters to strip ’ not needed.

    # Split the string into words, strip the unwanted characters from each word,
    # and filter out any resulting empty words.
    word_list = [word.strip(p) for word in _key.split(' ') if word.strip(p)]

    num = len(word_list)        # Count the number of words
    _key = ' '.join(word_list)  # Join words back into a single string

    return num, _key


def create_pattern(key: str) -> str:
    """Create a regex pattern based on the given key."""

    return rf"\b{key[:-2]}[s’][s’]" if key[-2:] == "s’" else rf"\b{key}\b"


def punctuation_counter(text: str) -> int:
    """Count the number of punctuation characters in text."""

    p = "()[];:!<>,.-?"  # ’ not needed because in the search file.
    num: int = 0
    for _ in p:
        k = text.count(_)
        num += k

    return num


def repeat_find(rx: str, start: int, end: int) -> int:
    """Repeat find of lengthening text.

    rx is the verse from the PCE-find.txt file
    or a similar file without italics.
    """

    flag: bool = True
    numb: int
    sumb: int = 0
    repeats: int = 0
    while flag:
        text: str = rx[start:end + sumb]
        numb = punctuation_counter(text)
        sumb += numb
        start = end + sumb - numb
        repeats += 1
        if repeats > 15 or numb == 0:
            flag = False

    return sumb


def repeat_find_keyinc(rx: str, start: int, end: int) -> int:
    """Repeat find of lengthening text.

    rx is the verse from the PCE-find.txt file
    or a similar file without italics."""

    numb: int
    sumb = 0
    while True:
        text: str = rx[start:end]
        numb = punctuation_counter(text)
        sumb += numb
        if numb == 0:
            break
        start = end
        end += numb

    return sumb


def readio(input_path: str, input_filename: str, file_length: int) -> list:
    """Read Bible files."""

    # print('readio ', input_filename)
    output_listname: list = []
    f_readio = open(f'{input_path}{input_filename}', 'r', encoding="utf-8")
    for _ in range(file_length):
        x5: str = f_readio.readline()
        i = f'{x5.splitlines()[0]}\n'
        output_listname.append(i)
    f_readio.close()

    return output_listname


def load_json_dict(file_dict: Any) -> Any:
    """Load a dictionary with JSON."""

    # print('load_json_dict ', file_dict)
    with open(file_dict, "r", encoding='utf-8') as read_file:
        file1 = load(read_file)

    return file1


def load_list_set_dict(input_filename: str, ref_dict: Any) -> dict[Any, set]:
    """Load a list_dict.txt/json file that is a dictionary of Bible words.

    As keys and values, lists of verse numbers of the Bible.

    The lists are converted to sets after reading, to return them to the
    format required for use. The ref_dict is used to get the relevant keys.

    The reason for this is that apparently JSON cannot deal with sets.

    The input_filename will be of the form 'list_[name].txt/json'.
    The receiving files name should be of the form 'set_[name]'.
    """

    # print('load_list_set_dict ', input_filename)
    setdict: dict[Any, set] = {}
    listdict: Any = load_json_dict(input_filename)
    sd: list = list(ref_dict)
    lsd: int = len(sd)
    for n in range(lsd):
        setdict[sd[n]] = set(listdict[sd[n]])

    return setdict


def is_float_re(string_: str) -> bool:
    """Take a string and determine if it represents a float.

    Many thanks to:
    https://stackoverflow.com/users/1399279/sethmmorton.
    """
    pattern = r"^[-+]?(?:\b[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+\b)?$"
    m = re.match(pattern, string_)  # Use re.match directly

    return m is not None  # More Pythonic than `return True if m else False`


def any_of_the_words_lookup(_key: str, _set: dict[str, set]) -> tuple[int, str]:
    """Takes '_key' and splits it into separate words in 'liszt',
    which are then looked up in the set of Bible words.

    Returns modified '_key' and 'count' in 'number_of_occurrences' of the words in it."""

    liszt: list[str] = _key.split(' ')

    # Uses a set to eliminate duplicates, keep words found in '_set'
    unique_words = set(word for word in liszt if word in _set)

    _key = ' '.join(unique_words)  # join the set into a string

    number_of_occurrences = len(unique_words)  # count the number of unique words

    return number_of_occurrences, _key


def squeeze(char: str, s: str) -> str:
    """Remove duplicate characters. For example, '.....' is replaced with '.'."""

    while char * 2 in s:
        s = s.replace(char * 2, char)

    return s


def remove_junk(text: str) -> str:
    """Remove junk characters from 'text'.
    Junk characters are any non-alphabetic characters,
    numbers, or any of the normal punctuation characters.
    Plus, the text must start and finish with a letter or a number."""

    # print(f"remove_junk: {text}")
    # Define allowed characters using a set for fast membership checks.
    allowed_set = set(ascii_letters + digits + "():,’;-?[].!<> ")
    # Filter out characters not in the allowed set.
    rex: str = "".join(ch for ch in text if ch in allowed_set)

    if text.lstrip('-').isdigit():
        return text  # Return the number as-is if it's valid
    else:
        #  Remove any junk from the beginning of a reference.
        try:
            m: int = re.search("[a-zA-Z0-9]+", rex).start()
            rex: str = rex[m:]
        except AttributeError:
            pass

        #  Remove any junk from the end of a reference.
        try:
            k: int = re.search("[a-zA-Z0-9]+", rex[::-1]).start()
            if k > 0:
                rex = rex[:-k]
        except AttributeError:
            pass

        #  Remove possible duplicate '.' or ':' chapter verse seperator.
        rex = squeeze('.', rex)
        rex = squeeze(':', rex)

        #  Remove possible KJV ending.
        if rex.endswith(' KJV'):
            rex = rex[:-4]

    return rex


def convert_roman_to_integer(reference_text: str) -> str:
    """
    Converts all Roman numeral occurrences in the reference text to numeric values.
    Roman numerals are case-insensitive (e.g. IV == iv == 4).
    Returns the modified text with numerals replaced by integers.
    """
    # Pattern that matches valid Roman numerals without exponential backtracking
    pattern = re.compile(
        r'\bM{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})\b',
        re.IGNORECASE
    )

    def replacer(matched: re.Match[str]) -> str:
        roman_numeral = matched.group(0)
        try:
            return str(fromRoman(roman_numeral))
        except InvalidRomanNumeralError:
            return roman_numeral

    return pattern.sub(replacer, reference_text)


def isRoman(s: str) -> bool:
    """Regular expression to match valid Roman numerals"""

    roman_pattern = r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
    s = s.upper()
    return bool(re.match(roman_pattern, s))


def update_devotional_font_size(new_size: Any, filename="settings.json"):
    """
    Update the devotional font size in the settings file.
    """
    settings = load_settings_from_file(filename)
    settings["devotional_font_size"] = new_size
    save_settings_to_file(settings, filename)
    # print(f"DEBUG: Updated devotional fontsize to: {new_size}")


def get_devotional_font_size(filename="settings.json") -> int:
    """
    Get the current devotional font size from settings.
    """
    settings = load_settings_from_file(filename)
    return settings.get("devotional_font_size", 12)


def load_settings_from_file(filename="settings.json") -> Any:
    """
    Load the settings dictionary from a JSON file.
    If the file is missing, empty, malformed, or has partial settings, return defaults.
    """
    # Default settings
    default_settings = get_default_settings()

    # Check if the file exists
    settings_dir = Path(sh.user_settings_dir)
    settings_dir.mkdir(parents=True, exist_ok=True)  # Create a directory if it doesn't exist
    filename = settings_dir / filename

    if not path.exists(filename):
        print("Settings file does not exist. Using default settings.")
        return default_settings

    # Attempt to read the file
    try:
        with open(filename, "r") as file1:
            # Read and parse the JSON
            content = file1.read().strip()  # Handle an empty file gracefully
            if not content:  # File is empty
                print("Settings file is empty. Falling back to default settings.")
                return default_settings

            settings_here = loads(content)  # Try to parse JSON

            # Add missing keys with their default values
            for key, value in default_settings.items():
                if isinstance(value, dict):
                    # Handle nested dictionaries (like window settings)
                    if key not in settings_here:
                        settings_here[key] = value
                    else:
                        # Ensure all subkeys exist
                        for sub_key, sub_value in value.items():
                            settings_here[key].setdefault(sub_key, sub_value)
                else:
                    settings_here.setdefault(key, value)

            # Clean up deprecated/unused keys to keep settings lean and avoid confusion
            changed = False
            if "pilgrims_progress_window" in settings_here:
                del settings_here["pilgrims_progress_window"]
                changed = True

            # Persist clean-up if anything was removed
            if changed:
                save_settings_to_file(settings_here)

            return settings_here

    except JSONDecodeError:
        print("Settings file is malformed. Overwriting with default settings.")
        return default_settings
    except (OSError, UnicodeDecodeError, PermissionError) as err:
        print(f"Error loading settings: {err}. Using default settings.")
        return default_settings


def save_window_geometry(window_name: str, x: int, y: int, width: int, height: int):
    """Save window geometry to settings"""
    # print(f"DEBUG: Saving geometry for {window_name}: x={x}, y={y}, w={width}, h={height}")

    settings = load_settings_from_file()
    # print(f"DEBUG: Current settings keys: {list(settings.keys())}")

    if window_name not in settings:
        settings[window_name] = {}

    settings[window_name]["x"] = x
    settings[window_name]["y"] = y
    settings[window_name]["width"] = width
    settings[window_name]["height"] = height

    # print(f"DEBUG: Updated settings for {window_name}: {settings[window_name]}")

    save_settings_to_file(settings)
    # print(f"DEBUG: Settings saved to file")


def get_window_geometry(window_name: str) -> tuple[int, int, int, int]:
    """Get window geometry from settings"""

    settings = load_settings_from_file()
    # print(f"DEBUG: Loading geometry for {window_name}")
    # print(f"DEBUG: Available settings keys: {list(settings.keys())}")
    width, height = get_screen_size()
    # print(f"DEBUG: Screen size from fcs.py: {width}x{height}")

    if window_name in settings:
        window_settings = settings[window_name]
        # print(f"DEBUG: Found settings for {window_name}: {window_settings}")
        result = (
            window_settings.get("x", 100),
            window_settings.get("y", 100),
            window_settings.get("width", 737),
            window_settings.get("height", 518)
        )
        if result[0] < 0:
            result = (100, result[1], result[2], result[3])
        if result[1] < 0:
            result = (result[0], 100, result[2], result[3])
        if result[0] + result[2] > width:
            result = (0, result[1], 737, result[3])
        if result[1] + result[3] > height:
            result = (result[0], 100, result[2], 518)
        # print(f"DEBUG: Returning geometry of {window_name}: {result}")
        return result
    else:
        # Return default values
        # print(f"DEBUG: No settings found for {window_name}, using defaults")
        return 100, 100, 640, 518


def save_settings_to_file(the_settings, filename="settings.json"):
    """
    Save the given settings dictionary to a JSON file.
    """
    # print(f"DEBUG: Saving settings to file: {filename}")
    # print(f"DEBUG: Settings: {the_settings}")
    settings_dir = Path(sh.user_settings_dir)
    filename = settings_dir / filename

    try:
        # Explicitly annotate the file object
        with open(filename, "w") as file1:
            # Dump the settings dictionary to JSON format
            dump(the_settings, file1, indent=4)  # Save as JSON with pretty formatting
    except IOError as e1:
        print(f"Error saving settings to file: {e1}")


def setup_Abib_settings(abib_directory: Path) -> None:
    """ Set up the Abib user folder containing the 'settings.json' file."""

    # Create the Abib directory if it doesn't exist
    abib_directory.mkdir(parents=True, exist_ok=True)

    # Path to the settings file in the target directory
    settings_file = abib_directory / "settings.json"

    # Create an empty settings.json if it doesn't exist
    if not settings_file.exists():
        with open(settings_file, "w") as f:
            f.write("{}")
        print(f"Created empty settings.json in {abib_directory}")
    else:
        print(f"Settings.json already exists in {abib_directory}")


def update_bible_font_size(new_size, filename="settings.json"):
    """
    Update the Bible font size in the settings file.
    """
    settings = load_settings_from_file(filename)
    settings["bible_font_size"] = new_size
    save_settings_to_file(settings, filename)
    # print(f"DEBUG: Updated Bible fontsize to: {new_size}")


def get_bible_font_size(filename="settings.json"):
    """
    Get the current Bible font size from settings.
    """
    settings = load_settings_from_file(filename)
    return settings.get("bible_font_size", 12)


def compare_versions(version1, version2):
    """
    Compares two version numbers and determines which one is newer.

    Args:
        version1 (str): The first version number (e.g. "1.0.0").
        version2 (str): The second version number (e.g. "2.3.6").

    Returns:
        int:
        -1 if version1 < version2,
         0 if version1 == version2,
         1 if version1 > version2.
    """
    # Split the version strings into lists of integers
    v1_parts = list(map(int, version1.split(".")))
    v2_parts = list(map(int, version2.split(".")))

    # Compare each part (major, minor, patch) in sequence
    for v1, v2 in zip(v1_parts, v2_parts):
        if v1 < v2:
            return -1  # version1 is older
        elif v1 > v2:
            return 1  # version1 is newer

    # If we run out of parts to compare, handle different lengths (e.g. 1.0 vs 1.0.1)
    if len(v1_parts) < len(v2_parts) and any(part > 0 for part in v2_parts[len(v1_parts):]):
        return -1  # version1 is older
    elif len(v1_parts) > len(v2_parts) and any(part > 0 for part in v1_parts[len(v2_parts):]):
        return 1  # version1 is newer

    return 0  # versions are equal


def clean_chap_prefix(reference_text: str) -> str:
    """Clean 'Chap' prefixes from the reference text."""

    reference_text = reference_text.lower()
    reference_text = reference_text.replace(':', '.')
    if reference_text.startswith('chap'):
        ref = reference_text.replace('chap', '')
        return ref.strip('.')

    # Remove spaces from '2 Corinthians' etc..
    reference_text = reference_text[:3].replace(' ', '') + reference_text[3:]

    # Remove spaces enclosed by a-z
    reference_text = re.sub(r"(?<=[a-z]) (?=[a-z])", "", reference_text)

    # Remove all after a comma, e.g. zechariah.1.12,13
    reference_text = reference_text.split(",")[0]

    return reference_text


def tidy(text: str, parts: list) ->  str:
    """Tidy up the reference parts."""

    abbr: list = ['d', 'c', 'l', 'm']
    full_names: list = ['deuteronomy', 'colossians', 'leviticus', 'micah']

    d: str = parts[0][0]
    # print(f"361 d: {d}")

    if d in abbr:
        # Get the corresponding full name
        try:
            a: str = full_names[abbr.index(d)]
            # print(f"367 '{d}' is an abbreviation for '{a}'.")
        except ValueError:
            # print(f"369 '{d}' is not in the list.")
            raise ValueError("ValueError")

        text = f"{a}{text[1:]}"
        # print(f"373 text: {text}")

    return text


def split_reference(reference_text: str) -> list:
    """
    Split a Bible reference into components based on the book, chapter, and verse,
    ensuring contiguous letters and numbers (e.g. 'g2.6') are split correctly.
    """

    # First, split on delimiters (space, period, colon)
    intermediate_parts = re.split(r'[ .:]+', reference_text)
    # print(f"385 Split reference: {reference_text} into {intermediate_parts}")

    parts_list = []

    # Further split parts with mixed letters and numbers (e.g., 'g2' -> ['g', '2'])
    part_number: int = -1
    for part in intermediate_parts:
        part_number += 1
        # Use regex to separate letters and digits if mixed
        if part_number == 0 and part in sh.bibledict:
            parts_list.append(part)
            # print(f"396 Part: {part} is a book name")
        else:
            match = re.findall(r'[a-zA-Z]+|\d+', part)
            parts_list.extend(match)

    if len(parts_list) > 1:
        try:
            if int(parts_list[0]):
                parts_list[1] = f"{parts_list[0]}{parts_list[1]}"
                del parts_list[0]
        except ValueError:
            pass

    if len(parts_list) == 4:
        parts_list = parts_list[:-1]

    return parts_list


def normalize_semicolon_refs(reference_text: str) -> str:
    """
    Normalise semicolon-separated scripture references so that any segment
    without an explicit book name inherits the book from the previous segment,
    and if a segment starts with only a verse/range, inherit the chapter too.

    Examples
    - "John 3:16; 4:2" -> "John 3:16; John 4:2"
    - "John 10:14-16; 25-28" -> "John 10:14-16; John 10:25-28"
    - "1 Cor 2:3; 4:5" -> "1 Cor 2:3; 1 Cor 4:5"

    If the first segment does not include a recognisable book, the string is
    returned unchanged.
    """
    if ";" not in reference_text:
        return reference_text

    segments = [seg.strip() for seg in reference_text.split(";")]
    last_book_display: str | None = None
    last_chapter: str | None = None

    normalized: list[str] = []
    for seg in segments:
        if not seg:
            continue
        seg_stripped = seg.strip()
        parts = split_reference(seg_stripped)
        if parts and parts[0].lower() in sh.bibledict:
            # Segment begins with a book -> reset inheritance anchors
            m = re.match(r"^\s*([1-4]?\s*[A-Za-z]+(?:\s+[A-Za-z]+)*)", seg_stripped)
            last_book_display = m.group(1) if m else parts[0]
            # Update last_chapter when present like Book 10:...
            chap_match = re.match(r"^[^0-9]*?(\d+)\s*[:.]", seg_stripped)
            last_chapter = chap_match.group(1) if chap_match else None
            normalized.append(seg_stripped)
            continue

        # No leading book in this segment
        if last_book_display:
            # Detect forms: chapter:verse..., or just verse/range
            chap_verse_match = re.match(r"^\s*(\d+)\s*[:.]\s*(.+)$", seg_stripped)
            if chap_verse_match:
                # Has chapter explicitly -> inherit book only
                last_chapter = chap_verse_match.group(1)
                normalized_seg = f"{last_book_display} {seg_stripped}"
                normalized.append(normalized_seg)
            else:
                # Starts with verse or range only (e.g. "25-28")
                if last_chapter:
                    normalized_seg = f"{last_book_display} {last_chapter}:{seg_stripped}"
                else:
                    # No known chapter to inherit; best effort — inherit book only
                    normalized_seg = f"{last_book_display} {seg_stripped}"
                normalized.append(normalized_seg)
        else:
            # No prior book to inherit from; leave as-is
            normalized.append(seg_stripped)

    return "; ".join(normalized)


def check_roman_chapter_adjacent(reference_text: str) -> str:
    """Check if the reference text can be split further into a book, chapter, and verse.
    Specifically, if the first part of the reference text is a book in sh.bibledict adjacent
    to a chapter number in roman numerals, then the reference text is split further."""

    #  Note: 'MI' is 1001 in roman numerals and will be converted later if we don't act.

    div: int = 0
    divis: int
    reference_parts = split_reference(reference_text)
    # print(f"425 Reference parts: {reference_parts}")

    # len_parts: int = len(reference_parts)
    # print(f"428 len_parts: {len_parts}")

    try:
        # Do this part only if the book name is invalid.
        if reference_parts[0] not in sh.bibledict and reference_parts[0][0] in sh.bibledict:
            reference_text = tidy(reference_text, reference_parts)
            # print(f"434 After fcs.tidy: reference_text: {reference_text}")
    except IndexError:
        return '436 Error: No reference parts.'

    reference_parts = split_reference(reference_text)
    len_parts = len(reference_parts)
    # print(f"440 Reference parts: {reference_parts}")
    ref = reference_parts[0]
    len_ref: int = len(ref)
    # print(f"443 Reference text length: {len_ref} ref = {ref}")

    if (ref in sh.bibledict or isRoman(ref)) and ref != 'mi':
        # print(f"446 ref: {ref} no need to split further.")
        return reference_text
    else:
        # print(f"449 Reference text: {ref} needs to be split.")
        pass

        # Find the start of the roman numeral.
        for i in range(len_ref, 0, -1):
            if isRoman(ref[i:]):
                div = i
            else:
                break

        divis = len_ref - div
        roman_number: str = ref[-divis:]
        # print(f"461 Roman number: {roman_number}")
        # print(f"462 divis = {divis}")
        # print(f"463 ref = {ref}")

        # Find the end of the bible book name.
        results = []
        for i in range(len_ref):
            if ref[:i] in sh.bibledict:
                results.append(i)
        # print(f"470 Results: {results}")

        if results:
            rr1: str = ref[:results[-1]]
            # print(f"474 results[-1] = {results[-1]}")
            # print(f"475 Book name is: {rr1}")
            if divis + results[-1] == len_ref:
                if len_parts == 1:
                    reference_text = f"{rr1} {ref[-divis:]}"
                elif len_parts == 2:
                    reference_text = f"{rr1} {ref[-divis:]}.{reference_parts[1]}"
                # print(f"481 Reference text: {reference_text}")
                reference_parts = split_reference(reference_text)
                len_parts = len(reference_parts)
            elif divis + results[-1] > len_ref:
                lbn: int =len(rr1)  # Length of the book name.
                book = ref[:lbn]
                # print(f"487 Book name: {book}")
                roman_number = ref[lbn:]
                reference_text = f"{book} {roman_number}" # roman number is the chapter.
            else:
                # print(f"491 Reference text: {reference_text} is unchanged.")
                pass

            if sh.bibledict[rr1] - 1 not in sh.onechapterbooks:
                # print(f"495 Reference parts: {reference_parts} len_parts: {len_parts}")
                match len_parts:
                    case 1:
                        reference_text = f"{rr1}"
                    case 2:
                        reference_text = f"{rr1}  {roman_number}"
                    case 3:
                        reference_text = f"{rr1} {roman_number}.{reference_parts[2]}"
                    case _:
                        reference_text = f"Error: {reference_text} is invalid."
                # print(f"505 Reference text @ end adj: {reference_text}")

    return reference_text


def attach_book_name(reference_text: str, current_line: int) -> str:
    """Attach a book name to the floating-point reference."""

    z1 = sh.Info[current_line][0] + 1
    book_name = next((key for key, value in sh.bibledict.items() if value == z1), "")
    return f"{book_name} {reference_text}"


def get_date_file(date_index: int = 0, adjustment: int = 0) -> tuple:
    """
    Process the date into the desired format without using global variables.

    Args:
        date_index (int): Hours relative to today's date.
        adjustment (int): Adjustment to apply to date_index.

    Returns:
        tuple: A tuple containing the formatted date, time of day (morning/evening),
               and the updated date_index.
    """

    # Adjust the date_index
    date_index += adjustment

    morn_or_even: str = ""

    # Get today's date and apply the date_index offset
    today = datetime.now() + timedelta(hours=date_index)

    # Extract the necessary date information
    month = today.strftime("%B")  # E.g. "February"
    day = today.day  # E.g. 3

    # Format the date as a string (e.g. "February 3")
    formatted_date = f"{month} {day}"

    # Determine if it's morning or evening
    if today.hour < 12:
        morn_or_even = "morning"
    elif today.hour >= 12:
        morn_or_even = "evening"

    # Return the formatted date, morning/evening info, and updated date_index
    return formatted_date, morn_or_even, date_index
