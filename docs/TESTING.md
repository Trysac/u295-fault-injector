# Testing

## Running

```sh
pytest
```

The provided test modules are under `tests/` and import the package as `fault_injector`.

## Policy

Tests use pytest and exercise the public package API. Timing is made deterministic by passing fake `sleep` and `async_sleep` callables into `FaultPlan`; probabilistic rules use the plan `seed`. No network, real sleep or external service is required by the library.

## Tiers

Only local pytest unit tests are present in the provided code: `tests/test_fault_injector.py` and `tests/test_plan.py`. No separate conformance tier or CI configuration is included.

## Layout

- `tests/test_fault_injector.py`: public-surface and validation tests. It covers `__all__` exports, semver `__version__`, `FaultError` code and short message, invalid rule triggers, `Delay` seconds validation, target length validation, the 100-rule limit, `on_calls` triggering, `patch` restoring an attribute when the body raises, async raise/return/passthrough, async delay-then-raise, and the plan logger's `NullHandler`.
- `tests/test_plan.py`: plan execution tests that import `FaultPlan`, `Rule`, `Raise`, `Return`, `Delay`, `Injection` and `FaultError`; it covers plan behaviour through the public API.

No `conftest.py` or additional test file is present in the provided code.
