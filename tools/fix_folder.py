# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""
This is to correct encoding errors in the downloaded UTF-8 Unicode files.

It works inside the folder you specify and corrects encoding errors in the files within it.

Copy the files to an empty folder of your choosing and then run this script.

"""

import glob
import os
import re
import sys


def detect_text_language(text):
    """Detect if the text contains Hebrew, Arabic, or other languages."""
    
    # Count Hebrew characters (Hebrew block: U+0590-U+05FF)
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    
    # Count Arabic characters (Arabic block: U+0600-U+06FF)
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    
    # Count Latin characters
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    
    # Count total characters (excluding spaces and punctuation)
    total_chars = len(re.findall(r'[^\s\W]', text))
    
    if total_chars == 0:
        return "unknown"
    
    hebrew_ratio = hebrew_chars / total_chars
    arabic_ratio = arabic_chars / total_chars
    latin_ratio = latin_chars / total_chars
    
    # Determine primary language
    if hebrew_ratio > 0.1:  # 10% threshold for Hebrew
        return "hebrew"
    elif arabic_ratio > 0.1:  # 10% threshold for Arabic
        return "arabic"
    elif latin_ratio > 0.7:   # 70% threshold for a Latin script
        return "latin"
    else:
        return "mixed"

def has_hebrew_transliterations(text):
    """Check if text contains Hebrew transliteration patterns."""
    
    hebrew_patterns = [
        r'\bcht[ÃÝÿ]',  # chateph patterns
        r'\blphy\b',     # lephi
        r'\bLephi\b',    # Lephi
        r'\bchataph\b',  # chataph
        r'\bqm[ÃÝÿ]',   # qametz patterns
        r'\bpth[ÃÝÿ]',  # patach patterns
        r'\bshrq[ÃÝÿ]', # shureq patterns
        r'\bsg[ÃÝÿ]',   # segol patterns
        r'\bhir[ÃÝÿ]',  # hireq patterns
        r'\bhol[ÃÝÿ]',  # holam patterns
        r'\bqbb[ÃÝÿ]',  # qibbuts patterns
    ]
    
    for pattern in hebrew_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def apply_corrections(text, mapping):
    """Apply a mapping of corrupted -> correct substrings and count changes.

    Returns a tuple: (corrected_text, corrections_made)
    """
    corrected_text = text
    corrections_made = 0
    for corrupted, correct in mapping.items():
        if corrupted in corrected_text:
            count = corrected_text.count(corrupted)
            corrected_text = corrected_text.replace(corrupted, correct)
            corrections_made += count
    return corrected_text, corrections_made

def fix_hebrew_corruptions(text):
    """Fix UTF-8 corruption patterns specific to Hebrew text."""
    
    # Hebrew-specific corruption patterns
    hebrew_corrections = {
        # Common Hebrew transliteration corruptions to Hebrew Unicode
        # Multiple variations of chateph corruption
        "chtÃ": "חֲטַף",     # chateph (short vowel) - original pattern
        "chtÝ": "חֲטַף",     # chateph with Ý corruption
        "chtÿ": "חֲטַף",     # chateph with ÿ corruption
        "chtý": "חֲטַף",     # chateph with ý corruption
        "chta": "חֲטַף",     # chateph without corruption marker
        "chat": "חֲטַף",     # shortened chateph
        "chateph": "חֲטַף",  # full transliteration
        
        # Context-specific patterns
        "lphy chtÃ": "לְפִי חֲטַף",    # according to chateph - original
        "lphy chtÝ": "לְפִי חֲטַף",    # according to chateph - with Ý
        "lphy chtÿ": "לְפִי חֲטַף",    # according to chateph - with ÿ
        "lphy chtý": "לְפִי חֲטַף",    # according to chateph - with ý
        "lphy": "לְפִי",              # standalone lphy
        "(Lephi chataph)": "(לְפִי חֲטַף)",  # parenthetical form
        "Lephi chataph": "לְפִי חֲטַף",      # without parentheses
        
        # Other Hebrew vowel corruptions
        "qmÃ": "קָמֵץ", "qmÝ": "קָמֵץ", "qmÿ": "קָמֵץ", "qmý": "קָמֵץ",      # qametz variations
        "pthÃ": "פַּתַח", "pthÝ": "פַּתַח", "pthÿ": "פַּתַח", "pthý": "פַּתַח",    # patach variations
        "shrqÃ": "שְׁרֵק", "shrqÝ": "שְׁרֵק", "shrqÿ": "שְׁרֵק", "shrqý": "שְׁרֵק",   # shureq variations
        "sgÃ": "סְגוֹל", "sgÝ": "סְגוֹל", "sgÿ": "סְגוֹל", "sgý": "סְגוֹל",     # segol variations
        "hirÃ": "חִירֵק", "hirÝ": "חִירֵק", "hirÿ": "חִירֵק", "hirý": "חִירֵק",    # hireq variations
        "holÃ": "חוֹלָם", "holÝ": "חוֹלָם", "holÿ": "חוֹלָם", "holý": "חוֹלָם",    # holam variations
        "qbbÃ": "קִבּוּץ", "qbbÝ": "קִבּוּץ", "qbbÿ": "קִבּוּץ", "qbbý": "קִבּוּץ",   # qibbuts variations
        
        # Hebrew letter corruptions with multiple patterns
        "alÃ": "אָלֶף", "alÝ": "אָלֶף", "alÿ": "אָלֶף", "alý": "אָלֶף",      # aleph
        "btÃ": "בֵּית", "btÝ": "בֵּית", "btÿ": "בֵּית", "btý": "בֵּית",      # bet
        "gmlÃ": "גִּימֶל", "gmlÝ": "גִּימֶל", "gmlÿ": "גִּימֶל", "gmlý": "גִּימֶל",   # gimel
        "dltÃ": "דָּלֶת", "dltÝ": "דָּלֶת", "dltÿ": "דָּלֶת", "dltý": "דָּלֶת",    # dalet
        "hÃ": "הֵא", "hÝ": "הֵא", "hÿ": "הֵא", "hý": "הֵא",         # he
        "vvÃ": "וָו", "vvÝ": "וָו", "vvÿ": "וָו", "vvý": "וָו",        # vav
        "zynÃ": "זַיִן", "zynÝ": "זַיִן", "zynÿ": "זַיִן", "zyný": "זַיִן",     # zayin
        "htÃ": "חֵית", "htÝ": "חֵית", "htÿ": "חֵית", "htý": "חֵית",       # chet
        "ttÃ": "טֵית", "ttÝ": "טֵית", "ttÿ": "טֵית", "ttý": "טֵית",       # tet
        "ywdÃ": "יוֹד", "ywdÝ": "יוֹד", "ywdÿ": "יוֹד", "ywdý": "יוֹד",      # yod
        
        # Common Hebrew words that might be corrupted
        "shbÃ": "שַׁבָּת", "shbÝ": "שַׁבָּת", "shbÿ": "שַׁבָּת", "shbý": "שַׁבָּת",   # Shabbat
        "trhÃ": "תּוֹרָה", "trhÝ": "תּוֹרָה", "trhÿ": "תּוֹרָה", "trhý": "תּוֹרָה",   # Torah
        "mzvÃ": "מִצְוָה", "mzvÝ": "מִצְוָה", "mzvÿ": "מִצְוָה", "mzvý": "מִצְוָה",   # mitzvah
        "brzÃ": "בָּרָזֶל", "brzÝ": "בָּרָזֶל", "brzÿ": "בָּרָזֶל", "brzý": "בָּרָזֶל",  # iron/metal
        "mlkÃ": "מֶלֶךְ", "mlkÝ": "מֶלֶךְ", "mlkÿ": "מֶלֶךְ", "mlký": "מֶלֶךְ",    # king
    }
    
    return apply_corrections(text, hebrew_corrections)

def fix_standard_utf8_corruption(text):
    """Fix common UTF-8 to Latin-1 corruption patterns for European languages."""
    
    corrections = {
        # Lowercase letters with diacritics
        "Ã ": "à", "Ã¡": "á", "Ã¢": "â", "Ã£": "ã", "Ã¤": "ä", "Ã¥": "å",
        "Ã§": "ç", "Ã¨": "è", "Ã©": "é", "Ãª": "ê", "Ã«": "ë",
        "Ã¬": "ì", "Ã­": "í", "Ã®": "î", "Ã¯": "ï",
        "Ã±": "ñ", "Ã²": "ò", "Ã³": "ó", "Ã´": "ô", "Ãµ": "õ", "Ã¶": "ö",
        "Ã¹": "ù", "Ãº": "ú", "Ã»": "û", "Ã¼": "ü", "Ã½": "ý", "Ã¿": "ÿ",
        
        # Capital letters with diacritics  
        "Ã€": "À", "Ã\x81": "Á", "Ã‚": "Â", "Ãƒ": "Ã", "Ã„": "Ä", "Ã…": "Å",
        "Ã‡": "Ç", "Ãˆ": "È", "Ã‰": "É", "ÃŠ": "Ê", "Ã‹": "Ë",
        "ÃŒ": "Ì", "Ã\x8D": "Í", "ÃŽ": "Î", "Ã\x8F": "Ï", "Ã\x90": "Ð",
        "Ã\x91": "Ñ", "Ã\x92": "Ò", "Ã\x93": "Ó", "Ã\x94": "Ô", "Ã•": "Õ", "Ã–": "Ö",
        "Ã™": "Ù", "Ãš": "Ú", "Ã›": "Û", "Ãœ": "Ü", "Ã\x9D": "Ý",
        
        # Special characters
        "Ã¦": "æ", "Ã°": "ð", "Ã¸": "ø", "Ã¾": "þ",
        "Ã†": "Æ", "Ã˜": "Ø", "Ãž": "Þ", "ÃŸ": "ß",
        
        # Common punctuation/symbols
        "Â¡": "¡", "Â¢": "¢", "Â£": "£", "Â¤": "¤", "Â¥": "¥",
        "Â§": "§", "Â©": "©", "Â®": "®", "Â°": "°", "Â±": "±",
        "Â²": "²", "Â³": "³", "Â¹": "¹", "Â¼": "¼", "Â½": "½",
        "Â¾": "¾", "Â¿": "¿",
        
        # Additional common corruptions
        "Â€": "€", "Â‚": "‚", "Âƒ": "ƒ", "Â„": "„", "Â…": "…",
        "Â†": "†", "Â‡": "‡", "Âˆ": "ˆ", "Â‰": "‰", "ÂŠ": "Š",
        "Â‹": "‹", "ÂŒ": "Œ", "ÂŽ": "Ž", "Â'": "'",
        'Â"': '"', "Â•": "•", "Â–": "–", "Â—": "—",
        "Ëœ": "˜", "Â™": "™", "Âš": "š", "Â›": "›", "Âœ": "œ",
        "Âž": "ž", "ÂŸ": "Ÿ", "ý¦": "ae", "ý†": "Æ",
        
        # Generic fallback for isolated corruption markers before punctuation
        "Ã,": "â,", "Ý,": "ý,", "ÿ,": "ÿ,", "ý,": "ý,",
        "Ã:": "â:", "Ý:": "ý:", "ÿ:": "ÿ:", "ý:": "ý:",
        "Ã.": "â.", "Ý.": "ý.", "ÿ.": "ÿ.", "ý.": "ý.",
        "Ã;": "â;", "Ý;": "ý;", "ÿ;": "ÿ;", "ý;": "ý;",
        "Ã!": "â!", "Ý!": "ý!", "ÿ!": "ÿ!", "ý!": "ý!",
        "Ã?": "â?", "Ý?": "ý?", "ÿ?": "ÿ?", "ý?": "ý?",
        "Ã)": "â)", "Ý)": "ý)", "ÿ)": "ÿ)", "ý)": "ý)",
        "Ã]": "â]", "Ý]": "ý]", "ÿ]": "ÿ]", "ý]": "ý]",
        # Cover additional symbol cases raised by users
        "Ý†": "ý†", "Ý¦": "ý¦",
        # Allow lowercase counterparts to pass through unchanged
        "Ý ": "ý ", "ÿ ": "ÿ ", "ý ": "ý ",
    }
    
    return apply_corrections(text, corrections)

def fix_utf8_corruption(text):
    """Apply appropriate UTF-8 corruption fixes based on detected language and content."""
    
    # Detect the primary language of the text
    language = detect_text_language(text)
    has_hebrew_translits = has_hebrew_transliterations(text)
    
    print(f"  Detected language context: {language}")
    print(f"  Contains Hebrew transliterations: {has_hebrew_translits}")
    
    total_corrections = 0
    corrected_text = text
    
    # Always apply Hebrew corrections if Hebrew transliterations are detected
    if has_hebrew_translits or language == "hebrew":
        print("  Applying Hebrew corrections...")
        corrected_text, hebrew_corrections = fix_hebrew_corruptions(corrected_text)
        total_corrections += hebrew_corrections
        print(f"  Hebrew corrections made: {hebrew_corrections}")
    
    # Apply standard corrections for remaining patterns
    print("  Applying standard UTF-8 corrections...")
    corrected_text, standard_corrections = fix_standard_utf8_corruption(corrected_text)
    total_corrections += standard_corrections
    print(f"  Standard corrections made: {standard_corrections}")
    
    return corrected_text, total_corrections

def clean_previous_corrected_files(folder_path):
    """Delete all files ending with '-corrected.txt' in the folder."""
    
    # Find all files ending with '-corrected.txt'
    corrected_pattern = os.path.join(folder_path, "*-corrected.txt")
    corrected_files = glob.glob(corrected_pattern)
    
    if not corrected_files:
        print("No previous '-corrected.txt' files found to delete.")
        return 0
    
    deleted_count = 0
    failed_deletions = []
    
    print(f"Found {len(corrected_files)} previous '-corrected.txt' files to delete:")
    
    for corrected_file in corrected_files:
        filename = os.path.basename(corrected_file)
        try:
            os.remove(corrected_file)
            print(f"  ✓ Deleted: {filename}")
            deleted_count += 1
        except OSError as e:
            print(f"  ✗ Failed to delete {filename}: {e}")
            failed_deletions.append(filename)
    
    if failed_deletions:
        print(f"Warning: Failed to delete {len(failed_deletions)} files:")
        for failed_file in failed_deletions:
            print(f"  - {failed_file}")
    
    print(f"Successfully deleted {deleted_count} previous corrected files.\n")
    return deleted_count

def correct_file_encoding(input_filename):
    """Read a file and correct UTF-8 corruption, then save it to a new file."""
    
    # Create output filename
    name, ext = os.path.splitext(input_filename)
    output_filename = f"{name}-corrected{ext}"
    
    try:
        # Read the input file
        with open(input_filename, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Fix corruptions
        corrected_content, total_corrections = fix_utf8_corruption(content)
        
        # Write the corrected content
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write(corrected_content)
        
        return total_corrections
        
    except UnicodeDecodeError as e:
        print(f"  Error: Could not read file as UTF-8. {e}")
        return -1
    except (OSError, UnicodeError, ValueError) as e:
        print(f"  Error: {e}")
        return -1

def process_folder(folder_path):
    """Process all .txt files in the given folder."""
    
    # Check if the folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' not found.")
        return False
    
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a directory.")
        return False
    
    # Clean up the previously corrected files first
    print("=" * 50)
    print("CLEANING PREVIOUS CORRECTED FILES")
    print("=" * 50)
    clean_previous_corrected_files(folder_path)
    
    # Find all .txt files in the folder (excluding corrected files)
    txt_pattern = os.path.join(folder_path, "*.txt")
    all_txt_files = glob.glob(txt_pattern)
    
    # Filter out any remaining corrected files (in case deletion failed)
    txt_files = [f for f in all_txt_files if not f.endswith("-corrected.txt")]
    
    if not txt_files:
        print(f"No source .txt files found in '{folder_path}' (excluding corrected files)")
        return False
    
    print("=" * 50)
    print("PROCESSING SOURCE FILES")
    print("=" * 50)
    print(f"Found {len(txt_files)} source .txt files in '{folder_path}'")
    
    total_files_processed = 0
    total_corrections = 0
    failed_files = []
    
    for txt_file in txt_files:
        filename = os.path.basename(txt_file)
        print(f"\nProcessing: {filename}")
        
        corrections = correct_file_encoding(txt_file)
        
        if corrections >= 0:
            total_files_processed += 1
            total_corrections += corrections
            if corrections > 0:
                print(f"  ✓ Total corrections made: {corrections}")
                corrected_name = filename.replace(".txt", "-corrected.txt")
                print(f"  ✓ Saved as: {corrected_name}")
            else:
                print("  ✓ No corruptions found - file processed successfully")
                corrected_name = filename.replace(".txt", "-corrected.txt")
                print(f"  ✓ Clean copy saved as: {corrected_name}")
        else:
            failed_files.append(filename)
            print("  ✗ Failed to process")
    
    # Summary
    print("\n" + "=" * 50)
    print("PROCESSING COMPLETE")
    print("=" * 50)
    print(f"Total files processed: {total_files_processed}")
    print(f"Total corrections made: {total_corrections}")
    
    if failed_files:
        print(f"Failed files ({len(failed_files)}):")
        for failed_file in failed_files:
            print(f"  - {failed_file}")
    
    return total_files_processed > 0

def main():
    """Main function to handle command line arguments or interactive input."""
    
    if len(sys.argv) > 1:
        # Use command line argument
        folder_path = sys.argv[1]
    else:
        # Ask for the folder path interactively
        folder_path = input("Enter the folder path containing .txt files: ").strip()
        if not folder_path:
            print("No folder path provided.")
            return
    
    # Handle relative paths and expand the user home directory
    folder_path = os.path.expanduser(folder_path)
    folder_path = os.path.abspath(folder_path)
    
    print(f"Processing all .txt files in: {folder_path}")
    success = process_folder(folder_path)
    
    if success:
        print("\nAll files processed successfully!")
    else:
        print("\nProcessing failed or no files were processed.")

if __name__ == "__main__":
    main()
