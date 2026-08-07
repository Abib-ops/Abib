import sys
from json import load
from pathlib import Path
from typing import Any


def readfile(input_filename: str, file_length: int, base_dir: Path | None = None) -> list[int | str]:
    """File reading routine — reads a text file into a list."""
    from abib.core import shared as sh
    _base = base_dir or sh.base_dir
    err = f"File not found: {input_filename}\n"
    
    path_to_open = Path(input_filename)
    if not path_to_open.is_absolute() and _base:
        path_to_open = _base / input_filename
            
    try:
        with open(path_to_open, 'r', encoding="utf-8") as f_read:
            # Bulk read all lines and slice to the required length
            lines = f_read.read().splitlines()[:file_length]
            output_listname = []
            for line in lines:
                # Faster than try-except for non-numeric strings
                if line.isdigit() or (line.startswith('-') and line[1:].isdigit()):
                    output_listname.append(int(line))
                else:
                    output_listname.append(line)
    except FileNotFoundError:
        print(err)
        sys.exit(1)

    return output_listname

def readio(input_filename: str, file_length: int, base_dir: Path | None = None) -> list[str]:
    """Read Bible files into a list with trailing newlines."""
    from abib.core import shared as sh
    _base = base_dir or sh.base_dir
    
    path_to_open = Path(input_filename)
    if not path_to_open.is_absolute() and _base:
        path_to_open = _base / input_filename
            
    with open(path_to_open, 'r', encoding="utf-8") as f:
        # Bulk read all lines and slice to the required length
        lines = f.read().splitlines()[:file_length]
        # Re-add newlines if the rest of the app expects them (as per current code)
        return [f"{line}\n" for line in lines]

def load_json_dict(file_dict_path: Any, base_dir: Path | None = None) -> Any:
    """Load a dictionary with JSON."""
    from abib.core import shared as sh
    _base = base_dir or sh.base_dir
    path_to_open = Path(file_dict_path)
    if not path_to_open.is_absolute() and _base:
        path_to_open = _base / file_dict_path

    with open(path_to_open, "r", encoding='utf-8') as read_file:
        return load(read_file)

def load_list_set_dict(input_filename: str, ref_dict: Any, base_dir: Path | None = None) -> dict[Any, set]:
    """Load a list_dict.txt/json file that is a dictionary of Bible words."""
    listdict: Any = load_json_dict(input_filename, base_dir)
    # Use dictionary comprehension for better performance and convert lists to sets
    if ref_dict is None:
        return {key: set(val) for key, val in listdict.items()}
    return {key: set(listdict[key]) for key in ref_dict}
