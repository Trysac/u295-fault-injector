"""Fault types that can be applied when a rule matches."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from .errors import FaultError


@dataclass(frozen=True)
class Raise:
    """Raise a new exception instance when injected."""

    factory: Callable[[], BaseException]


@dataclass(frozen=True)
class Return:
    """Return a fixed value instead of calling the wrapped function."""

    value: object


@dataclass(frozen=True)
class Delay:
    """Sleep for a given duration, then call through or apply another fault."""

    seconds: float
    then: Raise | Return | Delay | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.seconds, (int, float))
            or not math.isfinite(self.seconds)
            or self.seconds < 0
        ):
            raise FaultError("invalid_rule")


Fault = Raise | Return | Delay
