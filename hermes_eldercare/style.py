"""Lightweight response cleanup for eldercare mode."""

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
