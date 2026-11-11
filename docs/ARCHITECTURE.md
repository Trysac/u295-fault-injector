# Architecture

## Design Decisions

### Thread-Safe State Management

Mutable state (`_call_counts`, `_rule_injection_counts`, `_history`, `_dropped`, `_enabled`) is protected by a single `threading.Lock`. `_begin_call` holds the lock while counting a call, selecting a rule, incrementing the rule counter and appending history. The lock is released before the wrapped function, the injected sleep, or the `on_event` callback runs; async wrappers never hold the lock across an `await`. `history` returns a list copy and `dropped` is read under the lock.

### Deterministic Probability with a Per-Plan RNG

Each `FaultPlan` owns a `random.Random(seed)` instance. For every rule whose target pattern matches, if `probability` is set, one `rng.random()` draw is made before `first`, `every`, `on_calls` and `max_injections` are evaluated. `reset()` clears counters and history, resets `dropped`, and reseeds the RNG with the original `seed`.

### Bounded History with Drop Tracking

Injection records are stored in a `collections.deque` with `maxlen=max_history` (default 10,000). When the deque is full, the oldest entry is discarded, `dropped` increments, and the new `Injection` is appended. `history` returns `list(self._history)`.

### Rule Matching and Fault Application

`FaultPlan.wrap(fn, target)` validates the target, uses `functools.wraps`, and returns an async wrapper when `inspect.iscoroutinefunction(fn)` is true. Call numbers are 1-based and kept per exact target name. Rules are checked in order with `fnmatch.fnmatchcase(target, rule.target)`; the first rule whose triggers hold fires. A rule with no triggers fires on every call.

- `Raise` calls `factory()` on each injection and raises the returned exception.
- `Return` returns `value` without calling the wrapped function.
- `Delay` records a `delay` injection, calls `sleep`/`async_sleep` with `seconds`, then calls the original function if `then` is `None`, or recursively applies `then` without adding another history record.
- `patch(obj, attr, target)` sets `getattr(obj, attr)` to a wrapped version and restores the original object in `finally`.

### Validation

- Rule and `wrap` targets must be strings of 1-200 characters; otherwise `FaultError('invalid_target')`.
- `first`, `every` and `max_injections` must be integers >= 1; `probability` must be in [0, 1]; `Delay.seconds` must be finite and >= 0; violations raise `FaultError('invalid_rule')`.
- A plan accepts at most 100 rules; exceeding raises `FaultError('too_many_rules')`.

### Logging

A module-level `logging.getLogger(__name__)` has a `NullHandler`. `_record_injection` emits a debug message `injected %s into %s on call %d`; no other library logging is emitted. `on_event` is called after the lock is released.

## Testing Strategy

`tests/test_fault_injector.py` covers the public surface and validation cases listed in `docs/TESTING.md`; `tests/test_plan.py` covers plan execution through the public API. Timing-sensitive tests inject fake `sleep` and `async_sleep` callables, and probabilistic tests use the plan `seed`.
