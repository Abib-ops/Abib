import re
from string import ascii_letters, digits

def split_strip(_key: str) -> tuple[int, str]:
    """Remove whitespace from '_key' entered as passage reference."""
    p = " ()[];:'!<>,.-?"       # Characters to strip ’ not needed.
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
    allowed_set = set(ascii_letters + digits + "():,’;-?[].!<> ")
    rex: str = "".join(ch for ch in text if ch in allowed_set)

    if text.lstrip('-').isdigit():
        return text  # Return the number as-is if it's valid
    else:
        #  Remove any junk from the beginning of a reference.
        res = re.search("[a-zA-Z0-9]+", rex)
        if res:
            rex = rex[res.start():]

        #  Remove any junk from the end of a reference.
        res_end = re.search("[a-zA-Z0-9]+", rex[::-1])
        if res_end:
            k: int = res_end.start()
            if k > 0:
                rex = rex[:-k]

        #  Remove possible duplicate '.' or ':' chapter verse seperator.
        rex = squeeze('.', rex)
        rex = squeeze(':', rex)

        #  Remove possible KJV ending.
        if rex.endswith(' KJV'):
            rex = rex[:-4]
    return rex

def is_float_re(string_: str) -> bool:
    """Take a string and determine if it represents a float."""
    pattern = r"^[-+]?(?:\b[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+\b)?$"
    m = re.match(pattern, string_)
    return m is not None
