"""LLM backends for the Imprint Simulation Engine.

Priority order:
  1. Anthropic Claude Opus 4.7  — set ANTHROPIC_API_KEY
  2. OpenAI-compatible endpoint  — set IMPRINT_LLM_BASE_URL + IMPRINT_LLM_MODEL
  3. Local GGUF via llama-cpp    — set IMPRINT_LLM_LOCAL=1 (opt-in, dev only)
  4. Deterministic template fallback (always available, no model needed)

The simulation never hard-depends on a live model. Every call that returns None
triggers a deterministic fallback upstream. The goal of this module is to make
Claude Opus the default and best path while keeping the engine runnable offline.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("IMPRINT_ANTHROPIC_MODEL", "claude-opus-4-7-20250219").strip()

# OpenAI-compatible fallback
BASE_URL = os.environ.get("IMPRINT_LLM_BASE_URL", "").strip()
OAI_API_KEY = os.environ.get("IMPRINT_LLM_API_KEY", "ollama").strip()
OAI_MODEL = os.environ.get("IMPRINT_LLM_MODEL", "llama3.2").strip()

# Local GGUF (dev opt-in)
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
DEFAULT_GGUF = os.environ.get("IMPRINT_LLM_MODEL", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
LOCAL_OPT_IN = os.environ.get("IMPRINT_LLM_LOCAL", "").strip().lower() in ("1", "true", "yes", "on")

_state: dict[str, Any] = {
    "backend": None,   # "anthropic" | "openai-compatible" | "llama-cpp" | None
    "client": None,
    "attempted": False,
    "error": None,
}


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def _try_anthropic() -> bool:
    if not ANTHROPIC_API_KEY:
        return False
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        _state["backend"] = "anthropic"
        _state["client"] = client
        _state["error"] = None
        return True
    except Exception as exc:
        _state["error"] = f"Anthropic init failed: {type(exc).__name__}: {exc}"
        return False


def _try_openai_compat() -> bool:
    if not BASE_URL:
        return False
    _state["backend"] = "openai-compatible"
    _state["client"] = {"base_url": BASE_URL, "model": OAI_MODEL}
    return True


def _try_llama_cpp() -> bool:
    if not LOCAL_OPT_IN:
        return False
    model_path = None
    env_path = os.environ.get("IMPRINT_LLM_PATH", "").strip()
    if env_path and Path(env_path).exists():
        model_path = Path(env_path)
    elif (MODEL_DIR / DEFAULT_GGUF).exists():
        model_path = MODEL_DIR / DEFAULT_GGUF
    else:
        ggufs = sorted(MODEL_DIR.glob("*.gguf"))
        if ggufs:
            model_path = ggufs[0]
    if model_path is None:
        _state["error"] = "No GGUF model found and IMPRINT_LLM_LOCAL=1."
        return False
    try:
        from llama_cpp import Llama
        _state["backend"] = "llama-cpp"
        _state["client"] = Llama(model_path=str(model_path), n_ctx=2048, n_threads=4, verbose=False)
        _state["error"] = None
        return True
    except Exception as exc:
        _state["error"] = f"llama-cpp init: {type(exc).__name__}: {exc}"
        return False


def load() -> bool:
    if _state["attempted"]:
        return _state["backend"] is not None
    _state["attempted"] = True
    return _try_anthropic() or _try_openai_compat() or _try_llama_cpp()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def status() -> dict[str, Any]:
    load()
    return {
        "available": _state["backend"] is not None,
        "backend": _state["backend"],
        "model": ANTHROPIC_MODEL if _state["backend"] == "anthropic" else (
            (_state["client"] or {}).get("model") if isinstance(_state["client"], dict) else None
        ),
        "base_url": BASE_URL or None,
        "error": _state["error"],
    }


def generate(
    prompt: str,
    max_tokens: int = 256,
    temperature: float = 0.7,
    system: str | None = None,
) -> str | None:
    """Generate text. Returns None on any failure (caller uses deterministic fallback)."""
    if not load():
        return None
    backend = _state["backend"]
    try:
        if backend == "anthropic":
            return _anthropic_generate(prompt, max_tokens, temperature, system)
        if backend == "openai-compatible":
            return _oai_generate(prompt, max_tokens, temperature, system)
        if backend == "llama-cpp":
            return _llama_generate(prompt, max_tokens, temperature, system)
    except Exception as exc:
        _state["error"] = f"{type(exc).__name__}: {exc}"
    return None


def generate_structured(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str | None:
    """Higher-token structured generation path, primarily for the query interpreter."""
    return generate(prompt, max_tokens=max_tokens, temperature=temperature, system=system)


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

def _anthropic_generate(prompt: str, max_tokens: int, temperature: float, system: str | None) -> str | None:
    client = _state["client"]
    kwargs: dict[str, Any] = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return (response.content[0].text or "").strip()


def _oai_generate(prompt: str, max_tokens: int, temperature: float, system: str | None) -> str | None:
    import httpx
    cfg = _state["client"]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {OAI_API_KEY}"} if OAI_API_KEY else {}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(cfg["base_url"].rstrip("/") + "/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
    return (r.json()["choices"][0]["message"]["content"] or "").strip()


def _llama_generate(prompt: str, max_tokens: int, temperature: float, system: str | None) -> str | None:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    out = _state["client"].create_chat_completion(messages=messages, max_tokens=max_tokens, temperature=temperature)
    return (out["choices"][0]["message"]["content"] or "").strip()
