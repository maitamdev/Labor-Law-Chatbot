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

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL_NAME = "qwen2.5:7b"


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


class LocalLLMManager:
    """Manages connection and parameterization for local Qwen model via Ollama."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        base_url: str = DEFAULT_OLLAMA_URL,
        temperature: float = 0.0,
        num_predict: int = 1536,
        num_ctx: int = 8192,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.num_predict = num_predict
        self.num_ctx = num_ctx
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

            logger.info(f"Initializing local ChatOllama model='{self.model_name}' at {self.base_url}")
            self._llm = ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature,
                num_predict=self.num_predict,
                num_ctx=self.num_ctx,
                format="json",
            )
        return self._llm

    def get_model_info(self) -> Dict[str, Any]:
        """Returns metadata regarding the active local LLM configuration."""
        return {
            "selected_model": self.model_name,
            "parameter_size": "7.61B",
            "quantization": "Q4_K_M",
            "provider": "Ollama Local",
            "endpoint": self.base_url,
            "temperature": self.temperature,
            "context_window": self.num_ctx,
            "hardware_target": "NVIDIA GeForce RTX 3060 Laptop (6GB VRAM) / 100% GPU offload",
        }
