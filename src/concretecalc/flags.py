"""Structured calculation warnings; no display or logging side effects."""
from dataclasses import dataclass
from typing import Literal

from concretecalc.tables.models import Lookup, Status

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class Flag:
    """Stable machine-readable code with severity and human-readable explanation."""
    code: str
    severity: Severity
    message: str


def flags_from_lookup(lookup: Lookup, code: str) -> tuple[Flag, ...]:
    """Preserve table warning texts, marking unavailable values as errors."""
    severity: Severity = "info"
    if lookup.status == Status.UNAVAILABLE:
        severity = "error"
    elif lookup.status in (Status.CLAMPED, Status.EXTRAPOLATED):
        severity = "warning"
    return tuple(Flag(code, severity, message) for message in lookup.warnings)


def count_by_severity(flags: tuple[Flag, ...]) -> dict[str, int]:
    """Count flags including zero counts, without modifying their order."""
    counts = {"info": 0, "warning": 0, "error": 0}
    for flag in flags:
        counts[flag.severity] += 1
    return counts
