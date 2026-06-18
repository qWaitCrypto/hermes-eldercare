"""Hermes directory-plugin entrypoint for hermes-eldercare.

This is only used when Hermes loads the repository as a directory plugin.
Pip installs use the ``hermes_agent.plugins`` entry point instead.
"""

from hermes_eldercare.plugin import register

__all__ = ["register"]
