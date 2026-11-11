"""Tests for the FaultPlan class and fault injection semantics."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from fault_injector import Delay, FaultError, FaultPlan, Injection, Raise, Return, Rule

# Helper functions


def _real_fn(x: int) -> int:
    return x * 2


async def _real_async_fn(x: int) -> int:
    return x + 1


class _Module:
    def __init__(self) -> None:
        self.charge = _real_fn


# ----- Acceptance tests from the specification -----


def test_first_two_calls_raise_then_pass() -> None:
    """The criterion: the first two calls raise TimeoutError, the third returns charge's result, and plan.history == [Injection('payments.charge', 1, 'raise'), Injection('payments.charge', 2, 'raise')]."""
    plan = FaultPlan([Rule("payments.charge", Raise(lambda: TimeoutError("injected")), first=2)])
    wrapped = plan.wrap(_real_fn, "payments.charge")

    with pytest.raises(TimeoutError):
        wrapped(5)
    with pytest.raises(TimeoutError):
        wrapped(6)
    assert wrapped(7) == 14

    assert plan.history == [
        Injection("payments.charge", 1, "raise"),
        Injection("payments.charge", 2, "raise"),
    ]


def test_every_third_call_raises() -> None:
    plan = FaultPlan([Rule("db.query", Raise(lambda: ConnectionError()), every=3)])
    wrapped = plan.wrap(_real_fn, "db.query")

    results: list[Any] = []
    for i in range(1, 8):
        try:
            results.append(wrapped(i))
        except ConnectionError:
            results.append("raised")

    assert results == [2, 4, "raised", 8, 10, "raised", 14]
    assert plan.history == [
        Injection("db.query", 3, "raise"),
        Injection("db.query", 6, "raise"),
    ]


def test_delay_records_sleep_and_returns_real_result() -> None:
    sleep_calls: list[float] = []
    plan = FaultPlan([Rule("api.get", Delay(2.5))], sleep=lambda s: sleep_calls.append(s))
    wrapped = plan.wrap(_real_fn, "api.get")

    result = wrapped(4)
    assert result == 8
    assert sleep_calls == [2.5]
    assert plan.history == [Injection("api.get", 1, "delay")]


def test_async_delay_awaits_injected_async_sleep() -> None:
    async_sleep_calls: list[float] = []

    async def fake_async_sleep(seconds: float) -> None:
        async_sleep_calls.append(seconds)

    plan = FaultPlan(
        [Rule("api.get", Delay(2.5))],
        async_sleep=fake_async_sleep,
    )
    wrapped = plan.wrap(_real_async_fn, "api.get")

    async def run() -> None:
        result = await wrapped(5)
        assert result == 6

    asyncio.run(run())
    assert async_sleep_calls == [2.5]
    assert plan.history == [Injection("api.get", 1, "delay")]


def test_probability_with_seed_matches_specified_calls() -> None:
    plan = FaultPlan(
        [Rule("api.get", Raise(lambda: ConnectionError()), probability=0.5)],
        seed=1,
    )
    wrapped = plan.wrap(_real_fn, "api.get")

    results: list[Any] = []
    for i in range(1, 11):
        try:
            results.append(wrapped(i))
        except ConnectionError:
            results.append("raised")

    # Expected failures: calls 1, 4, 5, 6, 9, 10
    expected_raised = {1, 4, 5, 6, 9, 10}
    raised_calls = [i for i, r in zip(range(1, 11), results, strict=True) if r == "raised"]
    assert raised_calls == sorted(expected_raised)
    assert len(plan.history) == len(expected_raised)


def test_return_value_skips_function_call() -> None:
    call_counts: dict[str, int] = {"real": 0}

    def tracking_fn(x: int) -> int:
        call_counts["real"] += 1
        return x

    plan = FaultPlan([Rule("cache.get", Return(None))])
    wrapped = plan.wrap(tracking_fn, "cache.get")

    result = wrapped(10)
    assert result is None
    assert call_counts["real"] == 0
    assert plan.history == [Injection("cache.get", 1, "return")]


def test_pattern_matching_and_max_injections() -> None:
    plan = FaultPlan(
        [
            Rule("payments.*", Raise(lambda: ValueError()), max_injections=1),
        ]
    )
    wrapped_refund = plan.wrap(_real_fn, "payments.refund")
    wrapped_charge = plan.wrap(_real_fn, "payments.charge")
    wrapped_parent = plan.wrap(_real_fn, "payments")

    with pytest.raises(ValueError):
        wrapped_refund(2)  # first fire
    assert wrapped_refund(3) == 6  # second call, max reached, passes through
    assert wrapped_charge(4) == 8  # matches the pattern, but max_injections is used up
    # 'payments.*' requires the literal dot, so the parent target never matches.
    assert wrapped_parent(5) == 10
    assert plan.history == [Injection("payments.refund", 1, "raise")]


