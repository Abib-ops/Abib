from .files import (
    load_json_dict,
    load_list_set_dict,
    readfile,
    readio,
)
from .platform import (
    is_linux,
    is_macos,
    is_windows,
    is_windows_10,
)
from .roman_utils import (
    convert_roman_to_integer,
    isRoman,
)
from .text import (
    create_pattern,
    is_float_re,
    punctuation_counter,
    remove_junk,
    split_strip,
    squeeze,
)
from .ui import (
    center_on_screen,
    fit_to_screen,
    get_screen_size,
)

__all__ = [
    'center_on_screen',
    'convert_roman_to_integer',
    'create_pattern',
    'fit_to_screen',
    'get_screen_size',
    'isRoman',
    'is_float_re',
    'is_linux',
    'is_macos',
    'is_windows',
    'is_windows_10',
    'load_json_dict',
    'load_list_set_dict',
    'punctuation_counter',
    'readfile',
    'readio',
    'remove_junk',
    'split_strip',
    'squeeze',
]
