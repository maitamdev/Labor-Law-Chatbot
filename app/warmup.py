# -*- coding: utf-8 -*-
"""
VietLabor AI - Background Ollama warm-up.

Measured on the reference laptop (RTX 3060 6GB, qwen2.5:7b-instruct-q4_0):
first draft token ~8.3 s when the model is cold vs ~0.4 s when it is resident.
Loading the model while the user is still reading the welcome screen removes
that cold-start penalty from the first question.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_thread: Optional[threading.Thread] = None
_state: dict[str, Any] = {"started": False, "done": False, "ok": None}


def warmup_state() -> dict[str, Any]:
    """Snapshot of the warm-up status (for diagnostics / UI badges)."""
    return dict(_state)


def start_background_warmup(
    manager_factory: Optional[Callable[[], Any]] = None,
    enabled: Optional[bool] = None,
) -> Optional[threading.Thread]:
    """Starts the warm-up once per process. Safe to call on every Streamlit rerun."""
    global _thread
    if enabled is None:
        from config.settings import OLLAMA_WARMUP_ON_START
        enabled = OLLAMA_WARMUP_ON_START
    if not enabled:
        return None

    with _lock:
        if _state["started"]:
            return _thread
        _state["started"] = True

        def _run() -> None:
            try:
                if manager_factory is not None:
                    manager = manager_factory()
                else:
                    from models.local_llm import LocalLLMManager
                    manager = LocalLLMManager()
                _state["ok"] = bool(manager.warm_up())
            except Exception as exc:  # never crash the UI because of warm-up
                logger.warning("Background warm-up failed: %s", exc)
                _state["ok"] = False
            finally:
                _state["done"] = True

        _thread = threading.Thread(target=_run, name="ollama-warmup", daemon=True)
        _thread.start()
        return _thread


def _reset_for_tests() -> None:
    global _thread
    with _lock:
        _thread = None
        _state.update({"started": False, "done": False, "ok": None})
