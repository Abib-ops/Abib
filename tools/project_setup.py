import sys
from pathlib import Path

# This module is used by tools in the tools/ directory to set up sys.path
# and provide common project paths.

# Identify project paths based on this file's location (tools/project_setup.py)
TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_PATH = PROJECT_ROOT / "src"

def setup():
    """Ensure the project root and src are in sys.path."""
    for path in [str(PROJECT_ROOT), str(SRC_PATH)]:
        if path not in sys.path:
            sys.path.insert(0, path)

# Auto-setup on import
setup()
