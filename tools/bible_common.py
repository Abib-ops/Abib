import re
import unicodedata

CANONICAL_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
    "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
]

SINGLE_CHAPTER_BOOKS = {"Obadiah", "Philemon", "2 John", "3 John", "Jude"}

def is_mostly_caps(s):
    # Normalise to handle mathematical alphanumeric symbols (italics)
    s = unicodedata.normalize('NFKC', s)
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return True
    caps = [c for c in letters if c.isupper()]
    return len(caps) / len(letters) > 0.9

def parse_pce_text(txt_path):
    """
    Parses KJB_PCE.txt into a dict: (book, chapter, verse) -> text
    Matches the logic in generate_new_bible_json.py for reliability.
    """
    data = {}
    current_book_idx = -1
    current_book = None
    current_chapter = None
    current_verse = None
    current_text = []

    def flush():
        if current_book and current_chapter and current_verse:
            text = " ".join(current_text)
            text = " ".join(text.split())
            data[(current_book, current_chapter, current_verse)] = text

    def is_book_match(book_name, line_text):
        upper_line = line_text.upper()
        if len(upper_line) > 100:
            return False
        
        # Book headers are usually not verses.
        # If it starts with a verse number followed by lowercase, it's definitely a verse.
        if re.match(r'^\d+\s', line_text) and not is_mostly_caps(line_text):
            return False
            
        if not is_mostly_caps(line_text):
            return False

        b = book_name.upper()
        
        # Numeric books
        if b[0].isdigit() and " " in b:
            prefix = b[0]
            rest = b[2:]
            ordinals = {
                "1": ["I ", "FIRST", "1 "],
                "2": ["II ", "SECOND", "2 "],
                "3": ["III ", "THIRD", "3 "]
            }[prefix]
            
            # If the line contains both ordinal and the rest (e.g. "I JOHN")
            found_ordinal = False
            for o in ordinals:
                if o in upper_line:
                    found_ordinal = True
                    break
            if not found_ordinal:
                return False
                
            if rest not in upper_line:
                return False
            
            # Additional check: numeric books often have "THE ... BOOK" or "THE ... EPISTLE"
            # or just the name. But they should NOT have too many other texts.
            if len(upper_line) > 40 and "EPISTLE" not in upper_line and "BOOK" not in upper_line:
                return False
                
            return True

        # Standard books
        if b in upper_line:
            if b == "JOB":
                return "BOOK OF JOB" in upper_line or upper_line.strip('.') == "JOB"
            if b == "ACTS":
                return "ACTS" in upper_line and ("APOSTLES" in upper_line or upper_line.strip('.') == "ACTS")
            if b == "PSALMS":
                return "PSALMS" in upper_line or "PSALM" in upper_line
            # For other books, keep it strict
            if len(upper_line) > 40 and "BOOK" not in upper_line and "EPISTLE" not in upper_line:
                return False
            return True
        
        return False

    header_buffer = []
    with open(txt_path, 'r', encoding='utf-8') as f:
        # Skip preface/index (roughly 300 lines)
        for _ in range(300):
            next(f, None)
            
        for line in f:
            line = line.strip('\n')
            stripped = line.strip()
            if not stripped:
                header_buffer = [] # Reset buffer on empty line
                continue
            
            # Check for Book Transition or Noise Headers
            is_cap = is_mostly_caps(stripped)
            if is_cap:
                header_buffer.append(stripped)
                combined_header = " ".join(header_buffer)
                
                # 1. Try transition to NEXT book
                if current_book_idx + 1 < len(CANONICAL_BOOKS):
                    next_book = CANONICAL_BOOKS[current_book_idx + 1]
                    if is_book_match(next_book, combined_header):
                        # print(f"DEBUG: Transition to {next_book} at line: {combined_header}")
                        flush()
                        current_book = next_book
                        current_book_idx += 1
                        current_chapter = None
                        current_verse = None
                        current_text = []
                        header_buffer = []
                        if current_book in SINGLE_CHAPTER_BOOKS:
                            current_chapter = "1"
                            current_verse = "1"
                        continue

                # 2. Check if it matches ANY book (repeating header or out-of-order)
                # If it matches any book name, we discard it as a header.
                is_any_book = False
                for b_name in CANONICAL_BOOKS:
                    if is_book_match(b_name, combined_header):
                        is_any_book = True
                        break
                
                if is_any_book:
                    header_buffer = []
                    continue
            else:
                header_buffer = []

            if current_book and stripped.strip('.').upper() == current_book.upper():
                continue
            
            if "APPOINTED TO BE READ" in stripped.upper():
                continue

            # Check for CHAPTER or PSALM
            m_chap = re.match(r'^(?:CHAPTER|PSALM)\s+(\d+)', stripped)
            if m_chap:
                flush()
                current_chapter = m_chap.group(1)
                current_verse = "1"
                current_text = []
                continue

            # Check for Verse N (N > 1)
            m_verse = re.match(r'^(\d+)\s+(.*)', stripped)
            if m_verse and current_book and current_chapter:
                v_num, v_text = m_verse.groups()
                flush()
                current_verse = v_num
                current_text = [v_text]
                continue
            
            # If it's a caps line that didn't match anything above,
            # we ignore it (likely noise or multi-line header fragment).
            if is_cap:
                continue

            if current_verse:
                current_text.append(stripped)
                
    flush()
    return data
