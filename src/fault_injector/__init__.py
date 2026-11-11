"""Inject faults into outbound calls in tests.

Wrap sync or async callables with rules that raise, delay through an injected
sleep, or return canned values, on deterministic triggers such as call counts
or a seeded probability.
"""

from .errors import FaultError
from .faults import Delay, Raise, Return
from .plan import FaultPlan, Injection
from .rules import Rule

__version__ = "0.1.0"

__all__ = [
    "Delay",
    "FaultError",
    "FaultPlan",
    "Injection",
    "Raise",
    "Return",
    "Rule",
]
