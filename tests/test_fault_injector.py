"""Public-surface and validation tests for fault_injector."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

import fault_injector
from fault_injector import Delay, FaultError, FaultPlan, Injection, Raise, Return, Rule


def _double(x: int) -> int:
    return x * 2


class _Holder:
    def __init__(self) -> None:
        self.charge = _double


def test_public_api_exports() -> None:
    for name in ("FaultError", "Raise", "Delay", "Return", "Rule", "FaultPlan", "Injection"):
        assert name in fault_injector.__all__
        assert getattr(fault_injector, name) is not None


def test_version_is_semver() -> None:
    parts = fault_injector.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_fault_error_carries_code_and_short_message() -> None:
    error = FaultError("invalid_rule")
    assert error.code == "invalid_rule"
    assert str(error) == "invalid_rule"
    assert len(str(error)) <= 200


def test_plan_logger_has_null_handler() -> None:
    logger = logging.getLogger("fault_injector.plan")
    assert any(isinstance(handler, logging.NullHandler) for handler in logger.handlers)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"first": 0},
        {"every": 0},
        {"max_injections": 0},
        {"probability": -0.1},
        {"probability": 1.5},
        {"on_calls": {1}},
        {"on_calls": frozenset({0})},
    ],
)
def test_invalid_rule_triggers(kwargs: dict[str, Any]) -> None:
    with pytest.raises(FaultError) as exc_info:
        Rule("target", Raise(lambda: RuntimeError()), **kwargs)
    assert exc_info.value.code == "invalid_rule"


@pytest.mark.parametrize("seconds", [-1.0, float("inf"), float("nan")])
def test_delay_validates_seconds(seconds: float) -> None:
    with pytest.raises(FaultError) as exc_info:
        Delay(seconds)
    assert exc_info.value.code == "invalid_rule"


def test_target_length_validation() -> None:
    with pytest.raises(FaultError) as exc_info:
        Rule("x" * 201, Raise(lambda: RuntimeError()))
    assert exc_info.value.code == "invalid_target"

    plan = FaultPlan([])
    with pytest.raises(FaultError) as exc_info:
        plan.wrap(_double, "")
    assert exc_info.value.code == "invalid_target"


def test_rule_count_limit() -> None:
    rules = [Rule(f"t{i}", Raise(lambda: RuntimeError())) for i in range(100)]
    plan = FaultPlan(rules)
    assert plan.history == []
    with pytest.raises(FaultError) as exc_info:
        FaultPlan([*rules, Rule("extra", Raise(lambda: RuntimeError()))])
    assert exc_info.value.code == "too_many_rules"


def test_on_calls_trigger() -> None:
    plan = FaultPlan([Rule("x", Raise(lambda: RuntimeError()), on_calls=frozenset({2}))])
    wrapped = plan.wrap(_double, "x")

    assert wrapped(1) == 2
    with pytest.raises(RuntimeError):
        wrapped(2)
    assert wrapped(3) == 6
    assert plan.history == [Injection("x", 2, "raise")]


def test_patch_restores_attribute_when_body_raises() -> None:
    holder = _Holder()
    original = holder.charge
    plan = FaultPlan([Rule("payments.charge", Raise(lambda: RuntimeError()), first=1)])

    with (
        pytest.raises(ValueError, match="boom"),
        plan.patch(holder, "charge", "payments.charge"),
    ):
        raise ValueError("boom")

    assert holder.charge is original


def test_async_raise_return_and_passthrough() -> None:
    async def real(x: int) -> int:
        return x + 1

    raiser = FaultPlan([Rule("svc", Raise(lambda: ConnectionError()), first=1)])
    raised = raiser.wrap(real, "svc")

    async def run_raise() -> None:
        with pytest.raises(ConnectionError):
            await raised(1)
        assert await raised(2) == 3

    asyncio.run(run_raise())

    returner = FaultPlan([Rule("svc", Return(None), first=1)])
    returned = returner.wrap(real, "svc")
    assert asyncio.run(returned(1)) is None
    assert asyncio.run(returned(2)) == 3


def test_async_delay_then_raise() -> None:
    async_sleep_calls: list[float] = []

    async def fake_async_sleep(seconds: float) -> None:
        async_sleep_calls.append(seconds)

    async def real(x: int) -> int:
        return x

    plan = FaultPlan(
        [Rule("x", Delay(1.5, then=Raise(lambda: ValueError("late"))))],
        async_sleep=fake_async_sleep,
    )
    wrapped = plan.wrap(real, "x")

    async def run() -> None:
        with pytest.raises(ValueError):
            await wrapped(1)

    asyncio.run(run())
    assert async_sleep_calls == [1.5]
    assert plan.history == [Injection("x", 1, "delay")]
