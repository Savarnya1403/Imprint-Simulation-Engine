"""Division-level adoption analytics + TimesFM alignment.

The engine simulates individuals; this module answers the marketer's
question: across which divisions does the idea actually move, where does
it stall, and how does each division's curve line up with the TimesFM
market trend?

All divisions are computed from the same run (no re-simulation), so the
numbers are exactly reconcilable: segment adopted counts sum to the
reported total. Small groups (n < 20) are flagged, not hidden.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

import numpy as np

DIVISION_AXES = [
    ("tier", lambda a: f"Tier {a['tier']}"),
    ("region", lambda a: a.get("region", "")),
    ("settlement", lambda a: a.get("settlement", "")),
    ("occupation", lambda a: a.get("occupation", "")),
    ("occupation_id", lambda a: a.get("occupation_id", "")),
    ("occupation_category", lambda a: a.get("category", "")),
    ("state", lambda a: a.get("state", "")),
    ("religion", lambda a: a.get("religion", "")),
    ("caste_group", lambda a: a.get("caste_group", "")),
    ("ideology", lambda a: a.get("ideology", "")),
    ("thought_process", lambda a: a.get("thought_process", "")),
    ("economic_status", lambda a: a.get("economic_status", "")),
    ("education_band", lambda a: a.get("education_band", "")),
    ("age_band", lambda a: a.get("age_band", "")),
    ("gender", lambda a: a.get("gender", "")),
    ("personality_cluster", lambda a: a.get("personality_cluster", "")),
    ("language", lambda a: a.get("language", "")),
]

MIN_N = 20


def _corr(x: list[float], y: list[float]) -> float:
    if len(x) < 3 or len(y) != len(x):
        return 0.0
    try:
        xa = np.asarray(x, dtype=float)
        ya = np.asarray(y, dtype=float)
        if float(np.std(xa)) < 1e-9 or float(np.std(ya)) < 1e-9:
            return 0.0
        v = float(np.corrcoef(xa, ya)[0, 1])
        return 0.0 if not np.isfinite(v) else v
    except Exception:
        return 0.0


def _median_adopt_day(agents_idx: list[int], adopt_day: np.ndarray) -> float | None:
    days = [int(adopt_day[i]) for i in agents_idx if adopt_day[i] > 0]
    if not days:
        return None
    return float(statistics.median(days))


def division_report(
    agents: list[dict],
    adopted: np.ndarray,
    rejected: np.ndarray,
    rejection_reason: list,
    addressable: np.ndarray,
    adopt_day: np.ndarray,
    timeline: list[dict],
) -> dict:
    n = len(agents)
    overall_adopt = float(adopted.mean()) if n else 0.0
    total_addr = int(addressable.sum()) if hasattr(addressable, "sum") else 0
    overall_median_day = None
    all_days = [int(d) for d in adopt_day if d > 0] if adopt_day is not None else []
    if all_days:
        overall_median_day = float(statistics.median(all_days))
    market_trend = [float(t.get("market_trend", 0.0)) for t in (timeline or [])]

    axes: dict[str, list[dict]] = {}
    for key, fn in DIVISION_AXES:
        groups: dict[str, list[int]] = defaultdict(list)
        for i, a in enumerate(agents):
            try:
                label = str(fn(a))
            except Exception:
                label = ""
            if label:
                groups[label].append(i)
        rows = []
        for label, idxs in groups.items():
            idx = np.asarray(idxs, dtype=int)
            gn = len(idxs)
            g_addr = int(addressable[idx].sum()) if addr_is_array(addressable) else gn
            g_adopted = int(adopted[idx].sum())
            g_rejected = int(rejected[idx].sum())
            addr_rate = (g_addr / gn) if gn else 0.0
            adopt_rate = (g_adopted / gn) if gn else 0.0
            conv = (g_adopted / g_addr) if g_addr else 0.0
            rej_rate_addr = (g_rejected / g_addr) if g_addr else 0.0
            mean_intent = _mean([float(agents[i].get("intent", 0)) for i in idxs])
            mean_stance = _mean([float(agents[i].get("stance", 0)) for i in idxs])
            mean_aware = _mean([float(agents[i].get("awareness", 0)) for i in idxs])
            med_day = _median_adopt_day(idxs, np.asarray(adopt_day))
            lead = round(med_day - overall_median_day, 1) if (med_day is not None and overall_median_day is not None) else None
            share = (g_adopted / max(1, int(adopted.sum()))) if int(adopted.sum()) else 0.0
            size_share = gn / max(1, n)
            lift = (conv / max(1e-9, (float(adopted.sum()) / max(1, total_addr)))) if total_addr else 0.0
            # segment cumulative curve vs market trend
            seg_curve = _segment_curve(idxs, np.asarray(adopt_day), len(timeline or []))
            corr = _corr(seg_curve, market_trend[: len(seg_curve)]) if seg_curve and market_trend else 0.0
            # top rejection reason in this group
            reasons = Counter(rejection_reason[i] for i in idxs if rejection_reason[i])
            top_rej = reasons.most_common(1)[0][0] if reasons else None
            top_rej_n = reasons.most_common(1)[0][1] if reasons else 0
            # top media in group
            media = Counter(p for i in idxs for p in (agents[i].get("media") or []))
            top_media = [p for p, _ in media.most_common(3)]
            rows.append(
                {
                    "label": label,
                    "n": gn,
                    "size_share": round(size_share, 4),
                    "addressable": g_addr,
                    "addressable_rate": round(addr_rate, 4),
                    "adopted": g_adopted,
                    "adoption_rate": round(adopt_rate, 4),
                    "conversion": round(conv, 4),
                    "rejected": g_rejected,
                    "rejection_rate": round(rej_rate_addr, 4),
                    "mean_intent": round(mean_intent, 3),
                    "mean_stance": round(mean_stance, 3),
                    "mean_awareness": round(mean_aware, 3),
                    "median_adopt_day": round(med_day, 1) if med_day is not None else None,
                    "lead_days": lead,
                    "share_of_adopters": round(share, 4),
                    "lift": round(lift, 2),
                    "market_corr": round(corr, 3),
                    "top_rejection": top_rej,
                    "top_rejection_n": top_rej_n,
                    "top_media": top_media,
                    "small": gn < MIN_N,
                }
            )
        rows.sort(key=lambda r: -r["conversion"])
        axes[key] = rows

    # Cross-division leaders: highest conversion with non-trivial size.
    # occupation_id / language are exact projections of occupation/state;
    # keeping them would double-count the same people as "leaders".
    leaders = []
    for key, rows in axes.items():
        if key in ("occupation_id", "language", "occupation"):
            # occupation itself is kept; its two projections are not.
            if key in ("occupation_id", "language"):
                continue
        for r in rows:
            # Require both population and addressable mass; a 1/1 conversion
            # is not a beachhead.
            if r["n"] >= max(MIN_N, int(0.03 * n)) and r["addressable"] >= 12 and r["conversion"] > 0:
                leaders.append({**r, "axis": key})
    leaders.sort(key=lambda r: (-r["conversion"], -r["n"]))
    laggards = [r for r in leaders if r["conversion"] < 0.05]
    laggards.sort(key=lambda r: (r["conversion"], -r["n"]))

    # TimesFM market shape: when does the overall curve hit half its plateau?
    curve = [float(t.get("adoption", 0)) for t in (timeline or [])]
    plateau = max(curve) if curve else 0.0
    half_day = next((i + 1 for i, v in enumerate(curve) if plateau and v >= plateau / 2), None)

    return {
        "axes": axes,
        "overall": {
            "n": n,
            "adoption_rate": round(overall_adopt, 4),
            "addressable": total_addr,
            "median_adopt_day": overall_median_day,
            "plateau": round(plateau, 4),
            "half_plateau_day": half_day,
            "market_trend_end": round(market_trend[-1], 3) if market_trend else 0.0,
        },
        "leaders": leaders[:12],
        "laggards": laggards[:8],
        "min_n": MIN_N,
        "note": (
            "Segment counts reconcile to the run totals. Groups with n < 20 are flagged "
            "small; do not over-read them. market_corr compares each segment's cumulative "
            "adoption curve with the TimesFM market-trend signal."
        ),
    }


def addr_is_array(x) -> bool:
    return hasattr(x, "sum")


def _mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else 0.0


def _segment_curve(idxs: list[int], adopt_day: np.ndarray, ndays: int) -> list[float]:
    if ndays <= 0:
        return []
    gn = max(1, len(idxs))
    days = [int(adopt_day[i]) for i in idxs if adopt_day[i] > 0]
    out = []
    for d in range(1, ndays + 1):
        out.append(sum(1 for x in days if x <= d) / gn)
    return out
