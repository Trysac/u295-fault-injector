# Stack

## Used

| Tool | Why |
|---|---|
| Python standard library | The only runtime dependency. The package uses `asyncio`, `collections`, `contextlib`, `dataclasses`, `fnmatch`, `functools`, `inspect`, `logging`, `random`, `threading`, `time` and `typing`. |
| pytest | The provided tests are pytest modules: `tests/test_fault_injector.py` and `tests/test_plan.py`. |
| `py.typed` | The package ships `src/fault_injector/py.typed` for typing consumers. |

## Discarded

| Tool | Why not |
|---|---|
| `unittest.mock` `side_effect` lists | The library instead provides declarative per-target rules, seeded probability, injected sleep callables and bounded assertable history. |
| Network proxies and HTTP status simulators | Out of scope: the library injects in-process faults only. |
| Production chaos tooling | Out of scope per `docs/PROJECT.md`. |
