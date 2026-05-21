"""Test configuration.

Adds the ``src/`` directory to ``sys.path`` so that test modules can import
the package modules directly (``from etl.transform_clean import ...``).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
