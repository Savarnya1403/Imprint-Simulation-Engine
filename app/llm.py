"""Optional open-source LLM support.

Imprint runs fully without a model. If a GGUF file is present in ./models/ or an
OpenAI-compatible endpoint is configured (IMPRINT_LLM_BASE_URL), the same
surfaces (citizen chat, debate challenges, reasoning memos) can use it. Nothing
in the simulation depends on it; failures fall back to the deterministic core.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
DEFAULT_MODEL = os.environ.get("IMPRINT_LLM_MODEL", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
BASE_URL = os.environ.get("IMPRINT_LLM_BASE_URL", "").strip()
API_KEY = os.environ.get("IMPRINT_LLM_API_KEY", "ollama").strip()

_llm = None
_load_attempted = False
_load_error: str | None = None


def _find_model() -> Path | None:
    if BASE_URL:
        return None  # remote endpoint, no local file needed
    env_path = os.environ.get("IMPRINT_LLM_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return Path(env_path)
    p = MODEL_DIR / DEFAULT_MODEL
    if p.exists():
        return p
    # any gguf
    ggufs = sorted(MODEL_DIR.glob("*.gguf"))
    return ggufs[0] if ggufs else None


def load() -> bool:
    global _llm, _load_attempted, _load_error
    if _load_attempted:
        return _llm is not None
    _load_attempted = True
    if BASE_URL:
        _llm = {"backend": "openai-compatible", "base_url": BASE_URL, "model": os.environ.get("IMPRINT_LLM_MODEL", "llama3.2")}
        return True
    model_path = _find_model()
    if model_path is None:
        _load_error = "No GGUF model found in ./models and no IMPRINT_LLM_BASE_URL set."
        return False
    try:
        from llama_cpp import Llama
        _llm = {"backend": "llama-cpp", "model": Llama(model_path=str(model_path), n_ctx=2048, n_threads=4, verbose=False)}
        _load_error = None
        return True
    except Exception as exc:
        _load_error = f"{type(exc).__name__}: {exc}"
        _llm = None
        return False


def status() -> dict[str, Any]:
    loaded = load()
    mp = _find_model()
    return {
        "available": loaded,
        "backend": (_llm or {}).get("backend") if _llm else None,
        "model": (_llm or {}).get("model") if isinstance((_llm or {}).get("model"), str) else (mp.name if mp else None),
        "model_path": str(mp) if mp else None,
        "base_url": BASE_URL or None,
        "error": _load_error,
    }


def generate(prompt: str, max_tokens: int = 120, temperature: float = 0.7, system: str | None = None) -> str | None:
    if not load():
        return None
    backend = _llm["backend"]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        if backend == "llama-cpp":
            out = _llm["model"].create_chat_completion(messages=messages, max_tokens=max_tokens, temperature=temperature)
            return (out["choices"][0]["message"]["content"] or "").strip()
        if backend == "openai-compatible":
            import httpx
            url = _llm["base_url"].rstrip("/") + "/chat/completions"
            payload = {"model": _llm["model"], "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
            headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
            return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        global _load_error
        _load_error = f"{type(exc).__name__}: {exc}"
        return None
    return None