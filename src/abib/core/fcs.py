# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

################################################################################
## Module containing various functions.
##
## Used by Abib.py (sh.CURRENT_VERSION) =>
################################################################################

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from abib import utils
from abib.core import shared as sh

ANY_OF_WORDS_IGNORED_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "i", "in", "is", "it", "its",
    "not", "of", "on", "or", "that", "the", "their", "them", "they", "this",
    "to", "was", "were", "which", "with", "ye", "you",
}


def get_screen_size() -> tuple[int, int]:
    """Get the primary screen dimensions."""
    return utils.get_screen_size()


def split_strip(_key: str) -> tuple[int, str]:
    """Remove whitespace from '_key' entered as passage reference."""
    return utils.split_strip(_key)


def create_pattern(key: str) -> str:
    """Create a regex pattern based on the given key."""
    return utils.create_pattern(key)


def punctuation_counter(text_in: str) -> int:
    """Count the number of punctuation characters in text."""
    return utils.punctuation_counter(text_in)


def repeat_find(rx: str, start: int, end: int) -> int:
    """Repeat find of lengthening text.

    The rx variable is the verse from the PCE-find.txt file
    or a similar file without italics.
    """

    flag: bool = True
    numb: int
    sumb: int = 0
    repeats: int = 0
    while flag:
        text_val: str = rx[start:end + sumb]
        numb = utils.punctuation_counter(text_val)
        sumb += numb
        start = end + sumb - numb
        repeats += 1
        if repeats > 15 or numb == 0:
            flag = False

    return sumb


def repeat_find_keyinc(rx: str, start: int, end: int) -> int:
    """Repeat find of lengthening text.

    The rx variable is the verse from the PCE-find.txt file
    or a similar file without italics."""

    numb: int
    sumb = 0
    while True:
        text_val: str = rx[start:end]
        numb = utils.punctuation_counter(text_val)
        sumb += numb
        if numb == 0:
            break
        start = end
        end += numb

    return sumb


def readio(input_filename: str, file_length: int) -> list:
    """Read Bible files."""
    return utils.readio(input_filename, file_length, sh.base_dir)


def load_json_dict(file_dict: Any) -> Any:
    """Load a dictionary with JSON."""
    return utils.load_json_dict(file_dict, sh.base_dir)


def load_list_set_dict(input_filename: str, ref_dict: Any) -> dict[Any, set]:
    """Load a list_dict.txt/json file that is a dictionary of Bible words."""
    return utils.load_list_set_dict(input_filename, ref_dict, sh.base_dir)


def is_float_re(string_: str) -> bool:
    """Take a string and determine if it represents a float."""
    return utils.is_float_re(string_)


def any_of_the_words_lookup(_key: str, _set: dict[str, set]) -> tuple[int, str]:
    """Takes '_key' and splits it into separate words in 'liszt',
    which are then looked up in the set of Bible words.

    Returns modified '_key' and 'count' in 'number_of_occurrences' of the words in it."""

    liszt: list[str] = _key.split(' ')

    # Uses a set to eliminate duplicates, keep words found in '_set', and skip
    # very common words that can make an "Any of the words" search return almost
    # every verse.
    unique_words = {
        word for word in liszt
        if word in _set and word.lower() not in ANY_OF_WORDS_IGNORED_WORDS
    }

    _key = ' '.join(sorted(unique_words))  # join the set into a string

    number_of_occurrences = len(unique_words)  # count the number of unique words

    return number_of_occurrences, _key


def squeeze(char: str, s: str) -> str:
    """Remove duplicate characters. For example, '.....' is replaced with '.'."""
    return utils.squeeze(char, s)


def remove_junk(text_in: str) -> str:
    """Remove junk characters from 'text'."""
    return utils.remove_junk(text_in)


def convert_roman_to_integer(reference_text: str) -> str:
    """Converts all Roman numeral occurrences in the reference text to numeric values."""
    return utils.convert_roman_to_integer(reference_text)


def isRoman(s: str) -> bool:
    """Regular expression to match valid Roman numerals"""
    return utils.isRoman(s)




def compare_versions(version1: str, version2: str) -> int:
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
    # Helper to clean and split version string
    def clean_and_split(v: Any) -> list[int]:
        if not v or not isinstance(v, str):
            return [0]
        v = v.strip()
        v = v.removeprefix("v")
        parts = []
        for p in v.split("."):
            # Extract only digits from the start of the part
            match = re.match(r"(\d+)", p)
            if match:
                try:
                    parts.append(int(match.group(1)))
                except ValueError:
                    parts.append(0)
            else:
                parts.append(0)
        return parts

    v1_parts = clean_and_split(version1)
    v2_parts = clean_and_split(version2)

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

    # Remove spaces from '2 Corinthians' etc.
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

    # Further split parts with mixed letters and numbers (e.g. 'g2' -> ['g', '2'])
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
    today = datetime.now(tz=timezone.utc).astimezone() + timedelta(hours=date_index)

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
