# -*- coding: utf-8 -*-
import re
################################################################################
## Module containing various functions.
##
## Used by Abib.py version 412.2 =>
################################################################################

from json import load, loads, JSONDecodeError
from typing import Any
from string import ascii_letters, digits
from roman import fromRoman, InvalidRomanNumeralError
from os import path


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
        exit(err)  # Exit program with an error message

    return output_listname

def split_strip(_key: str) -> tuple[int, str]:
    """Remove whitespace from '_key' entered as passage reference."""

    p = " ()[];:'!<>,.-?"       # Characters to strip ’ not needed.

    # Split the string into words, strip the unwanted characters from each word,
    # and filter out any resulting empty words.
    word_list = [word.strip(p) for word in _key.split(' ') if word.strip(p)]

    num = len(word_list)        # Count the number of words
    _key = ' '.join(word_list)  # Join words back into a single string

    return num, _key

def create_pattern(key):
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
    while flag is True:
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
    """Takes _key and splits it into separate words in liszt,
    which are then looked up in the set of Bible words.
    Returns modified _key and count in num of occurrences of the words in it."""

    liszt: list[str] = _key.split(' ')

    # use a set to eliminate duplicates, keep words found in _set
    unique_words = set(word for word in liszt if word in _set)

    _key = ' '.join(unique_words)  # join the set into a string

    num = len(unique_words)  # count the number of unique words

    return num, _key

def squeeze(char: str, s: str) -> str:
    """Remove duplicate characters. For example, '.....' is replaced with '.'."""

    while char * 2 in s:
        s = s.replace(char * 2, char)

    return s

def remove_junk(text: str) -> str:
    """Remove junk characters from text.  Junk characters are any non-alphabetic characters,
       numbers or any of the normal punctuation characters.
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

def convert_roman_to_integer(reference_text):
    """
    Converts all Roman numeral occurrences in the reference text to numeric values.
    Roman numerals are case-insensitive (e.g. IV == iv == 4).
    """
    # Regex to match Roman numerals (case-insensitive)
    pattern = re.compile(r'\b(IV|IX|XL|XC|L|C|D|M|I|V|X)+\b', re.IGNORECASE)

    def replacer(matched):
        # Extract the matched Roman numeral
        roman_numeral = matched.group(0)
        try:
            # Use `fromRoman` to convert Roman numeral to an integer
            return str(fromRoman(roman_numeral))
        except InvalidRomanNumeralError:
            # In case of invalid Roman numerals, return the original text
            return roman_numeral

    # Replace all valid Roman numerals in the reference text with their numeric equivalents
    return pattern.sub(replacer, reference_text)

def load_settings_from_file(filename="settings.json"):
    """
    Load the settings dictionary from a JSON file.
    If the file is missing, empty, malformed, or has partial settings, return defaults.
    """
    # Default settings
    default_settings = {
        "theme": "Light",
        "show_splash": False
    }

    # Check if the file exists
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
                settings_here.setdefault(key, value)

            # print("Loaded settings:", settings_here)
            return settings_here

    except JSONDecodeError:
        print("Settings file is malformed. Overwriting with default settings.")
        return default_settings
    except Exception as err:
        print(f"Error loading settings: {err}. Using default settings.")
        return default_settings

def isRoman(s: str) -> bool:
    """Regular expression to match valid Roman numerals"""

    roman_pattern = r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
    s = s.upper()
    return bool(re.match(roman_pattern, s))
