# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

import re
import sys
from pathlib import Path


def normalize_apostrophes(text):
    """
    Applies normalisation rules to remove extra spaces around apostrophes.
    Returns the modified text and a list of changes made.
    """
    # Support both straight and curly apostrophes
    apos = "['\u2019]"
    changes = []
    
    # We'll process line by line to track changes better
    lines = text.splitlines()
    new_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Layer 1: Core apostrophe-space fixes (specifically for 's' or 'S')
        # Rule: WORD' S -> WORD'S (single letter S/s)
        # Avoid fixing if preceded by s/S to protect plural possessives like "Jesus' "
        # but the single-letter check (?=\s|$) already protects "Jesus' sake"
        
        # Layer 3: False-positive protection
        # We use a pattern that requires a letter before the apostrophe, 
        # but NOT an 's' or 'S' if we want to be extremely conservative.
        # Actually, let's allow any letter but keep it to single 'S'/'s' after.
        
        # Rule 1: [Letter]' S  -> [Letter]'S
        line = re.sub(rf"([A-Za-z])\s*({apos})\s+([Ss])(?=\s|$)", r"\1\2\3", line)
        
        # Layer 2: Capital-letter edge cases / Opening apostrophes
        # Rule 2: ' SWORD -> 'SWORD
        # Preceded by start of line or space/dash
        line = re.sub(rf"(^|[\s\-])({apos})\s+([A-Za-z]+)", r"\1\2\3", line)
        
        if line != original_line:
            changes.append((i + 1, original_line.strip(), line.strip()))
        
        new_lines.append(line)
        
    return "\n".join(new_lines), changes

def process_file(filepath):
    """
    Processes a single file: reads, normalises, and asks for confirmation to save.
    """
    file_path = Path(filepath)
    if not file_path.is_file():
        print(f"Skipping {filepath} (not a file).")
        return 'continue'

    print(f"\nProcessing: {filepath}")
    try:
        content = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeError, ValueError) as e:
        print(f"Error reading {filepath}: {e}")
        return 'continue'

    _new_content, changes = normalize_apostrophes(content)

    if not changes:
        print("No changes needed.")
        return 'continue'

    print(f"Found {len(changes)} potential changes in {file_path.name}.")
    
    final_lines = content.splitlines()
    applied_count = 0
    apply_all_in_file = False
    
    for line_num, old, new in changes:
        idx = line_num - 1
        if not apply_all_in_file:
            print(f"\nLine {line_num}:")
            print(f"  - {old}")
            print(f"  + {new}")
            choice = input("Apply this change? [y/n/a/s/q]: ").lower()
            if choice == 'q':
                return 'quit'
            if choice == 's':
                print(f"Skipping remaining changes in {filepath}.")
                break
            if choice == 'a':
                apply_all_in_file = True
            if choice == 'y' or apply_all_in_file:
                # We need to apply the change to the full line, not just the stripped version.
                # Let's re-run the normalisation on this specific line
                final_lines[idx], _ = normalize_apostrophes(final_lines[idx])
                applied_count += 1
        else:
            final_lines[idx], _ = normalize_apostrophes(final_lines[idx])
            applied_count += 1

    if applied_count > 0:
        print(f"\nApplied {applied_count} changes.")
        save = input(f"Save changes to {filepath}? [y/n]: ").lower()
        if save == 'y':
            file_path.write_text("\n".join(final_lines), encoding='utf-8')
            print("File saved.")
        else:
            print("Save cancelled.")
    else:
        print("No changes applied.")
    
    return 'continue'

def main():
    if len(sys.argv) < 2:
        print("Usage: python normalize_apostrophes.py <file_or_folder>")
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Path not found: {path}")
        return

    if path.is_file():
        process_file(path)
    elif path.is_dir():
        files = sorted(f for f in path.iterdir() if f.is_file())
        
        print(f"Found {len(files)} files in folder: {path}")
        for filepath in files:
            result = process_file(filepath)
            if result == 'quit':
                print("Quitting...")
                break
    else:
        print(f"Invalid path type: {path}")

if __name__ == "__main__":
    main()
