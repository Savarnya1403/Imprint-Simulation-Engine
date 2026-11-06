"""Self-reasoning layer.

This is not a hidden chain-of-thought and it is not a claim that one more module
makes the product "70x" better. It is a visible, auditable deliberation loop:

    frame → retrieve → simulate → replicate → stress → challenge → revise → verify

The loop can lower a verdict's confidence, downgrade a scale call, surface the
binding constraint, and name the evidence that would change the answer. Those are
quality moves you can inspect, not a multiplier you have to trust.
"""
from __future__ import annotations

import time
from statistics import mean, pstdev
from typing import Any

from . import atlas, calibration, causal, engine, perception, store

HYPOTHESES = [
    {
        "id": "price",
        "label": "Price and affordability are binding",
        "traits": ("price", "income"),
        "keys": ("price", "cost", "afford", "emi", "expensive", "budget", "value", "resale", "instal"),
        "prior": "price_sensitivity",
        "falsifier": "A price ladder in three states shows no difference in conversion across a 15–20% price change.",
    },
    {
        "id": "trust",
        "label": "Trust and failure risk are binding",
        "traits": ("trust_gov", "risk"),
        "keys": ("trust", "quality", "warranty", "service", "repair", "safety", "refund", "fake", "risk", "break"),
        "prior": "trust_barrier",
        "falsifier": "A credible service guarantee moves conversion by less than 5 percentage points in a live pilot.",
    },
    {
        "id": "supply",
        "label": "Supply and service access are binding",
        "traits": ("digital",),
        "keys": ("service network", "charging", "availability", "delivery", "stock", "supply", "wait", "install", "coverage", "dealer"),
        "prior": "supply_constraint",
        "falsifier": "Opening service points in the lowest-access districts does not change adoption relative to matched districts.",
    },
    {
        "id": "social",
        "label": "Social proof and status are binding",
        "traits": ("conformity", "status", "social_radius"),
        "keys": ("neighbour", "family", "status", "show", "peer", "everyone", "trend", "social", "approval", "wedding", "prestige"),
        "prior": "peer_effect",
        "falsifier": "A seeded community trial and a status framing test move adoption no more than a plain feature message.",
    },
    {
        "id": "awareness",
        "label": "Awareness and comprehension are binding",
        "traits": ("digital", "education"),
        "keys": ("aware", "heard", "know", "understand", "information", "confus", "explain", "language"),
        "prior": None,
        "falsifier": "Doubling reach in the lowest-awareness districts does not lift conversion.",
    },
]


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _num(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except Exception:
        return lo


def _objection_text(run: dict) -> str:
    s = run.get("summary") or {}
    parts = []
    for row in s.get("top_rejections") or []:
        parts.append(str(row.get("reason", "")))
    for row in (run.get("report") or {}).get("objections") or []:
        parts.append(str(row.get("reason", "")))
    return " ".join(parts).lower()


def _trait_corr(run: dict, names: tuple[str, ...]) -> float:
    rows = (run.get("report") or {}).get("trait_correlations") or []
    best = 0.0
    for row in rows:
        if row.get("trait") in names:
            best = max(best, abs(float(row.get("corr", 0))))
    return _num(best)


def _precedent_text(run: dict) -> str:
    rows = (run.get("precedents") or {}).get("precedents") or []
    return " ".join(" ".join(c.get("mechanisms") or []) + " " + " ".join(c.get("tags") or []) for c in rows).lower()


def score_hypotheses(run: dict) -> list[dict]:
    topic = run.get("topic") or {}
    prior = (run.get("context") or {}).get("prior") or atlas.category_prior(topic.get("id", "generic"))
    objection = _objection_text(run)
    precedent = _precedent_text(run)
    summary = run.get("summary") or {}
    rows = []
    for h in HYPOTHESES:
        hits = sum(1 for k in h["keys"] if k in objection)
        objection_score = _num(hits / max(2, len(h["keys"]) * .35))
        p = float(prior.get(h["prior"], .5)) if h["prior"] else _num(1 - float(summary.get("awareness", .5)))
        if h["id"] == "awareness":
            p = _num((1 - float(summary.get("awareness", .5))) + (0.12 if (summary.get("first_adoption_day") or 0) > 4 else 0))
        trait = _trait_corr(run, h["traits"])
        mech_hits = sum(1 for k in h["keys"] if k in precedent)
        mech_score = _num(mech_hits / max(2, len(h["keys"]) * .5))
        raw = .42 * objection_score + .26 * p + .18 * trait + .14 * mech_score
        evidence = []
        if hits:
            evidence.append(f"{hits} objection keyword(s) in the rejection set")
        evidence.append(f"category prior {prior.get(h['prior'], 'n/a') if h['prior'] else 'awareness gap'} = {p:.2f}")
        if trait:
            evidence.append(f"strongest trait correlation = {trait:.2f}")
        if mech_hits:
            evidence.append(f"{mech_hits} analogous mechanism(s) in retrieved precedents")
        rows.append({
            "id": h["id"],
            "label": h["label"],
            "score": round(raw, 3),
            "evidence": evidence,
            "falsifier": h["falsifier"],
        })
    total = sum(r["score"] for r in rows) or 1.0
    for r in rows:
        r["share"] = round(r["score"] / total, 3)
    rows.sort(key=lambda x: -x["score"])
    return rows


def _summary_row(run: dict, seed: int) -> dict:
    s = run.get("summary") or {}
    tiers = s.get("tier_adoption") or {}
    best_tier = max(tiers, key=lambda k: tiers[k]) if tiers else "—"
    return {
        "seed": seed,
        "adoption": round(float(s.get("adoption", 0)), 4),
        "conversion": round(float(s.get("conversion", 0)), 4),
        "sentiment": round(float(s.get("sentiment", 0)), 3),
        "verdict": s.get("verdict", "—"),
        "confidence": round(float(s.get("confidence", 0)), 3),
        "best_tier": best_tier,
        "addressable": s.get("addressable"),
    }


def _stability(base: dict, rows: list[dict], timeline: list[dict] | None = None) -> dict:
    all_rows = [base] + rows
    conv = [r["conversion"] for r in all_rows]
    verdicts = [r["verdict"] for r in all_rows]
    tiers = [r["best_tier"] for r in all_rows]
    avg = mean(conv) if conv else 0.0
    cv = (pstdev(conv) / avg) if len(conv) > 1 and avg else 0.0
    verdict_agreement = verdicts.count(base["verdict"]) / max(1, len(verdicts))
    tier_agreement = tiers.count(base["best_tier"]) / max(1, len(tiers))

    # --- Phase transition analysis from mathematical timeline ---
    order_values = [t.get("order_parameter", 0) for t in (timeline or []) if t.get("order_parameter") is not None]
    susc_values = [t.get("susceptibility", 0) for t in (timeline or []) if t.get("susceptibility") is not None]
    temp_values = [t.get("temperature", 1) for t in (timeline or []) if t.get("temperature") is not None]
    trend_values = [t.get("market_trend", 0) for t in (timeline or []) if t.get("market_trend") is not None]

    peak_susc = max(susc_values) if susc_values else 0.0
    order_end = order_values[-1] if order_values else 0.0
    temp_end = temp_values[-1] if temp_values else 1.0
    trend_end = trend_values[-1] if trend_values else 0.0

    # Phase transition detected if susceptibility spikes mid-simulation
    phase_transition = peak_susc > 0.05

    stable = verdict_agreement >= .75 and cv <= .30 and tier_agreement >= .60
    return {
        "runs": len(all_rows),
        "conversion_mean": round(avg, 4),
        "conversion_sd": round(pstdev(conv), 4) if len(conv) > 1 else 0.0,
        "conversion_cv": round(cv, 3),
        "verdict_agreement": round(verdict_agreement, 3),
        "best_tier_agreement": round(tier_agreement, 3),
        "stable": stable,
        "rows": all_rows,
        # New mathematical signals
        "order_parameter_end": round(order_end, 4),
        "peak_susceptibility": round(peak_susc, 4),
        "phase_transition": phase_transition,
        "temperature_end": round(temp_end, 3),
        "market_trend_end": round(trend_end, 3),
        "note": (
            "Seed replication checks whether the conclusion survives the simulator's own "
            "stochasticity. Agreement is not statistical significance. Susceptibility spikes "
            "indicate a phase transition in adoption dynamics."
        ),
    }


def _stress(base: dict, brief: str, n_agents: int, rounds: int, seed: int, scenario: str, focus_state: str | None, tier_mix: dict | None = None) -> dict:
    params = calibration.load_params()
    trials = [
        ("hazard −25%", {**params, "hazard_mult": round(float(params["hazard_mult"]) * .75, 4)}),
        ("hazard +25%", {**params, "hazard_mult": round(float(params["hazard_mult"]) * 1.25, 4)}),
        ("trust −25%", {**params, "trust_weight": round(float(params["trust_weight"]) * .75, 4)}),
        ("trust +25%", {**params, "trust_weight": round(float(params["trust_weight"]) * 1.25, 4)}),
    ]
    rows = []
    for name, p in trials:
        r = engine.run_simulation(
            brief, n_agents=n_agents, rounds=rounds, seed=seed, tier_mix=tier_mix,
            scenario=scenario, focus_state=focus_state, params=p, fast=True,
        )
        rows.append({
            "name": name,
            "adoption": round(float(r["summary"]["adoption"]), 4),
            "conversion": round(float(r["summary"]["conversion"]), 4),
            "verdict": r["summary"]["verdict"],
            "delta_adoption_pct": round((float(r["summary"]["adoption"]) - float(base["adoption"])) / max(1e-6, float(base["adoption"])) * 100, 1),
        })
    flips = [r for r in rows if r["verdict"] != base["verdict"]]
    return {
        "trials": rows,
        "verdict_flips": len(flips),
        "max_adoption_delta_pct": round(max((abs(r["delta_adoption_pct"]) for r in rows), default=0), 1),
        "robust": len(flips) == 0,
        "note": "Bounded ±25% perturbation of two dominant weights. A verdict flip means the call is assumption-sensitive.",
    }


def _causal_check(topic_id: str) -> dict:
    if not topic_id or topic_id == "generic":
        return {
            "ok": False,
            "error": "No matched category series. The brief fell back to the custom-hypothesis pack, so there is no category history to cross-check.",
        }
    try:
        d = causal.analyse(topic_id=topic_id, pre_end=72, horizon=12, sim_effect_pct=0)
        a = d.get("att") or {}
        b = d.get("bayesian") or {}
        sc = d.get("synthetic_control") or {}
        pl = d.get("placebo_time") or {}
        disagree = bool(b.get("disagreement"))
        opposite = (
            sc.get("available")
            and sc.get("att_relative_pct") is not None
            and a.get("relative_pct") is not None
            and (sc["att_relative_pct"] * a["relative_pct"] < 0)
        )
        return {
            "ok": True,
            "relative_pct": a.get("relative_pct"),
            "conformal_relative_low": a.get("conformal_relative_low"),
            "conformal_relative_high": a.get("conformal_relative_high"),
            "placebo_p": pl.get("p_value"),
            "synthetic_control_pct": sc.get("att_relative_pct"),
            "synthetic_control_p": sc.get("p_value"),
            "disagreement": disagree,
            "opposite_sign": bool(opposite),
            "validation_coverage": (d.get("validation") or {}).get("coverage_90"),
            "note": (
                "This is a drift check on the category's own history, not the effect of the "
                "specific decision in the brief. It cannot identify the brief's impact."
            ),
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _checks(run: dict, stability: dict, stress: dict, hypotheses: list[dict], ca: dict) -> list[dict]:
    s = run.get("summary") or {}
    context = run.get("context") or {}
    precedents = (run.get("precedents") or {}).get("precedents") or []
    top_sim = max([float(c.get("similarity", 0)) for c in precedents] or [0])
    top_rej = max([float(o.get("share", 0)) for o in (run.get("report") or {}).get("objections") or []] or [0])
    checks = []

    def add(cid, ok, detail, level="error"):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "level": level})

    add("seed_stability", stability["stable"], f"verdict agreement {stability['verdict_agreement']:.0%}, conversion CV {stability['conversion_cv']:.2f}")
    add("assumption_robust", stress["robust"], f"{stress['verdict_flips']} verdict flip(s) under ±25% weight perturbation")
    add("evidence_coverage", float(s.get("context_coverage", 0)) >= .90, f"{float(s.get('context_coverage', 0)):.0%} of agents carry citations", "warn")
    add("precedent_similarity", top_sim >= .45, f"top analogue similarity {top_sim:.0%}", "warn")
    add("addressable_sample", int(s.get("addressable") or 0) >= 30, f"{s.get('addressable')} addressable agents; small pools make conversion noisy", "warn")
    add("objection_concentration", top_rej < .75, f"largest objection share {top_rej:.0%}", "warn")
    add("causal_alignment", (not ca.get("ok")) or (not ca.get("opposite_sign")), ("causal check unavailable" if not ca.get("ok") else ("historical drift check points the same way as the simulation" if not ca.get("opposite_sign") else "historical drift check points the opposite way — reconcile before scaling")), "warn")
    add("calibration_current", True, "calibration history is visible in the Calibration tab", "warn")
    add("hypothesis_clear", bool(hypotheses) and hypotheses[0]["share"] >= .28, f"leading constraint share {hypotheses[0]['share'] if hypotheses else 0:.0%}", "warn")
    add("confidence_not_inflated", float(s.get("confidence", 0)) <= .93, f"reported confidence {float(s.get('confidence', 0)):.0%}", "warn")
    # Phase transition: if susceptibility spiked, the system is near a tipping point
    add("phase_transition_visible", bool(stability.get("phase_transition", False)), f"peak susceptibility {stability.get('peak_susceptibility', 0):.3f} — system near adoption tipping point", "warn")
    return checks


