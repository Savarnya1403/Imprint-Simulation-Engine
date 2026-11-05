"""Parameter calibration against public anchors.

This is the "self-improving" part of Imprint, stated honestly: it is *not*
fine-tuning a foundation model. It is a bounded coordinate search over the
simulator's explicit behavioural parameters, scored against analyst ranges drawn
from public category data. Every run is persisted so the change is auditable.

The anchors are ranges, not ground truth. A good score means the rehearsal is
consistent with those ranges under this objective, not that it is correct.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import threading
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"
PATH = DATA / "calibration.json"

# name: (floor, ceiling, step as a fraction of the current value)
SPECS: dict[str, tuple[float, float, float]] = {
    "ceiling_mult": (0.55, 1.85, 0.18),
    "price_sensitivity": (0.55, 1.65, 0.15),
    "social_mult": (0.65, 1.55, 0.15),
    "trust_weight": (0.65, 1.55, 0.15),
    "hazard_mult": (0.60, 2.40, 0.20),
    "atlas_strength": (0.40, 1.60, 0.20),
}

DEFAULTS: dict[str, float] = {
    "ceiling_mult": 1.0,
    "price_sensitivity": 1.0,
    "social_mult": 1.0,
    "trust_weight": 1.0,
    "hazard_mult": 1.0,
    "atlas_strength": 1.0,
}

# One topic per category, chosen so the objective is not dominated by near
# duplicates. Each has an analyst range in atlas.json.
CALIBRATION_TOPICS = [
    "quick-commerce",
    "upi-rural",
    "ai-jobs",
    "ott",
    "premium-fmcg",
    "misinformation",
    "gig-work",
]

_LOCK = threading.Lock()


def _clamp(name: str, value: float) -> float:
    lo, hi, _ = SPECS[name]
    return round(min(hi, max(lo, float(value))), 4)


def _clean(params: dict | None) -> dict[str, float]:
    out = dict(DEFAULTS)
    for k, v in (params or {}).items():
        if k in SPECS:
            try:
                out[k] = _clamp(k, v)
            except Exception:
                pass
    return out


def _load_file() -> dict:
    if PATH.exists():
        try:
            return json.loads(PATH.read_text())
        except Exception:
            pass
    return {
        "version": "2026.11",
        "updated": None,
        "params": dict(DEFAULTS),
        "objective": None,
        "history": [],
    }


def load_params() -> dict[str, float]:
    """Parameters the engine uses. Always returns a complete, clamped dict."""
    return _clean(_load_file().get("params"))


def set_params(params: dict[str, float]) -> dict[str, float]:
    """Clamp supplied params to declared specs, persist, and return the stored set."""
    data = _load_file()
    data["params"] = _clean(params)
    from datetime import datetime, timezone
    data["updated"] = datetime.now(timezone.utc).isoformat()
    _save(data)
    return data["params"]


def _save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def _anchor_rows(topics: list[str] | None = None) -> list[dict]:
    from . import atlas, store

    ids = topics or CALIBRATION_TOPICS
    out = []
    tm = store.topic_map()
    for tid in ids:
        topic = tm.get(tid)
        a = atlas.anchor(tid)
        if not topic or not a or a.get("topic_id") != tid:
            continue
        out.append({
            "topic_id": tid,
            "label": topic["label"],
            "target": float(a["conversion"]),
            "low": float(a["low"]),
            "high": float(a["high"]),
            "basis": a.get("basis", ""),
            "source_ids": a.get("source_ids", []),
            "sources": atlas.source_list(a.get("source_ids")),
        })
    return out


def _evaluate(params: dict[str, float], anchors: list[dict], n_agents: int, rounds: int, seed: int) -> dict:
    from . import engine

    rows = []
    sq = 0.0
    abs_err = 0.0
    inside = 0
    for a in anchors:
        topic = a["label"]
        try:
            r = engine.run_simulation(
                topic, n_agents=n_agents, rounds=rounds, seed=seed,
                params=params, fast=True,
            )
            sim = float(r["summary"]["conversion"])
        except Exception as exc:  # keep the search alive on one bad topic
            rows.append({**a, "simulated": None, "error": None, "note": f"{type(exc).__name__}: {exc}"})
            sq += 4.0
            continue
        half = max(0.05, (a["high"] - a["low"]) / 2)
        err = sim - a["target"]
        penalty = 0.0
        if sim < a["low"]:
            penalty = (a["low"] - sim) ** 2
        elif sim > a["high"]:
            penalty = (sim - a["high"]) ** 2
        sq += (err / half) ** 2 + 2.0 * penalty
        abs_err += abs(err)
        if a["low"] <= sim <= a["high"]:
            inside += 1
        rows.append({
            "topic_id": a["topic_id"], "label": a["label"],
            "target": a["target"], "low": a["low"], "high": a["high"],
            "simulated": round(sim, 4), "error": round(err, 4),
            "error_pct_points": round(err * 100, 2),
            "basis": a["basis"], "sources": a["sources"],
        })
    n = max(1, len(anchors))
    return {
        "loss": round(sq / n, 4),
        "mae": round(abs_err / n, 4),
        "within_range": inside,
        "n": len(rows),
        "topics": rows,
        "params": dict(params),
    }


def _search(anchors: list[dict], start: dict[str, float], budget: int, n_agents: int, rounds: int, seed: int) -> dict:
    params = dict(start)
    best = _evaluate(params, anchors, n_agents, rounds, seed)
    evals = 1
    trace = [{"step": "start", "loss": best["loss"], "params": dict(params), "mae": best["mae"]}]

    passes = [
        {k: max(0.08, start[k] * SPECS[k][2]) for k in SPECS},
        {k: max(0.04, start[k] * SPECS[k][2] * .5) for k in SPECS},
    ]
    stop_reason = "budget"
    for pi, step in enumerate(passes):
        improved_any = False
        for name in SPECS:
            if evals >= budget:
                stop_reason = "budget"
                break
            candidates = [
                best["params"][name] - step[name],
                best["params"][name] + step[name],
            ]
            local_best = None
            for cand in candidates:
                if evals >= budget:
                    break
                trial = dict(best["params"])
                trial[name] = _clamp(name, cand)
                if abs(trial[name] - best["params"][name]) < 1e-6:
                    continue
                scored = _evaluate(trial, anchors, n_agents, rounds, seed)
                evals += 1
                if scored["loss"] < (local_best or best)["loss"] - 1e-9:
                    local_best = scored
            if local_best and local_best["loss"] < best["loss"] - 1e-9:
                best = local_best
                improved_any = True
                trace.append({
                    "step": f"pass{pi + 1}:{name}",
                    "loss": best["loss"], "mae": best["mae"], "params": dict(best["params"]),
                })
        if not improved_any:
            stop_reason = "converged"
            break
    return {
        "params": _clean(best["params"]),
        "evaluation": best,
        "evaluations": evals,
        "stop_reason": stop_reason,
        "trace": trace,
    }


def run_calibration(
    budget: int = 24,
    n_agents: int = 420,
    rounds: int = 28,
    seed: int = 11,
    topics: list[str] | None = None,
    reset: bool = False,
) -> dict[str, Any]:
    """Tune the simulator against public category ranges and persist the result."""
    budget = max(4, min(90, int(budget)))
    n_agents = max(120, min(900, int(n_agents)))
    rounds = max(12, min(48, int(rounds)))
    anchors = _anchor_rows(topics)
    if not anchors:
        raise ValueError("No calibration anchors matched the requested topics.")

    with _LOCK:
        current = dict(DEFAULTS) if reset else load_params()
        before = _evaluate(current, anchors, n_agents, rounds, seed)
        found = _search(anchors, current, budget, n_agents, rounds, seed)
        after = found["evaluation"]

        improved = after["loss"] < before["loss"] - 1e-9
        # Only adopt a change that actually improves the objective. This prevents
        # the "self-improving" loop from drifting on noise.
        final = found["params"] if improved else current
        final_eval = after if improved else before

        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        data = _load_file()
        entry = {
            "id": f"cal-{int(dt.datetime.now().timestamp())}",
            "at": now,
            "seed": seed,
            "n_agents": n_agents,
            "rounds": rounds,
            "budget": budget,
            "evaluations": found["evaluations"],
            "before": {k: v for k, v in before.items() if k != "topics"},
            "after": {k: v for k, v in final_eval.items() if k != "topics"},
            "improved": improved,
            "adopted": improved,
            "stop_reason": found["stop_reason"],
            "params": final,
            "topics": final_eval["topics"],
            "grid": {k: {"low": SPECS[k][0], "high": SPECS[k][1]} for k in SPECS},
        }
        history = [entry] + [h for h in (data.get("history") or []) if h.get("id") != entry["id"]]
        out = {
            "version": "2026.11",
            "updated": now,
            "params": final,
            "objective": {
                "name": "normalised squared error to public anchor ranges",
                "before_loss": before["loss"],
                "after_loss": final_eval["loss"],
                "before_mae": before["mae"],
                "after_mae": final_eval["mae"],
                "within_range_before": before["within_range"],
                "within_range_after": final_eval["within_range"],
                "n_topics": final_eval["n"],
            },
            "history": history[:20],
            "last_run": entry,
            "note": (
                "Parameters are tuned against analyst ranges derived from public category data. "
                "This is calibration to anchors, not causal identification and not a claim of "
                "representative accuracy. The loop only adopts a change if it lowers the objective."
            ),
        }
        _save(out)
    return status(full=True)


def status(full: bool = False) -> dict[str, Any]:
    data = _load_file()
    params = _clean(data.get("params"))
    anchors = _anchor_rows()
    last = data.get("last_run") or {}
    out = {
        "params": params,
        "defaults": DEFAULTS,
        "specs": {k: {"low": v[0], "high": v[1], "step": v[2]} for k, v in SPECS.items()},
        "updated": data.get("updated"),
        "objective": data.get("objective"),
        "note": data.get(
            "note",
            "No calibration run yet. The simulator is using its documented defaults.",
        ),
        "history": [
            {
                "id": h.get("id"), "at": h.get("at"), "improved": h.get("improved"),
                "before_loss": (h.get("before") or {}).get("loss"),
                "after_loss": (h.get("after") or {}).get("loss"),
                "params": h.get("params"),
                "evaluations": h.get("evaluations"),
            }
            for h in (data.get("history") or [])[:8]
        ],
        "anchors": [
            {
                "topic_id": a["topic_id"], "label": a["label"], "target": a["target"],
                "low": a["low"], "high": a["high"], "basis": a["basis"],
                "sources": a["sources"],
            }
            for a in anchors
        ],
        "calibration_topics": [a["topic_id"] for a in anchors],
        "provenance_note": (
            "Anchor ranges come from public industry, regulator and consulting sources. "
            "They describe category-level conversion, not a measured panel of this synthetic population."
        ),
    }
    if full:
        out["last_run"] = last
    return out
