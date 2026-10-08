from __future__ import annotations

import os

import pytest

# Deterministic test runs: these features call the live Ollama daemon. Tests that
# cover them construct the components explicitly with fake LLMs.
os.environ.setdefault("VIETLABOR_LLM_FOLLOWUP_REWRITE", "0")
os.environ.setdefault("VIETLABOR_OLLAMA_WARMUP", "0")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-ollama",
        action="store_true",
        default=False,
        help="run tests that require a live local Ollama daemon",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-ollama"):
        return
    skip = pytest.mark.skip(reason="requires Ollama; rerun with --run-ollama")
    for item in items:
        if "ollama" in item.keywords:
            item.add_marker(skip)