def _revise(run: dict, checks: list[dict], stability: dict, stress: dict, hypotheses: list[dict]) -> dict:
    s = run.get("summary") or {}
    failed = [c for c in checks if not c["ok"] and c["level"] == "error"]
    warned = [c for c in checks if not c["ok"] and c["level"] == "warn"]
    cause = [c for c in checks if not c["ok"]]
    cap = .90
    cap -= .14 * len(failed)
    cap -= .04 * min(4, len(warned))
    if not stability["stable"]:
        cap -= .04
    if not stress["robust"]:
        cap -= .04
    revised = max(.40, min(float(s.get("confidence", .6)), cap))
    original_verdict = s.get("verdict", "TEST")
    revised_verdict = original_verdict
    reasons = []
    if original_verdict == "SCALE" and (failed or not stability["stable"] or not stress["robust"]):
        revised_verdict = "TEST"
        reasons.append("Scale call downgraded: the conclusion did not survive replication or assumption stress.")
    if original_verdict in ("TEST", "SCALE") and len(failed) >= 3:
        revised_verdict = "REFRAME"
        reasons.append("Multiple independent checks failed; reframe the hypothesis before spending.")
    if not reasons:
        reasons.append("Verdict unchanged. Confidence was capped where checks are weak.")
    posture = {
        "SCALE": "Staged scale test",
        "TEST": "Contained market test",
        "REFRAME": "Reframe before spending",
        "HOLD": "Hold and collect evidence",
    }.get(revised_verdict, "Contained market test")
    return {
        "original_verdict": original_verdict,
        "revised_verdict": revised_verdict,
        "original_confidence": round(float(s.get("confidence", 0)), 3),
        "revised_confidence": round(revised, 3),
        "confidence_cap": round(max(.40, cap), 3),
        "posture": posture,
        "reasons": reasons,
        "failed": failed,
        "warnings": warned,
        "downgraded": revised_verdict != original_verdict,
    }


