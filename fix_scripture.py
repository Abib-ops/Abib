import re
path = r'src\abib\core\scripture.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'short_alpha_keys = [k for k in sh.bibledict.keys() if k.isalpha() and len(k) <= 3]',
    'short_alpha_keys = _SHORT_ALPHA_KEYS'
)

if '_SHORT_ALPHA_KEYS = [' not in content:
    content = content.replace(
        'def classify_book_input(user_input: str) -> Dict[str, Any]:',
        '_SHORT_ALPHA_KEYS = [k for k in sh.bibledict.keys() if k.isalpha() and len(k) <= 3]'
        '\\n\\n\\ndef classify_book_input(user_input: str) -> Dict[str, Any]:'
    )

regex_defs = (
    '_RE_ORD1 = re.compile(r\\^1\\\\s*st\\\\.?\\)\\n'
    '_RE_ORD2 = re.compile(r\\^2\\\\s*nd\\\\.?\\)\\n'
    '_RE_ORD3 = re.compile(r\\^3\\\\s*rd\\\\.?\\)\\n'
    '_RE_FIRST = re.compile(r\\^first\\\\b\\)\\n'
    '_RE_SECOND = re.compile(r\\^second\\\\b\\)\\n'
    '_RE_THIRD = re.compile(r\\^third\\\\b\\)\\n'
    '_RE_ROMAN_III = re.compile(r\\^(iii)(?=\\\\b|\\\\s|\\\\.)\\)\\n'
    '_RE_ROMAN_II = re.compile(r\\^(ii)(?=\\\\b|\\\\s|\\\\.)\\)\\n'
    '_RE_ROMAN_I = re.compile(r\\^(i)(?=\\\\b|\\\\s|\\\\.)\\)\\n'
    '_RE_NON_WORD = re.compile(r\\\\\\W+\\)'
)

if '_RE_ORD1 =' not in content:
    content = content.replace(
        'def normalize_book_input(book_input: str) -> str:',
        regex_defs + '\\n\\ndef normalize_book_input(book_input: str) -> str:'
    )

content = content.replace(
    're.sub(r\\^1\\\\s*st\\\\.?\\, \\1\\, s)',
    '_RE_ORD1.sub(\\1\\, s)'
)
content = content.replace(
    're.sub(r\\^2\\\\s*nd\\\\.?\\, \\2\\, s)',
    '_RE_ORD2.sub(\\2\\, s)'
)
content = content.replace(
    're.sub(r\\^3\\\\s*rd\\\\.?\\, \\3\\, s)',
    '_RE_ORD3.sub(\\3\\, s)'
)
content = content.replace(
    're.sub(r\\^first\\\\b\\, \\1\\, s)',
    '_RE_FIRST.sub(\\1\\, s)'
)
content = content.replace(
    're.sub(r\\^second\\\\b\\, \\2\\, s)',
    '_RE_SECOND.sub(\\2\\, s)'
)
content = content.replace(
    're.sub(r\\^third\\\\b\\, \\3\\, s)',
    '_RE_THIRD.sub(\\3\\, s)'
)
content = content.replace(
    're.sub(r\\^(iii)(?=\\\\b|\\\\s|\\\\.)\\, \\3\\, s)',
    '_RE_ROMAN_III.sub(\\3\\, s)'
)
content = content.replace(
    're.sub(r\\^(ii)(?=\\\\b|\\\\s|\\\\.)\\, \\2\\, s)',
    '_RE_ROMAN_II.sub(\\2\\, s)'
)
content = content.replace(
    're.sub(r\\^(i)(?=\\\\b|\\\\s|\\\\.)\\, \\1\\, s)',
    '_RE_ROMAN_I.sub(\\1\\, s)'
)
content = content.replace(
    're.sub(r\\\\\\W+\\, \\\\, s)',
    '_RE_NON_WORD.sub(\\\\, s)'
)

ws_def_match = re.search(r'_WS = r\\(.*?)\\', content)
