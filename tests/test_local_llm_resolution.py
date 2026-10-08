# -*- coding: utf-8 -*-
"""Ollama model-name resolution: README tag vs config tag must both work."""
from models.local_llm import resolve_installed_model

CONFIG = "qwen2.5:7b-instruct-q4_0"


def test_exact_match_wins():
    assert resolve_installed_model(CONFIG, ["qwen2.5:7b", CONFIG]) == CONFIG


def test_readme_tag_accepted_for_config_default():
    assert resolve_installed_model(CONFIG, ["llama3:8b", "qwen2.5:7b"]) == "qwen2.5:7b"


def test_instruct_variant_preferred():
    installed = ["qwen2.5:7b", "qwen2.5:7b-instruct"]
    assert resolve_installed_model(CONFIG, installed) == "qwen2.5:7b-instruct"


def test_config_set_to_short_tag_accepts_quantized_install():
    assert resolve_installed_model("qwen2.5:7b", [CONFIG]) == CONFIG


def test_implicit_latest_tag():
    assert resolve_installed_model("qwen2.5", ["qwen2.5:latest"]) == "qwen2.5:latest"


def test_never_substitutes_other_family_or_size():
    assert resolve_installed_model(CONFIG, ["qwen2.5-coder:7b", "qwen2.5:14b", "qwen2.5:0.5b"]) is None
    assert resolve_installed_model(CONFIG, []) is None