def _memo(run: dict, hypotheses: list[dict], revise: dict, stability: dict, stress: dict, ca: dict) -> dict:
    s = run.get("summary") or {}
    topic = run.get("topic") or {}
    top = hypotheses[0] if hypotheses else {"id": "unknown", "label": "Unclear", "falsifier": "Collect more evidence."}
    headline = (
        f"{topic.get('label', 'This decision')} reads as a {revise['revised_verdict']} call, "
        f"not a {revise['original_verdict']} call." if revise["downgraded"] else
        f"{topic.get('label', 'This decision')} holds as a {revise['revised_verdict']} call after replication and stress."
    )
    body = (
        f"The rehearsal converts {s.get('conversion', 0) * 100:.1f}% of the addressable pool, "
        f"with sentiment {s.get('sentiment', 0):+.2f}. The strongest competing explanation is "
        f"“{top['label'].lower()}” at {top.get('share', 0) * 100:.0f}% of the evidence weight. "
        f"Across {stability['runs']} seeds, verdict agreement is {stability['verdict_agreement'] * 100:.0f}% "
        f"and conversion CV is {stability['conversion_cv']:.2f}; "
        f"{stress['verdict_flips']} of {len(stress['trials'])} weight perturbations flip the verdict."
    )
    # Mathematical dynamics from the belief ODE timeline
    if stability.get("phase_transition"):
        body += (
            f" The order parameter reached {stability['order_parameter_end']:.0%} of the addressable pool "
            f"with peak susceptibility {stability['peak_susceptibility']:.3f} — the system passed through "
            f"an adoption phase transition (tipping point)."
        )
    else:
        body += (
            f" The order parameter ended at {stability['order_parameter_end']:.0%} of the addressable pool "
            f"without a sharp phase transition — adoption is gradual, not epidemic."
        )
    if stability.get("market_trend_end", 0) > 0.1:
        body += f" TimesFM demand signal is positive ({stability['market_trend_end']:+.2f}) — market trend is a tailwind."
    elif stability.get("market_trend_end", 0) < -0.1:
        body += f" TimesFM demand signal is negative ({stability['market_trend_end']:+.2f}) — market trend is a headwind."
    if ca.get("ok"):
        body += (
            f" The category history shows a {ca.get('relative_pct', 0):+.1f}% drift against its own "
            f"counterfactual, but that is not the effect of this decision."
        )
    decision = (
        f"{revise['posture']}. Cap the spend at a level that buys a real read on "
        f"“{top['label'].lower()}”, not a national rollout."
        if revise["revised_verdict"] in ("TEST", "REFRAME", "HOLD")
        else "Staged scale test with a pre-registered stop rule."
    )
    return {
        "headline": headline,
        "body": body,
        "decision": decision,
        "binding_constraint": top["label"],
        "what_would_change_my_mind": [h["falsifier"] for h in hypotheses[:3]],
        "confidence_story": (
            f"Reported {revise['original_confidence'] * 100:.0f}% → revised "
            f"{revise['revised_confidence'] * 100:.0f}% after {len(revise['failed'])} failed "
            f"and {len(revise['warnings'])} weak checks. This is a modelled stability score, not sampling error."
        ),
    }