def test_validation_errors() -> None:
    with pytest.raises(FaultError) as exc_info:
        Rule("x", Raise(lambda: Exception()), probability=1.5)
    assert exc_info.value.code == "invalid_rule"

    with pytest.raises(FaultError) as exc_info:
        Rule("", Raise(lambda: Exception()))
    assert exc_info.value.code == "invalid_target"

    with pytest.raises(FaultError) as exc_info:
        FaultPlan([Rule("x", Raise(lambda: Exception()))] * 101)
    assert exc_info.value.code == "too_many_rules"


def test_patch_context_manager_restores_original() -> None:
    module = _Module()
    original_fn = module.charge
    plan = FaultPlan([Rule("payments.charge", Raise(lambda: RuntimeError()), first=1)])

    with plan.patch(module, "charge", "payments.charge"):
        assert module.charge is not original_fn
        with pytest.raises(RuntimeError):
            module.charge(1)

    assert module.charge is original_fn
    assert module.charge(2) == 4  # restored works


def test_disable_makes_all_calls_pass_through() -> None:
    plan = FaultPlan([Rule("x", Raise(lambda: RuntimeError()))])
    wrapped = plan.wrap(_real_fn, "x")

    with pytest.raises(RuntimeError):
        wrapped(1)

    plan.disable()
    assert wrapped(2) == 4
    plan.enable()
    with pytest.raises(RuntimeError):
        wrapped(3)


def test_history_bounded_and_dropped_count() -> None:
    plan = FaultPlan(
        [Rule("x", Raise(lambda: RuntimeError()))],
        max_history=3,
    )
    wrapped = plan.wrap(_real_fn, "x")

    for i in range(5):
        with pytest.raises(RuntimeError):
            wrapped(i)

    assert len(plan.history) == 3
    assert plan.dropped == 2
    assert plan.history == [
        Injection("x", 3, "raise"),
        Injection("x", 4, "raise"),
        Injection("x", 5, "raise"),
    ]


def test_on_event_callback_receives_correct_payload() -> None:
    events: list[dict[str, object]] = []
    plan = FaultPlan(
        [Rule("payments.charge", Raise(lambda: TimeoutError()), first=1)],
        on_event=events.append,
    )
    wrapped = plan.wrap(_real_fn, "payments.charge")

    with pytest.raises(TimeoutError):
        wrapped(1)

    assert len(events) == 1
    assert events[0] == {
        "event": "fault_injected",
        "target": "payments.charge",
        "call": 1,
        "kind": "raise",
    }


def test_delay_then_raise() -> None:
    sleep_calls: list[float] = []
    plan = FaultPlan(
        [Rule("x", Delay(0.5, then=Raise(lambda: ValueError("late"))))],
        sleep=lambda s: sleep_calls.append(s),
    )
    wrapped = plan.wrap(_real_fn, "x")

    with pytest.raises(ValueError):
        wrapped(1)

    assert sleep_calls == [0.5]
    assert plan.history == [Injection("x", 1, "delay")]


def test_two_rules_first_does_not_fire_second_does() -> None:
    plan = FaultPlan(
        [
            Rule("target", Raise(lambda: RuntimeError()), every=3),
            Rule("target", Raise(lambda: ValueError()), first=1),
        ]
    )
    wrapped = plan.wrap(_real_fn, "target")

    with pytest.raises(ValueError):
        wrapped(1)  # first rule: call 1 not every 3 -> skip; second: first=1 -> fire


def test_reset_reproduces_probabilistic_sequence() -> None:
    plan = FaultPlan(
        [Rule("x", Raise(lambda: ConnectionError()), probability=0.5)],
        seed=42,
    )
    wrapped = plan.wrap(_real_fn, "x")

    seq1 = []
    for i in range(10):
        try:
            wrapped(i)
            seq1.append(False)
        except ConnectionError:
            seq1.append(True)

    plan.reset()
    seq2 = []
    for i in range(10):
        try:
            wrapped(i)
            seq2.append(False)
        except ConnectionError:
            seq2.append(True)

    assert seq1 == seq2


def test_bound_method_wrapping() -> None:
    class Service:
        def call(self, x: int) -> int:
            return x + 1

    svc = Service()
    plan = FaultPlan([Rule("svc.call", Raise(lambda: RuntimeError()), first=1)])
    wrapped = plan.wrap(svc.call, "svc.call")

    with pytest.raises(RuntimeError):
        wrapped(1)
    assert wrapped(2) == 3


def test_real_function_exception_passes_through() -> None:
    def real_with_error(x: int) -> int:
        if x < 0:
            raise KeyError("negative")
        return x

    plan = FaultPlan([Rule("x", Raise(lambda: RuntimeError()), on_calls=frozenset({99}))])
    wrapped = plan.wrap(real_with_error, "x")

    with pytest.raises(KeyError):
        wrapped(-1)
