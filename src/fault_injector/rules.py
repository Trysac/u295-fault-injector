"""Rule definition and validation."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import FaultError
from .faults import Fault

MAX_TARGET_LENGTH = 200


@dataclass(frozen=True)
class Rule:
    """A fault injection rule.

    Args:
        target: fnmatch pattern to match against call targets.
        fault: The fault to inject when the rule fires.
        first: Fire only if the call number is <= ``first`` (1-based).
        every: Fire only if the call number is divisible by ``every``.
        on_calls: Fire only if the call number is in this set.
        probability: Fire with this probability, drawn once per matching call.
        max_injections: Maximum number of times this rule can fire.
    """

    target: str
    fault: Fault
    first: int | None = None
    every: int | None = None
    on_calls: frozenset[int] | None = None
    probability: float | None = None
    max_injections: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.target, str) or not 1 <= len(self.target) <= MAX_TARGET_LENGTH:
            raise FaultError("invalid_target")

        for value in (self.first, self.every, self.max_injections):
            if value is not None and (not isinstance(value, int) or value < 1):
                raise FaultError("invalid_rule")

        if self.probability is not None and not (
            isinstance(self.probability, (int, float)) and 0.0 <= self.probability <= 1.0
        ):
            raise FaultError("invalid_rule")

        if self.on_calls is not None and (
            not isinstance(self.on_calls, frozenset)
            or not all(isinstance(c, int) and c >= 1 for c in self.on_calls)
        ):
            raise FaultError("invalid_rule")