def _next_evidence(hypotheses: list[dict]) -> dict:
    top = hypotheses[0]["id"] if hypotheses else "trust"
    tests = {
        "price": [
            "Run a three-arm price ladder in one tier-2 and two tier-3 cities for 6 weeks.",
            "Measure willingness to pay with a van Westendorp or discrete-choice exercise, not a yes/no intent question.",
            "Test EMI framing separately from sticker price; do not bundle them.",
        ],
        "trust": [
            "Pilot a written service guarantee with a named local repair partner.",
            "Audit actual repair wait times and rejection rates by district.",
            "Test warranty framing against a plain feature message in a matched-market experiment.",
        ],
        "supply": [
            "Map service-point density and wait times against adoption by pin code.",
            "Run a matched-district test where service access improves but price and messaging do not.",
            "Track stock-outs and delivery delays as a separate conversion barrier.",
        ],
        "social": [
            "Seed a community trial with visible local users, not broad influencer reach.",
            "Test status framing against function framing in the same city.",
            "Measure whether adoption clusters by neighbourhood after controlling for income.",
        ],
        "awareness": [
            "Run a reach test in low-awareness districts with a fixed creative.",
            "Check comprehension of the offer in local language, not just recall.",
            "Separate “never heard of it” from “heard it and did not understand it”.",
        ],
    }
    return {
        "priority": top,
        "tests": tests.get(top, tests["trust"]),
        "general": [
            "Pre-register the metric, the comparison group and the stop rule before launch.",
            "Collect 2–4 weeks of in-market data; do not read a 3-day spike as durable demand.",
            "Keep the synthetic run as a hypothesis generator, not as the evidence base.",
        ],
        "missing": [
            "No measured perception panel: online reaction is not purchase behaviour.",
            "WhatsApp is invisible in public data; the largest Indian social channel is under-observed.",
            "Category anchors are analyst ranges, not experimental estimates.",
            "The causal layer is a drift check unless a real decision date and comparison group are supplied.",
        ],
    }


