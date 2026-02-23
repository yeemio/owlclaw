"""Data masking utilities for sensitive text."""

from __future__ import annotations

import re


class DataMasker:
    """Mask sensitive substrings from free-form text."""

    _PATTERNS = (
        # email
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        # phone-like
        re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b"),
        # 16-digit card-like
        re.compile(r"\b(?:\d[ -]?){13,19}\b"),
        # api/token-ish key-value
        re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*([^\s,;]+)"),
    )

    def mask(self, text: str) -> str:
        """Return masked text while preserving rough structure."""
        out = text
        for pattern in self._PATTERNS:
            out = pattern.sub("[REDACTED]", out)
        return out
