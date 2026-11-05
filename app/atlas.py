"""Sourced Indian-consumer context graph.

This is the retrieval and reasoning layer behind the simulator. It is deliberately
not a black-box "trained model": every context node carries a source, a year, a
geography and a confidence label. Derived nodes (state, tier, occupation,
category) are generated from the public packs and say so.

The corpus can grow without changing this module: `app/ingest.py` appends chunks
to `app/data/corpus/chunks.jsonl`, and `search()` blends curated facts with those
chunks.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from . import store

DATA = Path(__file__).parent / "data"
CORPUS = DATA / "corpus"
ATLAS_PATH = DATA / "atlas.json"

STOP = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "is", "are",
    "with", "at", "by", "from", "as", "that", "this", "it", "its", "be", "was",
    "were", "has", "have", "had", "but", "not", "than", "then", "into", "over",
    "per", "vs", "india", "indian", "consumer", "consumers", "market",
}


def _tok(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9₹]+", str(text or "").lower()) if len(w) > 1 and w not in STOP]


@lru_cache(maxsize=1)
def raw() -> dict:
    return json.loads(ATLAS_PATH.read_text())


@lru_cache(maxsize=1)
def sources() -> dict[str, dict]:
    rows = {s["id"]: s for s in raw()["sources"]}
    reg = CORPUS / "sources.json"
    if reg.exists():
        try:
            data = json.loads(reg.read_text())
            extra = data if isinstance(data, list) else data.get("sources", [])
            for r in extra:
                if r.get("id") and r["id"] not in rows:
                    rows[r["id"]] = r
        except Exception:
            pass
    return rows


@lru_cache(maxsize=1)
def facts() -> list[dict]:
    return raw()["facts"]


@lru_cache(maxsize=1)
def fact_map() -> dict[str, dict]:
    return {f["id"]: f for f in facts()}


@lru_cache(maxsize=1)
def regions() -> list[dict]:
    return raw()["regions"]


@lru_cache(maxsize=1)
def region_map() -> dict[str, dict]:
    return {r["id"]: r for r in regions()}


@lru_cache(maxsize=1)
def norms() -> list[dict]:
    return raw()["norms"]


@lru_cache(maxsize=1)
def category_priors() -> dict[str, dict]:
    return {c["topic_id"]: c for c in raw()["category_priors"]}


@lru_cache(maxsize=1)
def anchors() -> dict[str, dict]:
    return {a["topic_id"]: a for a in raw()["anchors"]}


@lru_cache(maxsize=1)
def state_index() -> dict[str, dict]:
    return {s["name"]: s for s in store.states()}


def source_list(ids: Iterable[str] | None) -> list[dict]:
    sm = sources()
    return [sm[i] for i in (ids or []) if i in sm]


def citation(fact: dict, why: str = "") -> dict:
    srcs = source_list(fact.get("source_ids"))
    first = srcs[0] if srcs else {}
    return {
        "id": fact.get("id"),
        "type": fact.get("type", "fact"),
        "dimension": fact.get("dimension", "context"),
        "claim": fact.get("claim") or fact.get("title"),
        "value": fact.get("value", ""),
        "unit": fact.get("unit", ""),
        "year": fact.get("year") or first.get("year"),
        "geo": fact.get("geo", "India"),
        "confidence": fact.get("confidence", "medium"),
        "detail": fact.get("detail") or fact.get("body", ""),
        "why": why,
        "sources": srcs[:2],
    }


def _norm_fact(f: dict) -> dict:
    srcs = source_list(f.get("source_ids"))
    return {
        "id": f["id"],
        "type": "fact",
        "dimension": f["dimension"],
        "title": f["claim"],
        "body": f.get("detail", ""),
        "value": f.get("value", ""),
        "unit": f.get("unit", ""),
        "geo": f.get("geo", "India"),
        "year": f.get("year"),
        "confidence": f.get("confidence", "medium"),
        "tags": f.get("tags", []),
        "source_ids": f.get("source_ids", []),
        "sources": srcs,
    }


@lru_cache(maxsize=1)
def derived_nodes() -> list[dict]:
    """Structured context generated from the public packs.

    These are not independent observations. They expose the priors the simulator
    already uses so they can be inspected and contested.
    """
    out: list[dict] = []

    for s in store.states():
        out.append({
            "id": f"state:{s['name']}", "type": "state", "dimension": "geography",
            "title": f"{s['name']} · state context",
            "body": (
                f"{s['population_m']}m people; {s['urban_pct']}% urban; "
                f"{s['internet_pct']}% internet penetration; NSDP per capita ₹{s['nsdp_pc']:,}. "
                f"Cities in the pack: {', '.join(c['name'] + ' (T' + str(c['tier']) + ')' for c in s['cities'])}."
            ),
            "value": f"{s['population_m']}m", "unit": "population", "geo": s["name"],
            "year": 2024, "confidence": "medium", "tags": [s["name"].lower(), s["region"], "state", "tier"],
            "source_ids": ["census2011", "trai", "hces2223"],
            "sources": source_list(["census2011", "trai", "hces2223"]),
            "state": s["name"], "region": s["region"],
        })
        r = region_map().get(s["region"])
        if r:
            out.append({
                "id": f"region:{s['name']}", "type": "region_state", "dimension": "culture",
                "title": f"{s['name']} · cultural context",
                "body": f"{r['summary']} Consumption: {r['consumption']} Constraints: {r['constraints']}",
                "value": s["region"], "unit": "region", "geo": s["name"],
                "year": 2024, "confidence": "medium",
                "tags": [s["name"].lower(), s["region"], "culture", "norms", "status"],
                "source_ids": r["source_ids"], "sources": source_list(r["source_ids"]),
                "state": s["name"], "region": s["region"],
            })

    for t in store.tiers():
        out.append({
            "id": f"tier:{t['id']}", "type": "tier", "dimension": "cognition",
            "title": f"Tier {t['id']} · {t['label']}",
            "body": f"{t['worldview']} Decision: {t['decision']} Money: {t['money']}",
            "value": f"{round(t['share'] * 100)}%", "unit": "of sample", "geo": "India",
            "year": 2026, "confidence": "modelled",
            "tags": ["tier", f"t{t['id']}", "cognition", "class"],
            "source_ids": ["census2011", "hces2223", "iamai"],
            "sources": source_list(["census2011", "hces2223", "iamai"]),
            "tier": t["id"],
        })

    for a in store.archetypes():
        tiers = sorted(int(k) for k, v in a["tiers"].items() if v > 0)
        out.append({
            "id": f"occ:{a['id']}", "type": "occupation", "dimension": "jobs",
            "title": f"{a['label']} · occupational context",
            "body": f"{a['short']}. {a['quirk']} Aspires: {a['aspiration']} Fears: {', '.join(a['fears'][:3])}.",
            "value": a["category"], "unit": "category", "geo": "India",
            "year": 2026, "confidence": "modelled",
            "tags": [a["id"], a["category"].lower(), "occupation", "jobs", "income"],
            "source_ids": ["plfs2324", "hces2223", "census2011"],
            "sources": source_list(["plfs2324", "hces2223", "census2011"]),
            "occupation": a["id"], "tiers": tiers,
        })

    for c in raw()["category_priors"]:
        topic = store.topic_map().get(c["topic_id"], {})
        out.append({
            "id": f"cat:{c['topic_id']}", "type": "category", "dimension": "category",
            "title": f"{topic.get('label', c['topic_id'])} · category prior",
            "body": (
                f"{c['penetration_note']} Price sensitivity {c['price_sensitivity']:.0%}; "
                f"status signal {c['status_signal']:.0%}; supply constraint {c['supply_constraint']:.0%}; "
                f"trust barrier {c['trust_barrier']:.0%}; peer effect {c['peer_effect']:.0%}."
            ),
            "value": f"{c['trust_barrier']:.0%}", "unit": "trust barrier", "geo": "India",
            "year": 2025, "confidence": "modelled",
            "tags": [c["topic_id"], topic.get("category", "").lower(), "category", "price", "trust", "supply"],
            "source_ids": c["source_ids"], "sources": source_list(c["source_ids"]),
            "topic_id": c["topic_id"],
        })

    for n in raw()["norms"]:
        out.append({
            "id": f"norm:{n['id']}", "type": "norm", "dimension": "norms",
            "title": n["claim"], "body": f"{n['detail']} Effect: {n['effect']}",
            "value": "norm", "unit": "", "geo": "India", "year": 2025,
            "confidence": "medium", "tags": n["tiers"] + n["regions"] + ["norm", "culture", "behaviour"],
            "source_ids": n["source_ids"], "sources": source_list(n["source_ids"]),
            "tiers": n["tiers"], "regions": n["regions"],
        })

    return out


@lru_cache(maxsize=1)
def corpus_chunks() -> list[dict]:
    path = CORPUS / "chunks.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


@lru_cache(maxsize=1)
def all_nodes() -> list[dict]:
    nodes = [_norm_fact(f) for f in facts()] + derived_nodes()
    for ch in corpus_chunks():
        nodes.append({
            "id": ch.get("id", ""), "type": "document", "dimension": ch.get("dimension", "document"),
            "title": ch.get("title", "Ingested document"), "body": ch.get("text", ""),
            "value": ch.get("source", ""), "unit": "", "geo": ch.get("geo", "India"),
            "year": ch.get("year"), "confidence": ch.get("confidence", "medium"),
            "tags": ch.get("tags", []), "source_ids": [ch.get("source_id", "")],
            "sources": [s for s in [sources().get(ch.get("source_id", ""))] if s],
        })
    return nodes


def _score(query_tokens: list[str], node: dict) -> float:
    if not query_tokens:
        return 0.0
    title = set(_tok(node.get("title", "")))
    body = set(_tok(node.get("body", "")))
    tags = set(_tok(" ".join(node.get("tags", []))))
    score = 0.0
    for q in query_tokens:
        if q in title:
            score += 3.0
        if q in tags:
            score += 2.2
        if q in body:
            score += 0.7
        if q in node.get("geo", "").lower():
            score += 1.8
    # small priors for inspectable, high-confidence nodes
    score += {"fact": .4, "category": .3, "state": .25, "norm": .2}.get(node.get("type"), 0)
    if node.get("confidence") == "high":
        score += .2
    return score


def search(q: str = "", dimension: str | None = None, type: str | None = None, limit: int = 20) -> list[dict]:
    toks = _tok(q)
    rows = all_nodes()
    if dimension:
        rows = [r for r in rows if r.get("dimension") == dimension]
    if type:
        rows = [r for r in rows if r.get("type") == type]
    if toks:
        scored = [(n, _score(toks, n)) for n in rows]
        scored = [(n, s) for n, s in scored if s > 0]
        scored.sort(key=lambda x: (-x[1], -(x[0].get("year") or 0)))
        return [{**n, "score": round(s, 2)} for n, s in scored[:limit]]
    return rows[:limit]


def dimensions() -> list[dict]:
    c = Counter(n.get("dimension", "context") for n in all_nodes())
    return [{"id": k, "count": v} for k, v in sorted(c.items(), key=lambda kv: -kv[1])]


def coverage() -> dict:
    nodes = all_nodes()
    srcs = list(sources().values())
    types = Counter(n.get("type") for n in nodes)
    years = [n.get("year") for n in nodes if isinstance(n.get("year"), int)]
    conf = Counter(n.get("confidence") for n in nodes)
    cited_sources = Counter()
    for n in nodes:
        for sid in n.get("source_ids", []):
            cited_sources[sid] += 1
    return {
        "version": raw().get("version"),
        "built": raw().get("built"),
        "scope_note": raw().get("scope_note"),
        "sources": len(srcs),
        "facts": len(raw()["facts"]),
        "regions": len(raw()["regions"]),
        "norms": len(raw()["norms"]),
        "categories": len(raw()["category_priors"]),
        "anchors": len(raw()["anchors"]),
        "derived_nodes": len(derived_nodes()),
        "document_chunks": len(corpus_chunks()),
        "nodes": len(nodes),
        "dimensions": dimensions(),
        "types": dict(types),
        "confidence": dict(conf),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "orphan_sources": [s["id"] for s in srcs if cited_sources[s["id"]] == 0],
        "sources_by_type": dict(Counter(s["type"] for s in srcs)),
    }


def region_for_state(state: str) -> dict | None:
    s = state_index().get(state)
    return region_map().get(s["region"]) if s else None


def category_prior(topic_id: str) -> dict:
    return category_priors().get(topic_id) or category_priors().get("generic") or {}


def anchor(topic_id: str) -> dict:
    return anchors().get(topic_id) or anchors().get("generic") or {}


def _tier_match(node: dict, tier: int) -> bool:
    ts = node.get("tiers")
    if not ts:
        return False
    return str(tier) in [str(x) for x in ts]


def _region_match(node: dict, region: str) -> bool:
    rs = node.get("regions")
    if not rs:
        return False
    return region in rs


@lru_cache(maxsize=4096)
def _context_key(state: str, region: str, tier: int, occ: str, cat: str, tid: str,
                 caste: str, religion: str, gender: str, limit: int) -> tuple:
    toks = _tok(" ".join([state, region, occ, cat, tid, caste, religion, gender]))
    cands: list[tuple[float, dict, str]] = []
    for n in all_nodes():
        if n.get("type") == "document":
            continue
        s = _score(toks, n) * .35
        why = []
        if n.get("state") == state:
            s += 4; why.append(f"same state ({state})")
        if n.get("region") == region:
            s += 2; why.append(f"same region ({region})")
        if n.get("topic_id") == tid:
            s += 4; why.append("same category")
        if n.get("type") == "category" and tid in n.get("tags", []):
            s += 2; why.append("category prior")
        if _tier_match(n, tier):
            s += 1.2; why.append(f"tier {tier}")
        if _region_match(n, region):
            s += 1.0; why.append("regional norm")
        if occ and occ in n.get("tags", []):
            s += 1.6; why.append("occupation")
        if n.get("type") == "fact" and n.get("dimension") in ("income", "consumption", "digital", "gender", "caste", "religion", "supply", "festival"):
            s += .5
        if s > 0:
            cands.append((s, n, "; ".join(why) or "topical match"))
    cands.sort(key=lambda x: -x[0])
    out: list[dict] = []
    seen_dims = Counter()
    for sc, n, why in cands:
        # diversify: no more than two of the same dimension
        if seen_dims[n.get("dimension")] >= 2:
            continue
        seen_dims[n.get("dimension")] += 1
        out.append(citation(n, why))
        if len(out) >= limit:
            break
    return tuple(out)


def context_for_agent(agent: dict, topic: dict, limit: int = 3) -> list[dict]:
    """Return the most relevant, inspectable context for this citizen.

    The ranking is explicit: state > region > category > tier/occupation >
    identity/norm. The returned `why` explains why the node was retrieved.
    Results are cached by the structural key, so calibration loops do not
    re-score the same citizen profile thousands of times.
    """
    key = (
        agent.get("state", ""), agent.get("region", ""), int(agent.get("tier", 4)),
        agent.get("occupation_id", ""), topic.get("category", ""), topic.get("id", "generic"),
        agent.get("caste_group", ""), agent.get("religion", ""), agent.get("gender", ""), int(limit),
    )
    return list(_context_key(*key))


def prior(agent: dict, topic: dict) -> dict:
    """Small, bounded nudges from the context layer.

    These do not replace the agent's traits; they encode the part of the
    environment the agent cannot choose: state connectivity, category supply,
    identity-linked access and regional norms.
    """
    st = state_index().get(agent.get("state", ""), {})
    cp = category_prior(topic.get("id", "generic"))
    reg = region_for_state(agent.get("state", "")) or {}
    internet = float(st.get("internet_pct", 55)) / 100
    urban = float(st.get("urban_pct", 31)) / 100
    supply = float(cp.get("supply_constraint", .5))
    trust_barrier = float(cp.get("trust_barrier", .5))
    peer = float(cp.get("peer_effect", .5))
    price_sens = float(cp.get("price_sensitivity", .5))
    status = float(cp.get("status_signal", .5))

    # identity-linked access frictions (structural, not essentialist)
    gender_gap = .035 if agent.get("gender") == "female" else 0.0
    caste_gap = .02 if agent.get("caste_group") in ("SC", "ST") else 0.0
    rural_gap = .03 if int(agent.get("tier", 4)) >= 3 else 0.0

    return {
        "awareness": round((internet - .55) * .06 - supply * .02 - gender_gap * .4, 4),
        "risk": round(trust_barrier * .05 + supply * .035 + rural_gap * .25, 4),
        "price": round(price_sens * .035 + caste_gap * .3, 4),
        "social": round(peer * .045 + urban * .01, 4),
        "trust": round(-trust_barrier * .04 + internet * .02, 4),
        "status": round(status * .025, 4),
        "citations": context_for_agent(agent, topic, 3),
        "category": cp,
        "region": reg.get("id"),
    }


def bundle(topic: dict, limit: int = 6) -> dict:
    """Topic-level context bundle used by the report and the UI."""
    cp = category_prior(topic.get("id", "generic"))
    anc = anchor(topic.get("id", "generic"))
    rows = search(topic.get("label", "") + " " + topic.get("category", ""), limit=limit)
    # ensure the category prior and an income anchor are present
    cat = next((n for n in all_nodes() if n.get("topic_id") == topic.get("id")), None)
    if cat and not any(r["id"] == cat["id"] for r in rows):
        rows.insert(0, cat)
    return {
        "topic_id": topic.get("id"),
        "prior": cp,
        "anchor": anc,
        "facts": [citation(r, "topic context") for r in rows[:limit]],
        "coverage": {
            "sources": len(cp.get("source_ids", [])),
            "confidence": "modelled",
        },
    }


def audit() -> dict:
    """Integrity checks for the context layer."""
    checks = []
    srcs = sources()
    referenced = Counter()
    broken = []
    for f in raw()["facts"]:
        for sid in f.get("source_ids", []):
            referenced[sid] += 1
            if sid not in srcs:
                broken.append({"fact": f["id"], "missing_source": sid})
    dupes = [k for k, v in Counter(f["id"] for f in raw()["facts"]).items() if v > 1]
    stale = [f["id"] for f in raw()["facts"] if isinstance(f.get("year"), int) and f["year"] < 2012]
    stale_share = len(stale) / max(1, len(raw()["facts"]))
    low = [f["id"] for f in raw()["facts"] if f.get("confidence") == "low"]
    checks.append({"id": "sources_resolve", "ok": not broken, "detail": f"{len(broken)} unresolved source references", "items": broken[:8]})
    checks.append({"id": "no_duplicate_facts", "ok": not dupes, "detail": f"{len(dupes)} duplicate fact ids", "items": dupes[:8]})
    checks.append({"id": "source_coverage", "ok": len(referenced) >= max(1, int(len(srcs) * .55)), "detail": f"{len(referenced)}/{len(srcs)} sources used", "items": []})
    checks.append({"id": "fact_recency", "ok": stale_share <= .25, "detail": f"{len(stale)}/{len(raw()['facts'])} facts predate 2012 ({stale_share:.0%}); structural baselines are allowed", "items": stale[:8]})
    checks.append({"id": "low_confidence_flagged", "ok": True, "detail": f"{len(low)} low-confidence facts are labelled", "items": low[:8]})
    checks.append({"id": "anchors_link_topics", "ok": all(a["topic_id"] in store.topic_map() for a in raw()["anchors"]), "detail": "every calibration anchor maps to a topic pack", "items": []})

    state_cover = len({n.get("state") for n in derived_nodes() if n.get("state")})
    checks.append({"id": "state_coverage", "ok": state_cover >= 30, "detail": f"{state_cover} states/UTs represented", "items": []})
    return {
        "ok": all(c["ok"] for c in checks),
        "checks": checks,
        "coverage": coverage(),
    }


def stats_for_ui() -> dict:
    cov = coverage()
    return {
        "coverage": cov,
        "regions": [
            {k: r[k] for k in ("id", "name", "states", "summary", "consumption", "gender", "status", "constraints", "culture", "source_ids")}
            for r in regions()
        ],
        "sources": list(sources().values()),
        "anchors": raw()["anchors"],
        "category_priors": raw()["category_priors"],
        "audit": audit(),
    }
