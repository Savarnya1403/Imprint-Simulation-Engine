"""GTM / marketing / sales playbook from a simulation run.

This is not a generic advice engine. Every recommendation is derived from
the run's division analytics (segments.py), rejection decomposition,
media diets, trait correlations and the TimesFM market trend. If a
segment is not in the leaders, it is not recommended as a beachhead.

The playbook always travels with its falsifiers: the observations that
would prove the recommendation wrong.
"""
from __future__ import annotations

from collections import Counter

from . import segments


def _top_media(rows: list[dict], k: int = 3) -> list[str]:
    c: Counter[str] = Counter()
    for r in rows[:5]:
        for p in r.get("top_media") or []:
            c[p] += 1
    return [p for p, _ in c.most_common(k)]


def _segment_row(div: dict, axis: str, label: str) -> dict | None:
    for r in (div.get("axes") or {}).get(axis) or []:
        if r.get("label") == label:
            return r
    return None


def playbook(run: dict) -> dict:
    div = run.get("divisions")
    if div is None and (run.get("agents") or []):
        import numpy as np

        agents = run.get("agents") or []
        div = segments.division_report(
            agents,
            np.array([bool(a.get("adopted")) for a in agents]),
            np.array([bool(a.get("rejected")) for a in agents]),
            [a.get("rejection_reason") for a in agents],
            np.array([bool(a.get("addressable")) for a in agents]),
            np.array([int(a.get("adopt_day") or -1) for a in agents]),
            run.get("timeline") or [],
        )
    if not div:
        return {"error": "No divisions available for this run."}
    summary = run.get("summary") or {}
    report = run.get("report") or {}
    topic = (run.get("topic") or {}).get("label") or "the idea"
    leaders = div.get("leaders") or []
    laggards = div.get("laggards") or []
    overall = div.get("overall") or {}

    # Beachhead: top conversions with real size, earliest median day wins ties.
    # Protected axes (religion / caste / ideology) are diagnostic only: they
    # show where trust fails, never who to target or exclude.
    PROTECTED = {"religion", "caste_group", "ideology"}
    targetable = [r for r in leaders if r.get("axis") not in PROTECTED]
    beachhead = sorted(
        [r for r in targetable if r["n"] >= max(20, int(0.03 * (overall.get("n") or 0)))],
        key=lambda r: (-r["conversion"], r.get("median_adopt_day") or 999),
    )[:3]
    nxt = sorted(
        [r for r in targetable if r not in beachhead],
        key=lambda r: -r["conversion"],
    )[:3]
    avoid = [r for r in laggards if r.get("axis") not in PROTECTED][:3]
    # Equity diagnostics: gaps across protected axes, for fixing, not targeting.
    equity = []
    for ax in ("religion", "caste_group", "ideology"):
        rows = (div.get("axes") or {}).get(ax) or []
        if rows:
            best = max(rows, key=lambda r: r["conversion"])
            worst = min(rows, key=lambda r: r["conversion"])
            equity.append(
                f"{ax.replace('_', ' ').title()}: {worst['label']} {worst['conversion'] * 100:.0f}% "
                f"vs {best['label']} {best['conversion'] * 100:.0f}% — inspect as a trust gap, not a targeting rule."
            )

    # Tiers as the spine of the rollout.
    tier_rows = (div.get("axes") or {}).get("tier") or []
    tier_sorted = sorted(tier_rows, key=lambda r: -r["conversion"])
    best_tier = tier_sorted[0]["label"] if tier_sorted else "Tier 2"
    worst_tier = tier_sorted[-1]["label"] if tier_sorted else "Tier 4"

    # Channels from leaders' media.
    channels = _top_media(leaders) or ["WhatsApp", "YouTube"]
    econ_rows = (div.get("axes") or {}).get("economic_status") or []
    econ_sorted = sorted(econ_rows, key=lambda r: -r["conversion"])
    price_read = ""
    if econ_sorted:
        top = econ_sorted[0]["label"]
        low = econ_sorted[-1]["label"]
        price_read = (
            f"Conversion concentrates in {top} (best) vs {low} (weakest). "
            "Price the risk (warranty, resale, return path) and the cash flow (EMI / sachet), "
            "not just the sticker."
        )

    objections = report.get("objections") or []
    top_obj = objections[0]["reason"] if objections else "trust / service"

    def _fmt(r: dict) -> str:
        return (
            f"{r['label']} — {r['conversion'] * 100:.0f}% converted "
            f"({r['adopted']}/{r['addressable']} addressable, n={r['n']})"
            + (f", median day {r['median_adopt_day']:.0f}" if r.get("median_adopt_day") is not None else "")
            + (f", lift {r['lift']:.1f}x" if r.get("lift") else "")
        )

    beachhead_lines = [_fmt(r) for r in beachhead] or ["No segment clears the size bar — treat as TEST, not SCALE."]
    next_lines = [_fmt(r) for r in nxt]
    avoid_lines = [
        f"{r['label']} — {r['conversion'] * 100:.0f}% converted. "
        f"{('Top blocker: ' + r['top_rejection'] + '.') if r.get('top_rejection') else ''}"
        for r in avoid
    ]

    # Messaging per beachhead segment, grounded in media + blocker.
    messages = []
    for r in beachhead[:2]:
        blocker = r.get("top_rejection") or top_obj
        media = r.get("top_media") or channels
        messages.append(
            {
                "segment": r["label"],
                "axis": r.get("axis", ""),
                "lead_message": f"Lead with the remedy for “{blocker}”, proved locally, not with a feature list.",
                "proof": f"One credible local owner + one service promise in {', '.join(media[:2])}.",
                "language": f"Local language + demo, not English-first copy (see {r['label']} media: {', '.join(media)}).",
            }
        )

    market_end = overall.get("market_trend_end", 0)
    trend_read = (
        "Tailwind: TimesFM market trend is positive at the end of the window; segments that track it "
        "(high market_corr) are the safest to scale first."
        if market_end > 0.1
        else "Headwind: TimesFM market trend is negative at the end of the window; do not mistake a "
        "category tailwind for your own traction. Prefer high market_corr segments only."
        if market_end < -0.1
        else "Flat market trend: no category wind at your back; the simulation's own social proof must carry the rollout."
    )

    plan = [
        {
            "window": "Weeks 1–2",
            "goal": f"Prove the remedy in {best_tier} only.",
            "moves": [
                f"Launch in {best_tier} with one service promise and one local owner.",
                f"Creative: remedy-first, in {' / '.join(channels[:2])}.",
                "Instrument adoption AND rejection reasons by district and occupation.",
            ],
            "metric": "Conversion of addressable + top rejection share (must fall).",
            "stop_rule": "If top rejection does not fall, reframe before spending on reach.",
        },
        {
            "window": "Weeks 3–6",
            "goal": "Expand to the next-wave segments that already convert.",
            "moves": next_lines[:2]
            or ["Extend the same playbook; do not change the promise."],
            "metric": "Segment conversion holds within ±20% of the beachhead.",
            "stop_rule": "Hold if a new wave's conversion is <50% of the beachhead's.",
        },
        {
            "window": "Weeks 7–12",
            "goal": "Reach the hard segments only if the blocker is fixed.",
            "moves": avoid_lines[:1] or ["No new segments until the blocker moves."],
            "metric": f"{worst_tier} conversion — the real forecast risk.",
            "stop_rule": "Do not fund national reach while the blocker share is above 50%.",
        },
    ]

    falsifiers = [
        "A matched-market test where the remedy alone moves conversion <5pp.",
        "A price ladder where conversion does not respond to a 15–20% change (price is not binding).",
        "Service-point density rises with no adoption lift (supply is not binding).",
        "A seeded community trial that does not cluster adoption by neighbourhood.",
        "The TimesFM market-trend segment (high market_corr) underperforms the overall curve in-market.",
    ]
    risks = [
        "WhatsApp is the largest channel but is under-observed in public data; instrument it directly.",
        "Anchors are analyst ranges, not measured panels; the playbook is a hypothesis, not a forecast.",
        "Caste, religion and ideology affect trust structurally in the model; never target by identity, always by behaviour and need.",
        "TimesFM weights are non-commercial; check before paid deployment.",
    ]

    return {
        "topic": topic,
        "verdict": summary.get("verdict", "—"),
        "adoption": overall.get("adoption_rate"),
        "conversion_note": f"Overall adoption {overall.get('adoption_rate', 0) * 100:.1f}% · addressable {overall.get('addressable', 0)} · half-plateau day {overall.get('half_plateau_day')}",
        "trend_read": trend_read,
        "beachhead": {"tier": best_tier, "lines": beachhead_lines},
        "next_wave": next_lines,
        "avoid": avoid_lines,
        "equity": equity,
        "channels": channels,
        "price_read": price_read,
        "top_blocker": top_obj,
        "messages": messages,
        "plan": plan,
        "falsifiers": falsifiers,
        "risks": risks,
        "equity_note": (
            "Divisions are used to find where the promise fails, never to exclude people. "
            "Fix the blocker; do not abandon the segment."
        ),
    }
