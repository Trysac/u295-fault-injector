# fault-injector

[![PyPI version](https://img.shields.io/pypi/v/trysac-fault-injector)](https://pypi.org/project/trysac-fault-injector/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-fault-injector)](LICENSE)
[![CI](https://github.com/Trysac/u295-fault-injector/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u295-fault-injector/actions/workflows/ci.yml)

Inject faults into outbound calls in tests: wrap sync or async callables with rules that raise, delay through an injected sleep or return canned values, on deterministic triggers

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-fault-injector
# or
uv add trysac-fault-injector
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import fault_injector

# normalize() trims surrounding whitespace and lower-cases the text.
print(fault_injector.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    fault_injector.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
