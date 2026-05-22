import re
from roman import fromRoman, InvalidRomanNumeralError

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
