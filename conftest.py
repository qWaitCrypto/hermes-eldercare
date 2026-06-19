"""Pytest collection config.

The repo root ``__init__.py`` is the Hermes directory-plugin entrypoint, not a
test module. Skip it during collection so pytest never treats the repo root as a
test package and tries to import it as one.
"""

collect_ignore = ["__init__.py"]
