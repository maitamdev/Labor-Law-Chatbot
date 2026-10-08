# -*- coding: utf-8 -*-
"""
VietLabor AI - Local LLM Manager
Provides interface to local Ollama inference server running on localhost:11434.
Strictly offline, zero cloud APIs, zero remote endpoints, zero API keys.
Wraps local Qwen instruct model using LangChain ChatOllama adapter.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from langchain_ollama import ChatOllama

from config.settings import (
    OLLAMA_BASE_URL,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_GPU,
    OLLAMA_NUM_PREDICT,
)

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = OLLAMA_BASE_URL
DEFAULT_MODEL_NAME = OLLAMA_MODEL

LEGAL_ANSWER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string"},
                    "issue": {"type": "string"},
                    "conclusion": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["issue_id", "issue", "conclusion", "evidence_ids"],
            },
        },
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": ["string", "null"]},
        "out_of_scope": {"type": "boolean"},
    },
    "required": ["answer", "findings", "needs_clarification", "out_of_scope"],
}


def check_ollama_health(base_url: str = DEFAULT_OLLAMA_URL) -> Dict[str, Any]:
    """Checks whether the local Ollama daemon is reachable and lists available models."""
    tags_url = f"{base_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(tags_url, headers={"User-Agent": "VietLabor-AI"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "online": True,
                    "base_url": base_url,
                    "models": models,
                    "error": None,
                }
    except Exception as e:
        return {
            "online": False,
            "base_url": base_url,
            "models": [],
            "error": str(e),
        }
    return {"online": False, "base_url": base_url, "models": [], "error": "Unknown state"}


def _split_model_name(name: str) -> tuple[str, str]:
    base, _, tag = (name or "").strip().lower().partition(":")
    return base, tag or "latest"


def resolve_installed_model(requested: str, available: List[str]) -> Optional[str]:
    """Maps the configured model name onto an installed Ollama tag.

    Order of preference:
      1. Exact name ("qwen2.5:7b-instruct-q4_0").
      2. Same name with the implicit ":latest" tag.
      3. Same family AND same parameter size, e.g. config "qwen2.5:7b-instruct-q4_0"
         accepts an installed "qwen2.5:7b" or "qwen2.5:7b-instruct" (instruct
         variants first). A different family (qwen2.5-coder) or size (14b) is
         never substituted silently.
    Returns None when nothing compatible is installed.
    """
    installed = [str(m) for m in available if m]
    if requested in installed:
        return requested
    req_base, req_tag = _split_model_name(requested)
    by_norm = {f"{b}:{t}": name for name in installed for b, t in [_split_model_name(name)]}
    if f"{req_base}:{req_tag}" in by_norm:
        return by_norm[f"{req_base}:{req_tag}"]

    req_size = req_tag.split("-")[0]  # "7b" from "7b-instruct-q4_0"
    if not req_size or not req_size[0].isdigit():
        return None
    candidates = []
    for name in installed:
        base, tag = _split_model_name(name)
        if base == req_base and tag.split("-")[0] == req_size:
            candidates.append((0 if "instruct" in tag else 1, len(tag), name))
    return min(candidates)[2] if candidates else None


class LocalLLMManager:
    """Manages connection and parameterization for local Qwen model via Ollama."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        base_url: str = DEFAULT_OLLAMA_URL,
        temperature: float = 0.0,
        num_predict: int = OLLAMA_NUM_PREDICT,
        num_ctx: int = OLLAMA_NUM_CTX,
        num_gpu: int = OLLAMA_NUM_GPU,
        keep_alive: str = OLLAMA_KEEP_ALIVE,
    ):

        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.num_gpu = num_gpu
        self.keep_alive = keep_alive
        self._llm: Optional[ChatOllama] = None

    def get_llm(self) -> ChatOllama:
        """Returns initialized ChatOllama instance configured for deterministic JSON reasoning."""
        if self._llm is None:
            health = check_ollama_health(self.base_url)
            if not health["online"]:
                raise ConnectionError(
                    f"Ollama server is not reachable at {self.base_url}. "
                    "Ensure 'ollama serve' is running locally."
                )
            available_models = [str(name) for name in health.get("models", []) if name]
            resolved = resolve_installed_model(self.model_name, available_models)
            if resolved is None:
                installed = ", ".join(available_models) or "(chưa có mô hình nào)"
                raise FileNotFoundError(
                    f"Ollama model '{self.model_name}' is not installed. "
                    f"Run: ollama pull {self.model_name} "
                    f"(or set OLLAMA_MODEL to an installed model). Installed: {installed}"
                )
            if resolved != self.model_name:
                logger.warning(
                    "Configured Ollama model '%s' not installed; using compatible installed model '%s'.",
                    self.model_name, resolved,
                )
                self.model_name = resolved

            logger.info(f"Initializing local ChatOllama model='{self.model_name}' at {self.base_url}")
            self._llm = ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature,
                num_predict=self.num_predict,
                num_ctx=self.num_ctx,
                num_gpu=self.num_gpu,
                keep_alive=self.keep_alive,
                format=LEGAL_ANSWER_JSON_SCHEMA,
                seed=42,
                top_p=0.9,
                repeat_penalty=1.05,
            )
        return self._llm

    def get_aux_llm(self, json_schema: Optional[Dict[str, Any]] = None, num_predict: int = 160) -> ChatOllama:
        """Short, deterministic model handle for auxiliary tasks (e.g. query rewriting).

        Unlike get_llm(), it does NOT force the legal-answer schema. Pass a small
        JSON schema to constrain the output, or None for plain text.
        """
        self.get_llm()  # health check + tag resolution (sets self.model_name)
        return ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=0.0,
            num_predict=num_predict,
            num_ctx=self.num_ctx,
            num_gpu=self.num_gpu,
            keep_alive=self.keep_alive,
            format=json_schema if json_schema is not None else "",
            seed=42,
        )

    def warm_up(self, timeout: float = 120.0) -> bool:
        """Loads the model into (GPU) memory ahead of the first question.

        Ollama loads a model on an empty-prompt generate call and keeps it for
        `keep_alive`. Safe to call from a background thread; never raises.
        """
        try:
            self.get_llm()
            payload = json.dumps({
                "model": self.model_name, "prompt": "", "keep_alive": self.keep_alive,
                # Must match the chat options: a different num_ctx/num_gpu makes
                # Ollama reload the model on the first real question.
                "options": {"num_ctx": self.num_ctx, "num_gpu": self.num_gpu},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/api/generate", data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ok = resp.status == 200
            logger.info("Ollama model '%s' warm-up %s", self.model_name, "done" if ok else "failed")
            return ok
        except Exception as exc:
            logger.warning("Ollama warm-up skipped: %s", exc)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Returns metadata regarding the active local LLM configuration."""
        return {
            "selected_model": self.model_name,
            "parameter_size": None,
            "quantization": None,
            "provider": "Ollama Local",
            "endpoint": self.base_url,
            "temperature": self.temperature,
            "context_window": self.num_ctx,
            "max_output_tokens": self.num_predict,
            "gpu_layers": self.num_gpu,
            "hardware_target": "Detected and managed by the local Ollama runtime",
        }
