import re
import unicodedata
from project_setup import SRC_PATH
from bible_common import parse_pce_text

def normalize_text(text):
    if not text:
        return ""
    # NFKC normalizes mathematical alphanumeric symbols to standard letters
    text = unicodedata.normalize('NFKC', text)
    # Remove Pilcrow signs
    text = text.replace('¶', '')
    # Standardise apostrophes
    text = text.replace('’', "'")
    # Normalise whitespace
    text = ' '.join(text.split())
    return text

def get_bible_json_data(json_path):
    """
    Parses bible_data.json line by line to keep track of line numbers.
    Returns a dict: (book, chapter, verse) -> (text, line_number)
    """
    data = {}
    current_book = None
    current_chapter = None
    
    book_re = re.compile(r'^\s+"([^"]+)":\s+\{$')
    chapter_re = re.compile(r'^\s+"(\d+)":\s+\{$')
    # Match verse: "17": "text", or "17": "text"
    verse_re = re.compile(r'^\s+"(\d+)":\s+"(.*)"(,?)$')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip('\n')
            
            # Match verse
            m_verse = verse_re.match(line)
            if m_verse:
                v_num, v_text, _ = m_verse.groups()
                # Basic JSON unescaping for quotes
                v_text = v_text.replace('\\"', '"')
                data[(current_book, current_chapter, v_num)] = (v_text, i)
                continue
                
            # Match chapter
            m_chapter = chapter_re.match(line)
            if m_chapter:
                current_chapter = m_chapter.group(1)
                continue
                
            # Match book
            m_book = book_re.match(line)
            if m_book:
                name = m_book.group(1)
                if not name.isdigit():
                    current_book = name
                    current_chapter = None
                    
    return data


def main():
    data_dir = SRC_PATH / "abib" / "data"
    json_path = data_dir / "bible_data.json"
    txt_path_kjb = data_dir / "KJB_PCE.txt"
    txt_path_kjv = data_dir / "KJV_PCE.txt"
    
    if txt_path_kjv.exists():
        txt_path = txt_path_kjv
    else:
        txt_path = txt_path_kjb
    
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
    if not txt_path.exists():
        print(f"Error: {txt_path} not found")
        return
        
    print(f"Loading {json_path.name}...")
    json_data = get_bible_json_data(json_path)
    
    print(f"Parsing {txt_path.name}...")
    pce_data = parse_pce_text(txt_path)
    
    print("Comparing verses...")
    diff_count = 0
    
    # Track which PCE verses we've seen to find extras later if needed
    pce_seen = set()

    for key, (json_text, line_num) in json_data.items():
        if key in pce_data:
            pce_seen.add(key)
            pce_text = pce_data[key]
            
            norm_json = normalize_text(json_text)
            norm_pce = normalize_text(pce_text)
            
            if norm_json != norm_pce:
                diff_count += 1
                book, chap, verse = key
                print(f"Difference in {book} {chap}:{verse} (JSON line {line_num}):")
                print(f"  JSON: {json_text}")
                print(f"  PCE:  {pce_text}")
                print("-" * 20)
        else:
            # Optionally report missing
            # print(f"Not found in PCE: {key}")
            pass

    print(f"Total differences found: {diff_count}")

if __name__ == "__main__":
    main()
