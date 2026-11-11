# trysac-fault-injector

> Inject faults into outbound calls in tests: wrap sync or async callables with rules that raise, delay through an injected sleep, or return canned values, on deterministic triggers such as call counts or a seeded probability.

## Description

Retry, timeout and fallback code is hard to test because making a dependency fail at the right moment needs ad hoc mocks per test. This library describes faults declaratively per call target, triggers them on call counts or a seeded probability, uses injected sleep callables instead of real sleeps, and keeps a bounded history tests can assert on. The package is `fault_injector`, uses only the Python standard library at runtime, and supports sync and async callables.

## Installation

```bash
pip install trysac-fault-injector
```

Import name: `fault_injector`.

## Usage

```python
from fault_injector import FaultPlan, Raise, Rule


def charge(amount):
    return "charged"


plan = FaultPlan([Rule("payments.charge", Raise(lambda: TimeoutError("injected")), first=2)])
wrapped = plan.wrap(charge, "payments.charge")
for amount in (1, 2, 3):
    try:
        print(wrapped(amount))
    except TimeoutError:
        print("timeout")
assert [i.kind for i in plan.history] == ["raise", "raise"]
```

## Public API

`FaultPlan(rules, *, seed=0, sleep=time.sleep, async_sleep=asyncio.sleep, max_history=10_000, on_event=None)` coordinates injection for wrapped targets. Methods and properties: `wrap(fn, target)` returns a `functools.wraps` wrapper (async when `fn` is a coroutine function); `patch(obj, attr, target)` is a context manager that restores the original attribute; `enable()`, `disable()` and `reset()` manage state; `history` returns a copy of the bounded injection list; `dropped` returns the number of records dropped because `max_history` was full.

`Rule(target, fault, *, first=None, every=None, on_calls=None, probability=None, max_injections=None)`: `target` is an `fnmatch.fnmatchcase` pattern; call numbers are 1-based and counted per exact target name passed to `wrap`. Rules are checked in order and the first matching rule whose triggers all hold fires. `first=n` fires on calls <= n, `every=n` on call % n == 0, `on_calls` on the set, `probability=p` with one `random.Random(seed)` draw per matching call before other triggers, and `max_injections` caps firings. A rule without triggers fires on every call.

Faults: `Raise(factory)` calls the factory on each injection and raises its result; `Return(value)` returns the value without calling the wrapped function; `Delay(seconds, then=None)` sleeps through the injected `sleep`/`async_sleep`, then calls through, or applies `then` if set. `Injection(target, call, kind)` is a frozen record with `kind` in `raise`, `delay`, `return`.

Errors and limits: `FaultError.code` is one of `invalid_rule`, `invalid_target`, `too_many_rules`; the exception message is the code. A plan accepts at most 100 rules. Targets must be 1-200 character strings. `first`, `every` and `max_injections` must be integers >= 1; `probability` must be in [0, 1]; `Delay.seconds` must be finite and >= 0. History beyond `max_history` drops the oldest record and increments `dropped`. `on_event` receives only `{'event': 'fault_injected', 'target': ..., 'call': ..., 'kind': ...}` after the state lock is released.

## Why not unittest.mock side_effect lists

`unittest.mock` `side_effect` lists attach failures to one mock's call order and require ad hoc code for per-target patterns, call-count triggers, seeded probability, async-aware sleeps and bounded assertable history. This library exposes those controls as declarative `Rule` objects and a `FaultPlan` with injected sleep callables.

## Documentation

See [docs/SECURITY.md](docs/SECURITY.md) for the threat model, plus `docs/ARCHITECTURE.md`, `docs/TESTING.md`, and `docs/PROJECT.md`.

## License

MIT