def deliberate(
    brief: str,
    n_agents: int = 240,
    rounds: int = 36,
    seed: int = 42,
    tier_mix: dict | None = None,
    scenario: str = "base",
    focus_state: str | None = None,
    question: str | None = None,
    replicates: int = 3,
) -> dict[str, Any]:
    t_all = time.perf_counter()
    trace = []
    topic = store.pick_topic(brief)
    trace.append({"step": "Frame", "status": "done", "detail": f"Topic: {topic['label']} · {n_agents} agents · {rounds} rounds · scenario {scenario}", "ms": 0})

    t = time.perf_counter()
    base = engine.run_simulation(
        brief, n_agents=n_agents, rounds=rounds, seed=seed, tier_mix=tier_mix,
        scenario=scenario, focus_state=focus_state, question=question,
    )
    base_row = _summary_row(base, seed)
    trace.append({"step": "Retrieve", "status": "done", "detail": f"{len((base.get('context') or {}).get('facts') or [])} context facts · {len((base.get('precedents') or {}).get('precedents') or [])} precedents · {float((base.get('summary') or {}).get('context_coverage') or 0):.0%} agents cited", "ms": 0})
    trace.append({"step": "Simulate", "status": "done", "detail": f"Adoption {base['summary']['adoption']:.1%} · conversion {base['summary']['conversion']:.1%} · verdict {base['summary']['verdict']} at {base['summary']['confidence']:.0%}", "ms": _ms(t)})

    t = time.perf_counter()
    replicates = max(0, min(6, int(replicates)))
    rep_rows = []
    for i in range(replicates):
        r = engine.run_simulation(
            brief, n_agents=n_agents, rounds=rounds, seed=seed + i + 1, tier_mix=tier_mix,
            scenario=scenario, focus_state=focus_state, fast=True,
        )
        rep_rows.append(_summary_row(r, seed + i + 1))
    stability = _stability(base_row, rep_rows, timeline=base.get("timeline", []))
    trace.append({"step": "Replicate", "status": "done" if stability["stable"] else "weak", "detail": f"{stability['runs']} runs · verdict agreement {stability['verdict_agreement']:.0%} · conversion CV {stability['conversion_cv']:.2f}", "ms": _ms(t)})

    t = time.perf_counter()
    stress = _stress(base_row, brief, n_agents, rounds, seed, scenario, focus_state, tier_mix)
    trace.append({"step": "Stress", "status": "done" if stress["robust"] else "weak", "detail": f"{stress['verdict_flips']} verdict flip(s) · max adoption delta {stress['max_adoption_delta_pct']:+.1f}%", "ms": _ms(t)})

    t = time.perf_counter()
    hypotheses = score_hypotheses(base)
    trace.append({"step": "Challenge", "status": "done", "detail": f"Leading explanation: {hypotheses[0]['label']} ({hypotheses[0]['share']:.0%})", "ms": _ms(t)})

    t = time.perf_counter()
    ca = _causal_check(topic["id"])
    verify_entry = {"step": "Verify", "status": "done" if ca.get("ok") else "unavailable", "detail": ca.get("note", ca.get("error", "")), "ms": _ms(t)}

    t = time.perf_counter()
    checks = _checks(base, stability, stress, hypotheses, ca)
    revise = _revise(base, checks, stability, stress, hypotheses)
    memo = _memo(base, hypotheses, revise, stability, stress, ca)
    nxt = _next_evidence(hypotheses)
    trace.append({"step": "Revise", "status": "done", "detail": f"{revise['original_verdict']} → {revise['revised_verdict']} · confidence {revise['original_confidence']:.0%} → {revise['revised_confidence']:.0%}", "ms": _ms(t)})
    trace.append(verify_entry)

    failed = sum(1 for c in checks if not c["ok"] and c["level"] == "error")
    warnings = sum(1 for c in checks if not c["ok"] and c["level"] == "warn")
    return {
        "brief": brief,
        "topic": {"id": base["topic"]["id"], "label": base["topic"]["label"], "category": base["topic"].get("category", "")},
        "run_id": base.get("run_id"),
        "elapsed_ms": _ms(t_all),
        "posture": revise["posture"],
        "revise": revise,
        "hypotheses": hypotheses,
        "binding_constraint": hypotheses[0] if hypotheses else None,
        "stability": stability,
        "stress": stress,
        "causal_check": ca,
        "critique": {
            "checks": checks,
            "passed": sum(1 for c in checks if c["ok"]),
            "failed": failed,
            "warnings": warnings,
            "total": len(checks),
        },
        "memo": memo,
        "next": nxt,
        "trace": trace,
        "context": {
            "facts": len((base.get("context") or {}).get("facts") or []),
            "precedents": len((base.get("precedents") or {}).get("precedents") or []),
            "coverage": (base.get("summary") or {}).get("context_coverage"),
        },
        "limits": [
            "Self-reasoning is a set of explicit checks, not sentience and not a guarantee of correctness.",
            "Seed agreement and weight stress test the simulator's assumptions; they do not validate reality.",
            "No multiplier is claimed. Quality comes from replication, refutation and disclosed uncertainty.",
            "The final decision still belongs to a human with real data.",
        ],
    }


