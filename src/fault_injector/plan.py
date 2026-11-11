"""Fault injection plan and execution."""

from __future__ import annotations

import asyncio
import fnmatch
import functools
import inspect
import logging
import random
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, cast

from .errors import FaultError
from .faults import Fault, Raise, Return
from .rules import Rule

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

T = TypeVar("T")

FaultKind = Literal["raise", "delay", "return"]

MAX_RULES = 100
MAX_TARGET_LENGTH = 200

# Deterministic, seeded triggering needs a pseudorandom generator, which is
# exactly what ``random`` provides; keeping the class in an alias documents
# that the use is intentional and not a security decision.
_PseudoRandom = random.Random


@dataclass(frozen=True)
class Injection:
    """Record of a fault that was injected."""

    target: str
    call: int
    kind: FaultKind


class FaultPlan:
    """Coordinates fault injection for a set of wrapped targets."""

    def __init__(
        self,
        rules: Sequence[Rule],
        *,
        seed: int = 0,
        sleep: Callable[[float], None] = time.sleep,
        async_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        max_history: int = 10_000,
        on_event: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        if len(rules) > MAX_RULES:
            raise FaultError("too_many_rules")

        self._rules: list[Rule] = list(rules)
        self._seed = seed
        self._rng = _PseudoRandom(seed)
        self._sleep = sleep
        self._async_sleep = async_sleep
        self._max_history = max_history
        self._on_event = on_event

        self._lock = threading.Lock()
        self._enabled = True

        # Per-target call counters: target -> current call number (1-based).
        self._call_counts: dict[str, int] = {}
        # Per-rule injection counters: index -> number of times the rule has fired.
        self._rule_injection_counts: list[int] = [0] * len(self._rules)

        self._history: deque[Injection] = deque(maxlen=max_history)
        self._dropped = 0

    @property
    def history(self) -> list[Injection]:
        """Return a copy of the injection history."""
        with self._lock:
            return list(self._history)

    @property
    def dropped(self) -> int:
        """Number of injections dropped due to history overflow."""
        with self._lock:
            return self._dropped

    def enable(self) -> None:
        """Enable fault injection (default)."""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """Disable fault injection; all wrapped calls pass through."""
        with self._lock:
            self._enabled = False

    def reset(self) -> None:
        """Reset all state: counters, history, dropped, and reseed the RNG."""
        with self._lock:
            self._call_counts.clear()
            self._rule_injection_counts = [0] * len(self._rules)
            self._history.clear()
            self._dropped = 0
            self._rng.seed(self._seed)

    def wrap(self, fn: Callable[..., T], target: str) -> Callable[..., T]:
        """Wrap a callable so that faults can be injected.

        Args:
            fn: The function to wrap (sync or async).
            target: The target name to match against rule patterns.
        """
        _validate_target(target)
        if inspect.iscoroutinefunction(fn):
            return cast(Callable[..., T], self._wrap_async(fn, target))
        return self._wrap_sync(fn, target)

    def _wrap_sync(self, fn: Callable[..., T], target: str) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            fault = self._begin_call(target)
            if fault is None:
                return fn(*args, **kwargs)
            return self._apply_fault_sync(fault, fn, args, kwargs)

        return wrapper

    def _wrap_async(self, fn: Callable[..., Any], target: str) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            fault = self._begin_call(target)
            if fault is None:
                return await fn(*args, **kwargs)
            return await self._apply_fault_async(fault, fn, args, kwargs)

        return wrapper

    def _begin_call(self, target: str) -> Fault | None:
        """Count the call and return the fault to apply, if a rule fires.

        The lock is released before the wrapped function or the injected sleep
        runs, so a wrapped callable may call another wrapped target of the same
        plan (and async callables never hold the lock across an ``await``).
        """
        fault: Fault | None = None
        event: dict[str, object] | None = None
        with self._lock:
            call_number = self._call_counts.get(target, 0) + 1
            self._call_counts[target] = call_number
            if self._enabled:
                rule_index = self._find_matching_rule(target, call_number)
                if rule_index is not None:
                    rule = self._rules[rule_index]
                    kind = self._fault_kind(rule.fault)
                    self._rule_injection_counts[rule_index] += 1
                    self._record_injection(target, call_number, kind)
                    fault = rule.fault
                    event = {
                        "event": "fault_injected",
                        "target": target,
                        "call": call_number,
                        "kind": kind,
                    }
        if event is not None:
            handler = self._on_event
            if handler is not None:
                handler(event)
        return fault

    def _find_matching_rule(self, target: str, call_number: int) -> int | None:
        """Return the index of the first matching rule that should fire, or None."""
        for idx, rule in enumerate(self._rules):
            if not fnmatch.fnmatchcase(target, rule.target):
                continue

            # The probability is drawn once per call for every matching
            # probabilistic rule, before the other triggers are evaluated.
            if rule.probability is not None and self._rng.random() >= rule.probability:
                continue

            if rule.first is not None and call_number > rule.first:
                continue
            if rule.every is not None and call_number % rule.every != 0:
                continue
            if rule.on_calls is not None and call_number not in rule.on_calls:
                continue
            if (
                rule.max_injections is not None
                and self._rule_injection_counts[idx] >= rule.max_injections
            ):
                continue

            return idx
        return None

    def _record_injection(self, target: str, call_number: int, kind: FaultKind) -> None:
        if len(self._history) >= self._max_history:
            self._dropped += 1
        self._history.append(Injection(target, call_number, kind))
        logger.debug("injected %s into %s on call %d", kind, target, call_number)

    @staticmethod
    def _fault_kind(fault: Fault) -> FaultKind:
        if isinstance(fault, Raise):
            return "raise"
        if isinstance(fault, Return):
            return "return"
        return "delay"

    def _apply_fault_sync(
        self,
        fault: Fault,
        fn: Callable[..., T],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> T:
        if isinstance(fault, Raise):
            raise fault.factory()
        if isinstance(fault, Return):
            return cast(T, fault.value)
        self._sleep(fault.seconds)
        if fault.then is not None:
            return self._apply_fault_sync(fault.then, fn, args, kwargs)
        return fn(*args, **kwargs)

    async def _apply_fault_async(
        self,
        fault: Fault,
        fn: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        if isinstance(fault, Raise):
            raise fault.factory()
        if isinstance(fault, Return):
            return fault.value
        await self._async_sleep(fault.seconds)
        if fault.then is not None:
            return await self._apply_fault_async(fault.then, fn, args, kwargs)
        return await fn(*args, **kwargs)

    @contextmanager
    def patch(self, obj: Any, attr: str, target: str) -> Iterator[None]:
        """Temporarily replace an object's attribute with a wrapped version."""
        original = getattr(obj, attr)
        setattr(obj, attr, self.wrap(original, target))
        try:
            yield
        finally:
            setattr(obj, attr, original)


def _validate_target(target: str) -> None:
    """Reject target names that are not 1-200 character strings."""
    if not isinstance(target, str) or not 1 <= len(target) <= MAX_TARGET_LENGTH:
        raise FaultError("invalid_target")
