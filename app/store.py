"""Data loading for the Imprint Bharat simulation."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from . import research

DATA = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def states():
    return json.loads((DATA / "states.json").read_text())


@lru_cache(maxsize=1)
def archetypes():
    return json.loads((DATA / "archetypes.json").read_text())


@lru_cache(maxsize=1)
def biases():
    return json.loads((DATA / "biases.json").read_text())


@lru_cache(maxsize=1)
def tiers():
    return json.loads((DATA / "tiers.json").read_text())


@lru_cache(maxsize=1)
def names():
    return json.loads((DATA / "names.json").read_text())


@lru_cache(maxsize=1)
def topics():
    return json.loads((DATA / "topics.json").read_text())


@lru_cache(maxsize=1)
def evidence():
    return json.loads((DATA / "evidence.json").read_text())


def topic_map():
    return {t["id"]: t for t in topics()}


def evidence_map():
    return {e["id"]: e for e in evidence()}


def archetype_map():
    return {a["id"]: a for a in archetypes()}


def pick_topic(text: str) -> dict:
    """Keyword match a free-text hypothesis to the richest scenario pack."""
    t = (text or "").lower()
    best = None
    best_score = 0
    for topic in topics():
        score = 0
        for kw in topic.get("keywords", []):
            if kw in t:
                score += 2 + len(kw.split())
        # direct label words
        for word in topic["label"].lower().split():
            if len(word) > 3 and word in t:
                score += 1
        if topic["label"].lower() in t:
            score += 6
        if score > best_score:
            best_score = score
            best = topic
    # A single incidental label word (e.g. "young" in a protein brief) should not
    # silently route a custom hypothesis into an unrelated pack. Require at least
    # one substantive keyword match.
    if best and best_score >= 2:
        return best
    return _custom_topic(text or "")


def _custom_topic(brief: str) -> dict:
    import copy
    base = copy.deepcopy(topic_map()["generic"])
    base["id"] = "custom"
    base["label"] = (brief or "").strip()[:90] or "Custom hypothesis"
    base["category"] = "Custom"
    base["keywords"] = [str(brief or "").lower()]
    base["motion"] = f"The proposed idea — {str(brief or '').strip()} — will find mainstream acceptance in India within three years."
    m = re.search(r"₹\s?([\d,\.]+)\s*(lakh|lac|cr|crore)?", str(brief or ""), re.I)
    if m:
        num = float(m.group(1).replace(",", ""))
        unit = (m.group(2) or "").lower()
        if unit in ("lakh", "lac"):
            num *= 100000
        elif unit in ("cr", "crore"):
            num *= 10000000
        if num > 0:
            base["price"] = int(num)
            base["price_note"] = "Extracted from the brief"
    r = research.research(str(brief or ""))
    base["research"] = r
    if r.get("ok"):
        extract = (r.get("extract") or "").strip()
        if extract:
            base["ground_reality"] = [extract[:260]] + (base.get("ground_reality") or [])[:2]
        base["pro_claims"] = [f"Public context: {r.get('title')}.", * (base.get("pro_claims") or [])[:2]]
        base["hashtags"] = [f"#{str(r.get('title','')).replace(' ', '')}"] + (base.get("hashtags") or [])[:3]
    else:
        base["ground_reality"] = [f"No public summary found for this phrase. Treated as a custom hypothesis with generic Indian priors."] + (base.get("ground_reality") or [])[:2]
    return base
