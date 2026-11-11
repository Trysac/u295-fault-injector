"""Error types for the fault injector."""

from __future__ import annotations

from typing import Literal

ErrorCode = Literal["invalid_rule", "invalid_target", "too_many_rules"]


class FaultError(Exception):
    """Error raised for an invalid fault injection configuration."""

    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code)
