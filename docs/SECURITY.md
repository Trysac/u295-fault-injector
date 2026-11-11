# Security notes

## Threat model

`trysac-fault-injector` is an in-process test library with no runtime I/O, network calls, `eval`, `exec`, or deserialization. It is not a security boundary.

### Defended

- Configuration validation: targets are strings of 1-200 characters; `first`, `every` and `max_injections` are integers >= 1; `probability` is in [0, 1]; `Delay.seconds` is finite and >= 0; at most 100 rules per plan. Violations raise `FaultError` with a code from `invalid_rule`, `invalid_target`, `too_many_rules`; the message is the code.
- Bounded history: `max_history` defaults to 10,000; when full, the oldest record is dropped and `dropped` increments, so history assertions do not grow without bound.
- Callback payload limits: `on_event` receives `{'event': 'fault_injected', 'target': ..., 'call': ..., 'kind': ...}` and never receives call arguments or keyword arguments.
- Counter integrity: call counters, rule injection counters, history and dropped are protected by a `threading.Lock`. The lock is released before the wrapped function, the injected sleep, or the `on_event` callback runs.
- Seeded probability uses a per-plan `random.Random(seed)`; `reset()` reseeds it.

### Not defended

- `Raise` factories, wrapped callables, `sleep`/`async_sleep` callables and `on_event` handlers run arbitrary caller-supplied code with the caller's privileges.
- Target names appear in `Injection` records, `on_event` payloads and debug logs; do not put secrets in a target name.
- The plan does not limit the number of distinct target names, so `_call_counts` can grow with unique targets even though rule count and history are bounded.
- No network-level faults, HTTP status simulation, production chaos or patching by import path strings are provided.
- No authentication, authorization, encryption, secret storage or audit log is provided.

## Publishing

The library contains no publishing or credential logic. If it is published to a package index, use the index's standard trusted-publishing or token flow outside this code and do not commit credentials.
