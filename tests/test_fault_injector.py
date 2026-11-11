"""Behavior tests for the public API of fault_injector."""

from __future__ import annotations

import pytest

import fault_injector


def test_normalize_trims_and_lowercases() -> None:
    assert fault_injector.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        fault_injector.normalize(value)


def test_version_is_semver() -> None:
    parts = fault_injector.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
