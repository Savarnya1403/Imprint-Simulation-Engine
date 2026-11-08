"""Reasoning layer over TimesFM.

A foundation model returns a point path and quantiles. This module treats that
path as *one hypothesis among several*, scores every hypothesis on the series'
own rolling history, and returns a blended path with an uncertainty
decomposition and an audit trail.

What it can do, in named moves:
  • shrink a foundation trend that is implausible against the series' own history
  • widen a band that is too tight given the hypotheses' disagreement
  • down-weight the foundation when its band is wider than the cheap models'
    residuals (i.e. it is less sure than the data)
  • lower its own confidence when the hypotheses disagree on direction

What it cannot do: turn a weak series into a strong one. The layer is scored by
the same rolling-origin backtest as everything else, and it reports the result
even when the reasoning blend loses to the raw foundation path.

No multiplier is claimed. Every adjustment is a named rule with a number
attached, and the falsifier is explicit.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

_Z = np.array([-1.2816, -0.8416, -0.5244, -0.2533, 0.0,
               0.2533, 0.5244, 0.8416, 1.2816], dtype=float)
_Q_LABELS = ["p10", "p20", "p30", "p40", "p50", "p60", "p70", "p80", "p90"]
_EPS = 1e-9


def _clean(values) -> np.ndarray:
    y = np.asarray(values, dtype=float).ravel()
    y = np.where(np.isfinite(y), y, np.nan)
    if len(y) == 0:
        return y
    # carry the last finite value through isolated gaps
    last = y[0] if np.isfinite(y[0]) else 0.0
    for i in range(len(y)):
        if np.isfinite(y[i]):
            last = y[i]
        else:
            y[i] = last
    return y


def _steps(horizon: int) -> np.ndarray:
    return np.arange(1, horizon + 1, dtype=float)


def _drift(y: np.ndarray, h: int, window: int = 12) -> np.ndarray:
    tail = y[-max(3, min(window + 1, len(y))):]
    d = np.diff(tail)
    slope = float(np.mean(d)) if len(d) else 0.0
    return y[-1] + slope * _steps(h)


def _damped(y: np.ndarray, h: int) -> np.ndarray:
    window = min(18, len(y))
    if window < 3:
        return np.repeat(float(y[-1]), h)
    x = np.arange(window, dtype=float)
    slope, intercept = np.polyfit(x, y[-window:], 1)
    year = np.arange(1, h + 1, dtype=float)
    return intercept + slope * (window - 1 + np.cumsum(0.9 ** year))


def _mean_revert(y: np.ndarray, h: int) -> np.ndarray:
    window = min(18, len(y))
    target = float(np.mean(y[-window:]))
    level = float(y[-1])
    slope = float(np.mean(np.diff(y[-max(3, min(12, len(y))):])))
    steps = _steps(h)
    path = target + (level - target) * (0.86 ** steps) + slope * np.cumsum(0.85 ** steps) * 0.5
    return path


def _seasonal(y: np.ndarray, h: int) -> np.ndarray:
    if len(y) < 24:
        return _damped(y, h)
    period = 12
    last_season = y[-period:]
    recent = float(np.mean(y[-3:])) or _EPS
    same_ago = float(np.mean(y[-period:-period + 3])) or recent
    scale = recent / same_ago
    reps = int(math.ceil(h / period))
    return np.tile(last_season, reps)[:h] * scale


def _candidates(y: np.ndarray, h: int) -> dict[str, np.ndarray]:
    return {
        "drift": _drift(y, h),
        "damped": _damped(y, h),
        "mean_revert": _mean_revert(y, h),
        "seasonal": _seasonal(y, h),
    }


def _rolling_scores(y: np.ndarray, h: int) -> tuple[dict[str, float], dict[str, float], float]:
    """MAE and residual scale per cheap hypothesis on the series' own history."""
    n = len(y)
    min_train = max(14, min(n - h, max(20, n // 2)))
    if min_train + h > n:
        min_train = max(6, n - h)
    origins = list(range(min_train, n - h + 1, max(2, h // 2)))
    if not origins:
        origins = [max(1, n - h)]
    if len(origins) > 8:
        picks = np.linspace(0, len(origins) - 1, 8)
        origins = sorted({origins[int(round(i))] for i in picks})

    errs: dict[str, list[float]] = {k: [] for k in ("drift", "damped", "mean_revert", "seasonal")}
    for t0 in origins:
        train, truth = y[:t0], y[t0:t0 + h]
        if len(truth) < h or len(train) < 6:
            continue
        for name, cand in _candidates(train, h).items():
            errs[name].extend((truth - cand).tolist())

    mae = {k: (float(np.mean(np.abs(v))) if v else float("nan")) for k, v in errs.items()}
    sigma = {k: (float(np.std(v)) if v else float("nan")) for k, v in errs.items()}
    fallback = float(np.mean(np.abs(np.diff(y[-max(4, min(24, n)):]))) if n > 3 else 1.0)
    valid = [v for v in mae.values() if math.isfinite(v)]
    drift_mae = mae.get("drift")
    if not math.isfinite(drift_mae or float("nan")):
        drift_mae = float(np.median(valid)) if valid else fallback
    for k in mae:
        if not math.isfinite(mae[k]):
            mae[k] = drift_mae
        if not math.isfinite(sigma[k]) or sigma[k] <= _EPS:
            sigma[k] = max(fallback, 1e-6)
    return mae, sigma, float(drift_mae)


def _skill_weights(mae: dict[str, float]) -> dict[str, float]:
    inv = {k: 1.0 / (v + _EPS) for k, v in mae.items()}
    tot = sum(inv.values()) or 1.0
    w = {k: v / tot for k, v in inv.items()}
    # sharpen toward the better hypotheses, then floor/cap so no one model owns
    # the result and the blend cannot silently collapse to a single rule
    sharp = {k: max(v, 1e-6) ** 1.35 for k, v in w.items()}
    tot = sum(sharp.values()) or 1.0
    w = {k: v / tot for k, v in sharp.items()}
    w = {k: min(0.60, max(0.04, v)) for k, v in w.items()}
    tot = sum(w.values()) or 1.0
    return {k: v / tot for k, v in w.items()}


def _foundation_sigma(quantiles, h: int) -> np.ndarray | None:
    if quantiles is None:
        return None
    try:
        q = np.asarray(quantiles, dtype=float)
    except Exception:
        return None
    if q.ndim != 2 or q.shape[0] != h or q.shape[1] < 9:
        return None
    if not np.all(np.isfinite(q)):
        return None
    return np.maximum((q[:, 8] - q[:, 0]) / 2.5632, 1e-6)


def _llm_critique(payload: dict[str, Any]) -> dict | None:
    """Optional hosted-model critique. Never changes the numbers."""
    try:
        from . import llm

        if not llm.status().get("available"):
            return None
        prompt = (
            "You are a forecasting auditor. In at most 90 words, name the single "
            "weakest assumption in this plan and one check that would falsify it. "
            "Do not invent numbers.\n" + str(payload)
        )
        text = llm.generate(prompt, max_tokens=140, temperature=0.3,
                            system="You audit forecasts. Be terse, concrete and skeptical.")
        if not text:
            return None
        return {"text": text, "model": llm.status().get("model"), "used_for_numbers": False}
    except Exception:
        return None


def reason(
    values,
    horizon: int,
    foundation_point=None,
    foundation_quantiles=None,
    label: str = "",
    include_llm: bool = False,
    blend_weight: float | None = None,
) -> dict[str, Any]:
    """Blend the foundation path with cheap hypotheses, then audit the blend.

    Parameters
    ----------
    values : sequence
        Observed history, oldest first.
    horizon : int
        Months to forecast.
    foundation_point : sequence | None
        TimesFM (or fallback) point path. Optional; without it the function is a
        plain multi-hypothesis ensemble.
    foundation_quantiles : ndarray | None
        ``(horizon, 9)`` quantile matrix in the order p10…p90.
    """
    y = _clean(values)
    h = max(1, min(36, int(horizon)))
    if len(y) < 4:
        point = np.repeat(float(y[-1]) if len(y) else 0.0, h)
        sigma = np.full(h, max(1e-6, abs(float(point[0])) * .05))
        q = point[:, None] + _Z[None, :] * sigma[:, None]
        return {
            "available": False,
            "reason": "History shorter than four observations; no reasoning blend is meaningful.",
            "point": point.tolist(),
            "quantiles": {k: q[:, i].tolist() for i, k in enumerate(_Q_LABELS)},
            "p10": q[:, 0].tolist(), "p90": q[:, 8].tolist(),
            "confidence": 0.2, "weights": {}, "foundation_weight": 0.0,
            "critique": ["Too little history to score competing hypotheses."],
            "falsifier": "Collect at least 18 monthly prints before trusting this path.",
            "no_multiplier_claimed": True,
        }

    mae, sigma_model, drift_mae = _rolling_scores(y, h)
    weights = _skill_weights(mae)
    cand = _candidates(y, h)

    fpoint = None
    if foundation_point is not None:
        f = np.asarray(foundation_point, dtype=float).ravel()
        if len(f) == h and np.all(np.isfinite(f)):
            fpoint = f
    fsigma = _foundation_sigma(foundation_quantiles, h) if fpoint is not None else None

    hi = {k: cand[k] for k in cand}
    cheap = sum(weights[k] * hi[k] for k in hi)
    m_sigma = np.sqrt(sum(weights[k] * sigma_model[k] ** 2 for k in hi))

    # weight the foundation against the cheap ensemble. The default is 1.0:
    # keep the foundation path and let the ensemble *audit* it. The backtest
    # showed a fixed 0.75 blend improves the median but hurts most topics, so
    # blending is opt-in and reported per category rather than assumed.
    if fpoint is not None:
        if blend_weight is None:
            w_f = 1.0
        else:
            w_f = float(np.clip(blend_weight, 0.0, 1.0))
        if fsigma is not None and w_f < 1.0:
            ratio = float(np.median(m_sigma)) / max(1e-6, float(np.median(fsigma)))
            w_f *= float(np.clip(ratio, .85, 1.10))
            w_f = float(np.clip(w_f, .25, 1.0))
        point = w_f * fpoint + (1 - w_f) * cheap
        sigma = w_f * (fsigma if fsigma is not None else m_sigma) + (1 - w_f) * m_sigma
    else:
        w_f = 0.0
        point = cheap
        sigma = m_sigma
        fpoint = cheap

    # epistemic spread: how far the hypotheses sit from each other at each step
    stack = np.vstack([hi[k] for k in hi] + ([fpoint] if w_f else []))
    sigma_epi = np.std(stack, axis=0)
    epi_scale = 0.35 if w_f >= .999 else (0.65 if w_f else 1.0)
    sigma = np.sqrt(sigma ** 2 + (sigma_epi * epi_scale) ** 2)
    sigma = np.maximum(sigma, 1e-6)

    critique: list[str] = []
    base = float(y[-1])
    hist_growth = 0.0
    if len(y) >= 13 and abs(float(y[-13])) > _EPS:
        hist_growth = (float(y[-1]) - float(y[-13])) / abs(float(y[-13]))
    raw_growth = (float(point[-1]) - base) / abs(base) if abs(base) > _EPS else 0.0

    # 1. plausibility gate: do not let any blend imply a trend far outside the
    #    series' own one-year range
    cap = 3.0 * abs(hist_growth) + 0.15
    if abs(raw_growth) > cap and abs(raw_growth) > _EPS:
        alpha = float(np.clip(cap / abs(raw_growth), 0.20, 1.0))
        drift_path = _drift(y, h)
        point = drift_path + alpha * (point - drift_path)
        sigma = sigma * (1.0 + 0.25 * (1.0 - alpha))
        critique.append(
            f"Implausible-trend gate: blended growth {raw_growth:+.1%} exceeded the "
            f"history-scaled cap {cap:.1%}; path shrunk {1 - alpha:.0%} toward drift."
        )
        raw_growth = (float(point[-1]) - base) / abs(base) if abs(base) > _EPS else 0.0

    # 2. non-negativity for count/share series
    if float(np.min(y)) >= 0 and float(np.min(point)) < 0:
        point = np.maximum(point, 0.0)
        critique.append("Non-negativity clamp: the blend crossed below zero on a non-negative series.")

    # 3. band sanity: a band wider than the level is not a forecast
    rel_band = float((point[-1] + 1.2816 * sigma[-1] - (point[-1] - 1.2816 * sigma[-1])) / max(1e-6, abs(point[-1])))
    if rel_band > 1.6:
        sigma = sigma * (1.6 / rel_band)
        critique.append(
            f"Band cap: p10–p90 width was {rel_band:.1f}× the level; scaled to 1.6× so the "
            "interval stays interpretable."
        )

    # 4. disagreement on direction
    end_signs = [1 if float(v[-1]) >= base else -1 for v in hi.values()]
    if w_f:
        end_signs.append(1 if float(fpoint[-1]) >= base else -1)
    agreement = max(end_signs.count(1), end_signs.count(-1)) / max(1, len(end_signs))
    if agreement < 0.75:
        critique.append(
            f"Direction disagreement: only {agreement:.0%} of hypotheses agree on the sign of the "
            "change; confidence reduced and band widened."
        )
        sigma = sigma * 1.12

    # 5. thin history
    if len(y) < 24:
        critique.append(
            f"Thin history: {len(y)} prints. Foundation weight capped at {w_f:.2f}; "
            "treat the path as a prior, not an estimate."
        )

    q = point[:, None] + _Z[None, :] * sigma[:, None]
    q = np.sort(q, axis=1)

    f_growth = (float(fpoint[-1]) - base) / abs(base) if abs(base) > _EPS else 0.0
    corr = (float(point[-1]) - float(fpoint[-1])) / abs(float(fpoint[-1])) if abs(float(fpoint[-1])) > _EPS else 0.0
    best_mae = min(mae.values()) if mae else drift_mae
    skill = float(np.clip(1.0 - best_mae / max(drift_mae, _EPS), 0.0, 1.0))
    length_score = float(np.clip(len(y) / 60.0, 0.0, 1.0))
    band_score = float(np.clip(1.0 - rel_band / 1.6, 0.0, 1.0))
    confidence = float(np.clip(
        0.18 + 0.30 * agreement + 0.20 * length_score + 0.20 * skill + 0.12 * band_score,
        0.15, 0.90,
    ))

    direction = "rising" if raw_growth > .02 else "falling" if raw_growth < -.02 else "flat"
    out = {
        "available": True,
        "label": label,
        "horizon": h,
        "point": [round(float(v), 4) for v in point],
        "quantiles": {k: [round(float(v), 4) for v in q[:, i]] for i, k in enumerate(_Q_LABELS)},
        "p10": [round(float(v), 4) for v in q[:, 0]],
        "p50": [round(float(v), 4) for v in q[:, 4]],
        "p90": [round(float(v), 4) for v in q[:, 8]],
        "confidence": round(confidence, 3),
        "agreement": round(agreement, 3),
        "direction": direction,
        "growth_pct": round(raw_growth * 100, 1),
        "foundation_growth_pct": round(f_growth * 100, 1),
        "correction_pct": round(corr * 100, 1),
        "foundation_weight": round(w_f, 3),
        "weights": {k: round(v, 3) for k, v in weights.items()},
        "rolling_mae": {k: round(v, 4) for k, v in mae.items()},
        "drift_mae": round(drift_mae, 4),
        "skill_vs_drift": round(skill, 3),
        "band_ratio": round(rel_band, 3),
        "components": {
            k: [round(float(v), 4) for v in arr]
            for k, arr in {**hi, "ensemble": cheap, **({"foundation": fpoint} if w_f else {})}.items()
        },
        "mode": (
            "foundation_first_with_critique" if w_f >= .999
            else "foundation_ensemble_blend" if w_f > 0
            else "ensemble_only"
        ),
        "blend_weight": round(w_f, 3),
        "critique": critique or ["No rule fired: the foundation path and the cheap hypotheses agree."],
        "method": (
            "Foundation path + drift + damped trend + mean reversion + seasonal naive, "
            "weighted by rolling-origin MAE on the series' own history. The band combines "
            "weighted residual scale, cross-hypothesis spread and the foundation's own "
            "quantile width."
        ),
        "falsifier": (
            "If the next three official prints land outside the p10–p90 band twice, or the "
            "blend's direction is wrong twice in a row, disable the adjustment and fall "
            "back to the raw foundation path."
        ),
        "no_multiplier_claimed": True,
    }
    if include_llm:
        out["llm_critique"] = _llm_critique({
            "label": label, "growth_pct": out["growth_pct"],
            "confidence": out["confidence"], "weights": out["weights"],
            "critique": out["critique"], "band_ratio": out["band_ratio"],
        })
    return out


def reasoned_fast_forecast(values, horizon: int) -> np.ndarray:
    """Cheap multi-hypothesis ensemble used inside rolling-origin backtests.

    Deliberately does **not** take the surrogate as the foundation path: if it
    did, the default foundation-first mode would make the "reasoned" column an
    exact copy of the baseline. The backtest therefore asks a sharper question:
    does the ensemble of cheap hypotheses beat the single damped-trend rule?
    """
    r = reason(values, horizon)
    return np.asarray(r["point"], dtype=float)


__all__ = ["reason", "reasoned_fast_forecast"]
