"""Lightweight response cleanup for eldercare mode.

NOTE: system-info leakage (approval prompts, BLOCKED messages, tool progress,
``<untrusted_tool_result>`` errors) happens entirely in the gateway/system layer
— the gateway renders those events straight to the channel; they never pass
through the model's reply. So they are fixed in the profile config, not here:
approvals.mode="off" stops approval prompts and BLOCKED tool results at the
source, and the Weixin display tier pinned silent stops tool progress / interim
status. This module only does cosmetic cleanup of the model's own spoken reply.
"""

from __future__ import annotations

import re


_TECH_PREFACE_RE = re.compile(
    r"^\s*(?:As an AI language model|I am an AI|作为(?:一个)?AI(?:语言模型)?)[,，：:\s]*",
    re.IGNORECASE,
)


def clean_response(text: str) -> str:
    """Apply conservative cleanup without changing substantive content."""
    if not isinstance(text, str):
        return text
    cleaned = text.strip()
    cleaned = _TECH_PREFACE_RE.sub("", cleaned).strip()
    # Keep Weixin replies quiet: collapse excessive blank lines only.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned
