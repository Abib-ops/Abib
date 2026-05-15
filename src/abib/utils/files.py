import sys
from pathlib import Path
from json import load
from typing import Any

def readfile(input_filename: str, file_length: int, base_dir: Path | None = None) -> list[int | str]:
    """File reading routine — reads a text file into a list."""
    from abib.core import shared as sh
    _base = base_dir or sh.base_dir
    err = f"File not found: {input_filename}\n"
    output_listname = []
    
    path_to_open = Path(input_filename)
    if not path_to_open.is_absolute() and _base:
        path_to_open = _base / input_filename
            
    try:
        with open(path_to_open, 'r', encoding="utf-8") as f_read:
            for _ in range(file_length):
                line = f_read.readline()
                if not line:
                    break
                stripped = line.splitlines()[0]
                try:
                    i_line = int(stripped)  # Convert to int if possible
                except ValueError:
                    i_line = stripped  # Keep as string if conversion fails
                output_listname.append(i_line)
    except FileNotFoundError:
        print(err)
        sys.exit(1)

    return output_listname

def readio(input_filename: str, file_length: int, base_dir: Path | None = None) -> list[str]:
    """Read Bible files into a list with trailing newlines."""
    from abib.core import shared as sh
    _base = base_dir or sh.base_dir
    output_listname: list = []
    
    path_to_open = Path(input_filename)
    if not path_to_open.is_absolute() and _base:
        path_to_open = _base / input_filename
            
    with open(path_to_open, 'r', encoding="utf-8") as f:
        for _ in range(file_length):
            line = f.readline()
            if not line:
                break
            output_listname.append(f'{line.splitlines()[0]}\n')

    return output_listname

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
    setdict: dict[Any, set] = {}
    listdict: Any = load_json_dict(input_filename, base_dir)
    sd: list = list(ref_dict)
    for key in sd:
        setdict[key] = set(listdict[key])

    return setdict
