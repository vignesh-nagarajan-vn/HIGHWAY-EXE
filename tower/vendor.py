"""Import the organisers' enterprise module (unmodified) from vendor/.

We reuse it for the calendar helpers and, in verify/twin.py, as an in-process digital twin
that dry-runs every plan before a single real call is made.
"""
from __future__ import annotations

import importlib.util
import sys

from .config import PACKAGE_DIR


def _load():
    name = "hth_enterprise"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PACKAGE_DIR / "enterprise.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


enterprise = _load()
TOOLS = enterprise.TOOLS
WRITE_TOOLS = enterprise.WRITE_TOOLS
Enterprise = enterprise.Enterprise
ToolError = enterprise.ToolError
