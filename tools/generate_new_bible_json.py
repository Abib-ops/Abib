import json

from bible_common import CANONICAL_BOOKS, parse_pce_text
from project_setup import SRC_PATH


def main():
    data_dir = SRC_PATH / "abib" / "data"
    json_path = data_dir / "bible_data.json"
    output_path = data_dir / "bible_data_new.json"
    
    txt_path_kjb = data_dir / "KJB_PCE.txt"
    txt_path_kjv = data_dir / "KJV_PCE.txt"
    txt_path = txt_path_kjv if txt_path_kjv.exists() else txt_path_kjb

    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
    if not txt_path.exists():
        print(f"Error: {txt_path} not found")
        return
        
    print(f"Loading {json_path.name}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        bible_data = json.load(f)
        
    print(f"Parsing {txt_path.name}...")
    pce_data = parse_pce_text(txt_path)
    
    print("Preferring PCE verses...")
    update_count = 0
    missing_count = 0
    
    # We iterate over the existing JSON structure to preserve its keys and order
    for book in CANONICAL_BOOKS:
        if book not in bible_data:
            continue
            
        for chap_num, verses in bible_data[book].items():
            for verse_num, json_text in verses.items():
                key = (book, chap_num, verse_num)
                if key in pce_data:
                    pce_text = pce_data[key]
                    if json_text != pce_text:
                        bible_data[book][chap_num][verse_num] = pce_text
                        update_count += 1
                else:
                    missing_count += 1

    print(f"Updated {update_count} verses.")
    if missing_count > 0:
        print(f"Note: {missing_count} verses were not found in PCE and kept original.")
        
    print(f"Saving to {output_path.name}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        # Use indent=4 to match standard JSON formatting
        json.dump(bible_data, f, indent=4, ensure_ascii=False)
        
    print("Successfully created bible_data_new.json")

if __name__ == "__main__":
    main()
