"""Hermes directory-plugin entrypoint for hermes-eldercare.

This is only used when Hermes loads the repository as a directory plugin.
Pip installs use the ``hermes_agent.plugins`` entry point instead.

``hermes plugins install`` only ``git clone``s the repo; it does not run
``pip install``. So the ``hermes_eldercare`` package is not guaranteed to be on
``sys.path`` when this entrypoint runs. We add this repo directory to
``sys.path`` (if needed) and import the package normally, so the package's own
relative imports keep working. Importing lazily inside ``register`` also keeps
this module's top level import-free, so test runners / loaders that import this
file as a plain top-level module never trip over a package-relative import.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = str(Path(__file__).resolve().parent)


def register(ctx: Any) -> None:
    """Register eldercare hooks/CLI, importing the package self-sufficiently."""
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    from hermes_eldercare.plugin import register as _register

    _register(ctx)


__all__ = ["register"]
