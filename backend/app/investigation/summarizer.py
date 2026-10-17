"""Bounded Log Summarizer for Sherlog incident investigations.

Normalizes raw, noisy log streams into bounded structured summaries:
- Deduplicates repetitive log lines and error patterns
- Replaces dynamic variables (timestamps, UUIDs, memory addresses, IPs) with tokens
- Aggregates frequency counts (e.g. "[18x] QueuePool limit reached")
- Neutralizes prompt-injection keywords in logs
- Bounds output size to prevent token budget flooding
"""

import re
from typing import Dict, List, Optional


# Patterns to normalize dynamic values in log messages
_NORMALIZATION_PATTERNS = [
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX_ADDR>"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b"), "<IP>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b"), "<TIMESTAMP>"),
    (re.compile(r"\b(?:[A-Za-z0-9_-]+\.)+[A-Za-z]{2,}(?::\d+)?\b"), "<HOST>"),
]

# Prompt injection neutralization
_INJECTION_KEYWORDS = [
    re.compile(r"(?i)\bignore\s+(?:all\s+)?previous\s+instructions\b"),
    re.compile(r"(?i)\byou\s+are\s+now\s+a\b"),
    re.compile(r"(?i)\bsystem\s*:\s*"),
    re.compile(r"(?i)\bassistant\s*:\s*"),
    re.compile(r"(?i)\buser\s*:\s*"),
    re.compile(r"(?i)<\/?(?:system|instruction|prompt)[^>]*>"),
]


def sanitize_log_text(text: str) -> str:
    """Neutralize potential prompt-injection strings inside log text."""
    clean = text
    for pattern in _INJECTION_KEYWORDS:
        clean = pattern.sub("[FILTERED_INJECTION_ATTEMPT]", clean)
    return clean


def normalize_log_line(line: str) -> str:
    """Normalize dynamic parameters in a log line to enable clustering."""
    normalized = sanitize_log_text(line.strip())
    for pattern, replacement in _NORMALIZATION_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def summarize_logs(
    raw_lines: List[str],
    max_summary_chars: int = 800,
    max_patterns: int = 5,
) -> str:
    """Aggregate, deduplicate, and summarize a collection of raw log lines.

    Args:
        raw_lines: List of raw log strings from Loki or container logs.
        max_summary_chars: Strict character bound for the output summary.
        max_patterns: Maximum number of distinct signature clusters to return.

    Returns:
        Bounded string containing frequency-counted log signatures.
    """
    if not raw_lines:
        return "No error logs observed."

    pattern_counts: Dict[str, int] = {}
    pattern_examples: Dict[str, str] = {}

    for raw in raw_lines:
        if not raw or not raw.strip():
            continue
        norm = normalize_log_line(raw)
        # Bounded signature key
        sig = norm[:120]
        pattern_counts[sig] = pattern_counts.get(sig, 0) + 1
        if sig not in pattern_examples:
            pattern_examples[sig] = raw.strip()[:150]

    # Sort signatures by frequency descending
    sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)

    summary_items: List[str] = []
    total_chars = 0

    for sig, count in sorted_patterns[:max_patterns]:
        example = pattern_examples.get(sig, sig)
        # Neutralize any injection in the example text
        safe_example = sanitize_log_text(example)
        entry = f"[{count}x] {safe_example}"
        if total_chars + len(entry) + 1 > max_summary_chars:
            break
        summary_items.append(entry)
        total_chars += len(entry) + 1

    if not summary_items:
        return "Log patterns extracted, exceeded boundary."

    return "\n".join(summary_items)
