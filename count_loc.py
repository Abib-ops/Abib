#!/usr/bin/env python3
"""
Count lines of code in this project.

- Counts only first-party source files (default: .py)
- Excludes virtual environment folders and other common third-party directories
- Prints a single integer: the total line count

Usage:
    python count_loc.py            # count .py files
    python count_loc.py .py .ui    # include more extensions if desired
"""
from __future__ import annotations

import sys
from pathlib import Path

# Root is the directory containing this script
ROOT = Path(__file__).resolve().parent

# Directories to ignore (relative to ROOT)
EXCLUDE_DIRS = {
    'venv', 'venv_3_13', 'venv_3_14_0',
    '.git', '__pycache__', '.idea', '.pytest_cache', 'build', 'dist'
}

# File extensions considered as code
DEFAULT_EXTS = {'.py'}


def iter_code_files(root: Path, exts: set[str]) -> list[Path]:
    files: list[Path] = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            for p in d.iterdir():
                name = p.name
                if p.is_dir():
                    if name in EXCLUDE_DIRS:
                        continue
                    stack.append(p)
                else:
                    if p.suffix in exts:
                        files.append(p)
        except (OSError, PermissionError):
            # Skip unreadable paths
            continue
    return files


def count_lines(paths: list[Path]) -> int:
    total = 0
    for p in paths:
        try:
            with p.open('r', encoding='utf-8', errors='ignore') as f:
                for _ in f:
                    total += 1
        except OSError:
            continue
    return total


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        exts = {e if e.startswith('.') else f'.{e}' for e in argv[1:]}
    else:
        exts = set(DEFAULT_EXTS)

    files = iter_code_files(ROOT, exts)
    total = count_lines(files)
    print(total)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
