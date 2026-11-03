"""Explicit scoring for Cerune stdout + runtime diagnostic predictions.

Semantic normalization is intentionally *narrow*: it only accepts a casing or
underscore/hyphen variation of an already-known runtime error code.
Printed values, order, return status and other characters remain exact.
"""
from __future__ import annotations

import re

KNOWN_CODES = frozenset({
    "integer-overflow",
    "division-by-zero",
    "division-overflow",
    "array-index-out-of-bounds",
    "array-range-out-of-bounds",
    "array-length-out-of-range",
    "allocation-limit-exceeded",
    "allocation-size-overflow",
    "allocation-failed",
})
ERROR = re.compile(r"\AERROR:([a-zA-Z0-9_-]+):(.*)\Z", re.DOTALL)


def normalize_semantic_response(response: str) -> str:
    """Canonicalize only the error-code token, not the printed output.

    In particular, ERROR:INTEGER_OVERFLOW:5 becomes ERROR:integer-overflow:5;
    OK:99,99 is unchanged and still incorrect for an expected OK:20,99.
    """
    raw = response.strip()
    match = ERROR.fullmatch(raw)
    if not match:
        return raw
    code, printed_lines = match.groups()
    normalized = code.lower().replace("_", "-")
    if normalized not in KNOWN_CODES:
        return raw
    return f"ERROR:{normalized}:{printed_lines}"


def compare_prediction(actual: str, expected: str) -> dict[str, bool]:
    actual, expected = actual.strip(), expected.strip()
    return {
        "strict": actual == expected,
        "semantic": normalize_semantic_response(actual)
                    == normalize_semantic_response(expected),
    }