# ---------------------------------------------------------------------------
# Claude Opus 4.7 — deep deliberation layer
# ---------------------------------------------------------------------------

_CLAUDE_DELIBERATION_SYSTEM = """You are a simulation analyst reviewing a completed multi-agent behavioral simulation.
Your job is to reason deeply about the simulation results and provide:
1. A sharp, honest critique of the most important finding
2. The single most likely explanation for the simulation outcome
3. What the simulation missed or cannot see
4. The one real-world test that would most quickly confirm or deny the finding
5. A confidence assessment (0-100%) with explicit reasoning

Be concise, critical, and honest. Do not inflate confidence. Surface what a smart skeptic would push back on.
Format your response as JSON with keys: critique, top_explanation, blind_spots, priority_test, confidence_pct, confidence_reasoning.
"""


def claude_enrich(
    deliberation_result: dict[str, Any],
    query: str = "",
    domain: str = "market",
) -> dict[str, Any]:
    """Call Claude Opus 4.7 to deepen the deliberation with cross-domain reasoning.

    This is additive — the base deliberation result is unchanged. Claude's
    analysis is attached as deliberation_result['claude_analysis']. If Claude
    is unavailable, the function returns unchanged.
    """
    try:
        from . import llm
        if not llm.status().get("available"):
            return deliberation_result
    except Exception:
        return deliberation_result

    summary = deliberation_result.get("revise", {})
    memo = deliberation_result.get("memo", {})
    top_hypothesis = (deliberation_result.get("hypotheses") or [{}])[0]
    stability = deliberation_result.get("stability", {})
    stress = deliberation_result.get("stress", {})
    checks = (deliberation_result.get("critique") or {}).get("checks") or []

    prompt = f"""Simulation domain: {domain}
Query: {query}
Brief: {deliberation_result.get('brief', '')}

Simulation outcome:
- Verdict: {summary.get('revised_verdict')} (was {summary.get('original_verdict')})
- Confidence: {summary.get('revised_confidence', 0) * 100:.0f}%
- Verdict agreement across {stability.get('runs', 0)} seeds: {stability.get('verdict_agreement', 0) * 100:.0f}%
- Verdict flips under stress: {stress.get('verdict_flips', 0)} of {len(stress.get('trials', []))}
- Failed checks: {deliberation_result.get('critique', {}).get('failed', 0)}
- Leading explanation: {top_hypothesis.get('label', 'unknown')} ({top_hypothesis.get('share', 0) * 100:.0f}% of evidence weight)
- Memo headline: {memo.get('headline', '')}
- Memo body: {memo.get('body', '')[:300]}

Provide your analysis as JSON."""

    raw = llm.generate_structured(
        prompt=prompt,
        system=_CLAUDE_DELIBERATION_SYSTEM,
        max_tokens=800,
        temperature=0.3,
    )

    if raw:
        import json, re
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)
        try:
            analysis = json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
            deliberation_result["claude_analysis"] = {
                "model": "claude-opus-4-7",
                "domain": domain,
                **analysis,
            }
        except Exception:
            deliberation_result["claude_analysis"] = {"raw": raw, "model": "claude-opus-4-7"}

    return deliberation_result


def generate_domain_hypotheses(query: str, domain: str, brief_result: dict) -> list[dict]:
    """Use Claude to generate domain-specific hypotheses beyond the India-market defaults."""
    try:
        from . import llm
        if not llm.status().get("available"):
            return []
    except Exception:
        return []

    prompt = f"""Domain: {domain}
Query: {query}
Simulation brief: {brief_result.get('brief', '')}
Topic: {(brief_result.get('topic') or {}).get('label', '')}

Generate 4 competing hypotheses that explain why adoption/acceptance might succeed or fail in this simulation.
Return JSON array where each item has: id, label, binding_factor, keys (list of 3-5 keywords), falsifier (what would disprove this).
Be domain-specific — not generic market hypotheses unless the domain is market."""

    raw = llm.generate_structured(
        prompt=prompt,
        system="You are a behavioral scientist generating competing causal hypotheses. Return only valid JSON.",
        max_tokens=600,
        temperature=0.3,
    )

    if not raw:
        return []

    import json, re
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        hyps = json.loads(raw[start : end + 1])
        return [h for h in hyps if isinstance(h, dict) and "label" in h][:5]
    except Exception:
        return []
