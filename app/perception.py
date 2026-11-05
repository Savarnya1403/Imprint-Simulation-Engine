"""Precedent retrieval and soft perception priors.

The model does not learn "decision X caused outcome Y". With sixteen cases that
would overfit. It retrieves analogous decisions, carries their perception arcs
as a wide prior, and exposes the base rates to the report. The arcs are
reconstructed from public reporting; they are not measured panels.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from statistics import median

DATA = Path(__file__).parent / "data"
PATH = DATA / "precedents.json"

STOP = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "is", "are",
    "with", "at", "by", "from", "as", "that", "this", "it", "its", "be", "was",
    "were", "has", "have", "had", "but", "not", "than", "then", "into", "over",
    "india", "indian", "consumer", "consumers", "market", "will",
}


def _tok(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9₹]+", str(text or "").lower()) if len(w) > 1 and w not in STOP]


@lru_cache(maxsize=1)
def raw() -> dict:
    return json.loads(PATH.read_text())


@lru_cache(maxsize=1)
def cases() -> list[dict]:
    return raw()["cases"]


@lru_cache(maxsize=1)
def case_map() -> dict[str, dict]:
    return {c["id"]: c for c in cases()}


def fit_curve(case: dict, days: list[int] | None = None) -> list[dict]:
    """Linear interpolation of the reconstructed perception points."""
    pts = sorted(case.get("perception", []), key=lambda x: x["day"])
    if not pts:
        return []
    if days is None:
        days = list(range(-14, 61))
    out = []
    for d in days:
        if d <= pts[0]["day"]:
            row = pts[0]
        elif d >= pts[-1]["day"]:
            row = pts[-1]
        else:
            lo = max((p for p in pts if p["day"] <= d), key=lambda p: p["day"])
            hi = min((p for p in pts if p["day"] >= d), key=lambda p: p["day"])
            if hi["day"] == lo["day"]:
                row = lo
            else:
                t = (d - lo["day"]) / (hi["day"] - lo["day"])
                row = {k: lo[k] + (hi[k] - lo[k]) * t for k in ("support", "neutral", "oppose")}
        out.append({"day": d, **{k: round(float(row[k]), 3) for k in ("support", "neutral", "oppose")}})
    return out


def _score(text_tokens: list[str], case: dict, topic_id: str | None, category: str | None) -> float:
    body = " ".join([
        case.get("brand", ""), case.get("decision", ""), case.get("summary", ""),
        case.get("context", ""), case.get("category", ""), " ".join(case.get("tags", [])),
        " ".join(case.get("mechanisms", [])),
    ]).lower()
    toks = set(_tok(body))
    score = 0.0
    for t in text_tokens:
        if t in toks:
            score += 2.2 if len(t) > 4 else 1.4
    if category and category.lower() in (case.get("category", "") + " " + " ".join(case.get("tags", []))).lower():
        score += 2.0
    if topic_id and topic_id.replace("-", " ") in body:
        score += 1.0
    # recency: newer cases are more relevant to current behaviour
    score += max(0.0, (case.get("year", 2015) - 2012) / 12)
    return score


def summarise(case: dict) -> dict:
    out = case.get("outcome", {})
    return {
        "id": case["id"], "brand": case["brand"], "decision": case["decision"],
        "year": case["year"], "category": case["category"], "tags": case.get("tags", []),
        "summary": case["summary"], "treatment_type": case.get("treatment_type", ""),
        "geography": case.get("geography", "India"),
        "peak_oppose_day": case.get("peak_oppose_day"),
        "peak_support_day": case.get("peak_support_day"),
        "half_life_days": case.get("half_life_days"),
        "outcome": out,
        "mechanisms": case.get("mechanisms", []),
        "segments": case.get("segments", []),
        "sources": case.get("sources", []),
        "caveats": case.get("caveats", ""),
    }


def retrieve(text: str, topic_id: str | None = None, category: str | None = None, k: int = 4) -> list[dict]:
    toks = _tok(text)
    scored = [(_score(toks, c, topic_id, category), c) for c in cases()]
    scored.sort(key=lambda x: -x[0])
    top = [(s, c) for s, c in scored if s > 0][:k]
    if not top:
        top = scored[:k]
    mx = max(1.0, top[0][0])
    out = []
    for s, c in top:
        item = summarise(c)
        item["similarity"] = round(min(1.0, s / mx), 3)
        item["curve"] = fit_curve(c, [-14, -7, 0, 7, 14, 30, 45, 60])
        out.append(item)
    return out


def base_rates() -> dict:
    cs = cases()
    neg = [c for c in cs if c["outcome"]["direction"] == "down"]
    pos = [c for c in cs if c["outcome"]["direction"] == "up"]
    flat = [c for c in cs if c["outcome"]["direction"] == "flat"]
    peaks = [c.get("peak_oppose_day", 0) for c in cs if c.get("peak_oppose_day") is not None]
    halves = [c.get("half_life_days", 30) for c in cs]
    return {
        "n": len(cs),
        "negative_outcomes": len(neg),
        "positive_outcomes": len(pos),
        "flat_outcomes": len(flat),
        "share_negative": round(len(neg) / max(1, len(cs)), 3),
        "median_peak_oppose_day": median(peaks) if peaks else None,
        "median_half_life_days": median(halves) if halves else None,
        "median_peak_oppose_share": round(median([
            max(p["oppose"] for p in c["perception"]) for c in cs
        ]), 3),
        "note": "Base rates from a reconstructed, purposively selected case library. Not a random sample of decisions.",
    }


def prior_for_simulation(text: str, topic: dict, k: int = 4) -> dict:
    """Turn retrieved precedents into bounded simulation adjustments.

    This is a prior, not an identified effect. It is intentionally wide and is
    shown to the user next to the simulation output.
    """
    cs = retrieve(text, topic_id=topic.get("id"), category=topic.get("category"), k=k)
    if not cs:
        return {"precedents": [], "base_rates": base_rates()}
    peak_oppose = [max(p["oppose"] for p in c["curve"]) for c in cs]
    halves = [c.get("half_life_days") or 30 for c in cs]
    neg = [c for c in cs if c["outcome"]["direction"] == "down"]
    pos = [c for c in cs if c["outcome"]["direction"] == "up"]
    p_neg = len(neg) / len(cs)
    # Bounded adjustments: no precedent can move the simulation more than ~20%.
    trust_scale = round(0.85 + 0.35 * (sum(peak_oppose) / len(peak_oppose)), 3)
    recovery = int(median(halves)) if halves else 30
    direction = "negative" if p_neg >= .6 else "positive" if len(pos) / len(cs) >= .6 else "mixed"
    return {
        "precedents": cs,
        "base_rates": base_rates(),
        "adjustments": {
            "trust_shock_scale": min(1.35, max(0.75, trust_scale)),
            "recovery_days": recovery,
            "outcome_direction": direction,
            "negative_outcome_share": round(p_neg, 3),
            "prior_sd_pct": round(8 + 10 * (1 - min(1, len(cs) / 6)), 1),
        },
        "note": (
            "Precedent prior only. The cases are reconstructed from public reporting, "
            "not a measured panel; the adjustment is capped and should be read as a "
            "hypothesis, not an identified effect."
        ),
    }
