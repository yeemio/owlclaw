"""MemorySystem — short-term memory manager for current Agent run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _ShortTermEntry:
    role: str
    content: str


class MemorySystem:
    """Manage short-term run context with token budget and auto-compression."""

    def __init__(self, short_term_token_limit: int = 2000) -> None:
        if not isinstance(short_term_token_limit, int) or short_term_token_limit < 1:
            raise ValueError("short_term_token_limit must be a positive integer")
        self.short_term_token_limit = short_term_token_limit
        self._short_term_entries: list[_ShortTermEntry] = []

    def add_short_term(self, role: str, content: str) -> None:
        """Append a short-term memory entry for this run."""
        normalized_role = (role or "").strip()
        normalized_content = (content or "").strip()
        if not normalized_role:
            raise ValueError("role must be a non-empty string")
        if not normalized_content:
            raise ValueError("content must be a non-empty string")
        self._short_term_entries.append(
            _ShortTermEntry(role=normalized_role, content=normalized_content)
        )

    def build_short_term_context(self) -> str:
        """Build compressed short-term context constrained by token limit."""
        if not self._short_term_entries:
            return ""

        lines = [f"{entry.role}: {entry.content}" for entry in self._short_term_entries]
        compressed_lines, removed = self._compress_to_limit(lines)
        if removed > 0:
            compressed_lines.insert(0, f"[compressed {removed} earlier entries]")
        return "\n".join(compressed_lines).strip()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens with a lightweight heuristic suitable for tests/runtime guardrails."""
        if not text or not text.strip():
            return 0
        return len(text.split())

    def _compress_to_limit(self, lines: list[str]) -> tuple[list[str], int]:
        """Keep newest entries within token budget; return (kept_lines, removed_count)."""
        if self.estimate_tokens("\n".join(lines)) <= self.short_term_token_limit:
            return lines, 0

        kept: list[str] = []
        total_tokens = 0
        for line in reversed(lines):
            line_tokens = self.estimate_tokens(line)
            if total_tokens + line_tokens > self.short_term_token_limit:
                continue
            kept.append(line)
            total_tokens += line_tokens
        kept.reverse()

        if not kept:
            # Extremely small limit: keep tail line truncated to fit.
            tail = lines[-1]
            words = tail.split()
            kept = [" ".join(words[: self.short_term_token_limit])]
        removed = max(0, len(lines) - len(kept))
        return kept, removed
