"""Lightweight research layer for arbitrary user hypotheses.

The product is not allowed to pretend it has an analyst on call. What it can do
honestly is fetch a public, citable summary (Wikipedia) for the thing the user
typed, cache it, and feed that context into the generic topic pack so a custom
brief is not simulated in a vacuum. Network failures degrade to "no research",
never to a crash.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent / "data" / "research_cache.json"
TIMEOUT = 4.0


def _load_cache() -> dict:
    try:
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _key(brief: str) -> str:
    return hashlib.sha256((brief or "").strip().lower().encode("utf-8")).hexdigest()[:16]


def _fetch_json(url: str) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def research(brief: str) -> dict:
    brief = (brief or "").strip()
    if not brief:
        return {"ok": False, "error": "empty brief"}
    cache = _load_cache()
    k = _key(brief)
    if k in cache:
        out = dict(cache[k])
        out["cached"] = True
        return out

    # 1. Search Wikipedia for the most relevant title. Try the full phrase, then
    # shorter fallbacks so a long custom brief still finds something.
    candidates = [brief[:120]]
    words = brief.split()
    if len(words) > 4:
        candidates.append(" ".join(words[:4]))
    if len(words) > 2:
        candidates.append(" ".join(words[:2]))
    if len(words) > 1:
        candidates.append(words[0])
    titles = []
    for cand in candidates:
        q = urllib.parse.quote(cand)
        search = _fetch_json(f"https://en.wikipedia.org/w/api.php?action=opensearch&search={q}&limit=3&namespace=0&format=json")
        if isinstance(search, list) and len(search) >= 2 and isinstance(search[1], list) and search[1]:
            titles = search[1]
            break
    title = titles[0] if titles else None

    out = {"ok": False, "brief": brief, "cached": False, "queried_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if title:
        t = urllib.parse.quote(title.replace(" ", "_"))
        summary = _fetch_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{t}")
        if isinstance(summary, dict) and summary.get("extract"):
            out = {
                "ok": True,
                "brief": brief,
                "title": summary.get("title", title),
                "extract": summary.get("extract", ""),
                "url": summary.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{t}"),
                "thumbnail": (summary.get("thumbnail") or {}).get("source"),
                "source": "Wikipedia (CC BY-SA)",
                "alternatives": titles[1:],
                "cached": False,
                "queried_at": out["queried_at"],
            }
    if not out.get("ok"):
        out["error"] = "No Wikipedia summary found for this phrase; simulation uses the generic priors."

    cache[k] = {k2: v for k2, v in out.items() if k2 != "cached"}
    _save_cache(cache)
    return out