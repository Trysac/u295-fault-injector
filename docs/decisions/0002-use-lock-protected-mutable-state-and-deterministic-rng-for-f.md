# Use lock-protected mutable state and deterministic RNG for fault injection

Status: accepted (generated, pending human review)

## Context

The fault injector needs to maintain per-target call counts, per-rule injection counts, a bounded history, and a seeded random number generator. These must be correct under concurrent calls and reproducible across test runs.

## Decision

All mutable state is guarded by a single `threading.Lock`. Each `FaultPlan` creates its own `random.Random(seed)` and uses it for all probability draws. The lock is held for counter updates and history operations but not for sleeping or fault application, avoiding deadlocks and unnecessary contention.

## Consequences

Concurrent use is safe. Tests can reset the plan to reproduce the exact sequence of faults. The lock introduces minimal overhead and does not affect the determinism of the injected faults.
