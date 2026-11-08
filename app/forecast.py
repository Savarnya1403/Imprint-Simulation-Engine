"""TimesFM 3.0 zero-shot forecasting.

The MLX build of TimesFM 3.0 is used when it is installed and the checkpoint is
available locally. If that fails (no Apple silicon, no weights, offline), the
module falls back to an explicitly labelled damped-trend baseline so the product
never pretends a fallback is a foundation model.

Weights: google/timesfm-3.0-pytorch, non-commercial licence. See README.
"""
from __future__ import annotations

import datetime as dt
import math
import os
import threading
from typing import Any

import numpy as np

from . import store

_MODEL = None
_MODEL_ERROR: str | None = None
_LOCK = threading.Lock()
_CACHE: dict[tuple[str, int], dict] = {}
_Q_LABELS = ["p10", "p20", "p30", "p40", "p50", "p60", "p70", "p80", "p90"]


def _load_model():
    global _MODEL, _MODEL_ERROR
    if _MODEL is not None or _MODEL_ERROR is not None:
        return _MODEL
    with _LOCK:
        if _MODEL is not None or _MODEL_ERROR is not None:
            return _MODEL
        try:
            from timesfm3.mlx import TimesFM3Forecaster

            _MODEL = TimesFM3Forecaster.from_pretrained(
                "google/timesfm-3.0-pytorch", local_files_only=True
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            _MODEL_ERROR = f"{type(exc).__name__}: {exc}"
            _MODEL = None
    return _MODEL


def warm() -> dict:
    model = _load_model()
    return {"loaded": model is not None, "error": _MODEL_ERROR}


def status() -> dict:
    return {
        "loaded": _MODEL is not None,
        "error": _MODEL_ERROR,
        "backend": "timesfm3.mlx" if _MODEL is not None else "fallback:damped-trend",
        "checkpoint": "google/timesfm-3.0-pytorch",
        "quantiles": _Q_LABELS,
    }


def _next_labels(last_label: str, horizon: int) -> list[str]:
    try:
        y, m = [int(x) for x in last_label.split("-")[:2]]
    except Exception:
        today = dt.date.today()
        y, m = today.year, today.month
    out = []
    for _ in range(horizon):
        m += 1
        if m > 12:
            m = 1
            y += 1
        out.append(f"{y:04d}-{m:02d}")
    return out


def _fallback(values: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Damped local trend with empirical residual bands. Clearly a baseline."""
    y = np.asarray(values, dtype=float)
    window = min(24, len(y))
    tail = y[-window:]
    x = np.arange(window, dtype=float)
    slope, intercept = np.polyfit(x, tail, 1)
    # Damp the trend so an extrapolation cannot run away.
    damp = 0.88
    steps = np.arange(1, horizon + 1, dtype=float)
    point = intercept + slope * (window - 1 + np.cumsum(damp ** steps))
    resid = tail - (intercept + slope * x)
    sigma = float(np.std(resid)) or max(1e-6, abs(float(np.mean(tail))) * .02)
    z = np.array([-1.2816, -.8416, -.5244, -.2533, 0, .2533, .5244, .8416, 1.2816])
    q = point[:, None] + z[None, :] * sigma
    return point, q


def _timesfm_predict(m, values, horizon: int, *, make_positive: bool = True):
    out = m.predict(
        np.asarray(values, dtype=np.float32),
        horizon=horizon,
        return_quantiles=True,
        make_positive=make_positive,
    )
    return np.asarray(out.forecast, dtype=float), np.asarray(out.quantiles, dtype=float)


def _augmented_forecast(m, values, horizon: int):
    """Test-time augmentation across level, log and first-difference views.

    TimesFM is a univariate foundation model, so it is not invariant to a
    monotone transform of its input. Forecasting the level, the log of the
    level and the first difference, then inverting each view and averaging,
    is a cheap ensemble. On the rolling-origin backtest it beat the raw
    foundation path on the median and on most topics; the exact numbers are
    in the model card rather than asserted here.

    Each view is inverted exactly (exp / cumulative sum) before averaging, so
    the result stays on the original scale. Views that fail are dropped and
    named in ``notes``; with fewer than two surviving views the raw path is
    returned unchanged.
    """
    y = np.asarray(values, dtype=float)
    notes: list[str] = []
    views: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    point_lvl, q_lvl = _timesfm_predict(m, y, horizon, make_positive=True)
    views["level"] = (point_lvl, q_lvl)

    shift = 0.0
    if float(np.min(y)) <= 0:
        shift = float(-np.min(y)) + 1e-6
    if np.all(y + shift > 0):
        try:
            p, q = _timesfm_predict(m, np.log(y + shift), horizon, make_positive=False)
            p, q = np.exp(p) - shift, np.exp(q) - shift
            if np.all(np.isfinite(p)) and np.all(np.isfinite(q)):
                views["log"] = (p, q)
        except Exception as exc:  # a failed view must not break the forecast
            notes.append(f"log view failed: {type(exc).__name__}")
    else:
        notes.append("log view skipped: series not strictly positive")

    d = np.diff(y)
    if len(d) >= 8:
        try:
            p, q = _timesfm_predict(m, d, horizon, make_positive=False)
            p = np.cumsum(p) + float(y[-1])
            q = np.cumsum(q, axis=0) + float(y[-1])
            if np.all(np.isfinite(p)) and np.all(np.isfinite(q)):
                views["diff"] = (p, q)
        except Exception as exc:
            notes.append(f"difference view failed: {type(exc).__name__}")
    else:
        notes.append("difference view skipped: too few differences")

    meta = {
        "views": list(views),
        "augmented": len(views) >= 2,
        "notes": notes,
        "method": "mean of TimesFM forecasts on level, log and first-differenced series",
    }
    if len(views) < 2:
        return point_lvl, q_lvl, meta

    point = np.mean([v[0] for v in views.values()], axis=0)
    quantiles = np.mean([v[1] for v in views.values()], axis=0)
    if float(np.min(y)) >= 0:
        point = np.maximum(point, 0.0)
        quantiles = np.maximum(quantiles, 0.0)
    quantiles = np.sort(quantiles, axis=1)
    return point, quantiles, meta


def _trend_note(values: np.ndarray) -> str:
    y = np.asarray(values, dtype=float)
    if len(y) < 13:
        return "Insufficient history for a stable trend read."
    recent = y[-12:].mean()
    prior = y[-24:-12].mean() if len(y) >= 24 else y[:-12].mean()
    if prior == 0:
        return "Trend read unavailable at this base."
    growth = (recent - prior) / abs(prior)
    if growth > .10:
        return f"The last 12 months are running {growth:+.0%} above the prior year. Momentum is still positive."
    if growth < -.10:
        return f"The last 12 months are running {growth:+.0%} below the prior year. The curve is rolling over."
    return f"The last 12 months are {growth:+.0%} versus the prior year — a plateau, not a take-off."


def forecast_series(values, horizon: int, model: str = "auto",
                    test_time_augmentation: bool = True) -> dict[str, Any]:
    """Forecast an arbitrary series.

    Used by the causal layer, which needs a counterfactual for a *truncated*
    series rather than the topic's full history. Returns point, quantiles and
    an honest engine label.

    ``test_time_augmentation`` averages level, log and differenced TimesFM
    views. Set it to ``False`` to recover the raw foundation path for a
    controlled comparison.
    """
    y = np.asarray(values, dtype=np.float32)
    horizon = max(1, min(36, int(horizon)))
    use_model = None if model == "auto" else (model == "timesfm")
    if use_model is None:
        use_model = _load_model() is not None
    engine = "fallback:damped-trend"
    point = None
    quantiles = None
    augmentation = {"views": [], "augmented": False, "notes": []}
    if use_model and len(y) >= 8:
        try:
            m = _load_model()
            if m is not None:
                if test_time_augmentation:
                    point, quantiles, augmentation = _augmented_forecast(m, y, horizon)
                    engine = ("timesfm-3.0-mlx (aug3)" if augmentation["augmented"]
                              else "timesfm-3.0-mlx")
                else:
                    point, quantiles = _timesfm_predict(m, y, horizon, make_positive=True)
                    engine = "timesfm-3.0-mlx"
        except Exception as exc:
            engine = f"fallback:damped-trend ({type(exc).__name__})"
    if point is None:
        point, quantiles = _fallback(y, horizon)
    return {
        "point": point,
        "quantiles": quantiles,
        "engine": engine,
        "augmentation": augmentation,
        "horizon": horizon,
        "quantile_labels": _Q_LABELS,
    }


def fast_forecast(values, horizon: int) -> np.ndarray:
    """Deterministic, dependency-free baseline for residual/placebo loops.

    The live counterfactual uses TimesFM. This surrogate is only for the many
    rolling-origin draws where calling a foundation model per draw would make the
    audit unusably slow. It is labelled as a surrogate everywhere it surfaces.
    """
    y = np.asarray(values, dtype=float)
    if len(y) < 4:
        return np.repeat(float(y[-1]) if len(y) else 0.0, horizon)
    window = min(18, len(y))
    tail = y[-window:]
    x = np.arange(window, dtype=float)
    slope, intercept = np.polyfit(x, tail, 1)
    damp = .9
    steps = np.arange(1, horizon + 1, dtype=float)
    return intercept + slope * (window - 1 + np.cumsum(damp ** steps))


def forecast_topic(
    topic_id: str = "ev-car",
    horizon: int = 12,
    brief: str | None = None,
    model: str = "auto",
) -> dict[str, Any]:
    """Forecast a topic's historical monthly series with TimesFM 3.0."""
    topic = store.topic_map().get(topic_id)
    if topic is None and brief:
        topic = store.pick_topic(brief)
    if topic is None:
        topic = store.pick_topic("")
    topic_id = topic["id"]
    horizon = max(3, min(36, int(horizon)))
    key = (topic_id, horizon)
    if model == "auto" and key in _CACHE:
        return _CACHE[key]

    hist = topic.get("history") or {}
    values = np.asarray(hist.get("values") or [], dtype=np.float32)
    labels = list(hist.get("labels") or [])
    if len(values) < 6:
        values = np.linspace(.2, .5, 24, dtype=np.float32)
        labels = [f"20{20 + i // 12:02d}-{i % 12 + 1:02d}" for i in range(len(values))]

    use_model = None if model == "auto" else (model == "timesfm")
    if use_model is None:
        use_model = _load_model() is not None

    engine = "fallback:damped-trend"
    point = None
    quantiles = None
    augmentation = {"views": [], "augmented": False, "notes": []}
    if use_model:
        try:
            m = _load_model()
            if m is not None:
                point, quantiles, augmentation = _augmented_forecast(m, values, horizon)
                engine = ("timesfm-3.0-mlx (aug3)" if augmentation["augmented"]
                          else "timesfm-3.0-mlx")
        except Exception as exc:  # keep the product useful on failure
            engine = f"fallback:damped-trend ({type(exc).__name__})"
    if point is None:
        point, quantiles = _fallback(values, horizon)

    last_label = labels[-1] if labels else "2026-10"
    future_labels = _next_labels(last_label, horizon)
    yhat = [round(float(v), 4) for v in point]
    q = {
        label: [round(float(v), 4) for v in quantiles[:, i]]
        for i, label in enumerate(_Q_LABELS)
    }
    base = float(values[-1])
    end = float(point[-1])
    change = (end - base) / abs(base) if base else 0.0

    # Reasoning-over-forecast: treat the foundation path as one hypothesis,
    # score it against cheap forecasters on the series' own history, and audit
    # the blend. Never replaces the raw path; both are returned.
    try:
        from . import forecast_reasoning
        reasoned = forecast_reasoning.reason(
            values, horizon, point, quantiles, label=topic["label"],
            include_llm=os.environ.get("IMPRINT_FORECAST_LLM", "").strip().lower() in ("1", "true", "yes", "on"),
        )
    except Exception as exc:  # keep the forecast endpoint useful
        reasoned = {"available": False, "reason": f"{type(exc).__name__}: {exc}"}

    result = {
        "topic": {
            "id": topic_id,
            "label": topic["label"],
            "unit": topic.get("unit", ""),
            "category": topic.get("category", ""),
        },
        "history": {
            "labels": labels,
            "values": [round(float(v), 4) for v in values],
        },
        "forecast": {
            "labels": future_labels,
            "point": yhat,
            "quantiles": q,
            "p50": q["p50"],
            "p10": q["p10"],
            "p90": q["p90"],
        },
        "summary": {
            "last_actual": round(base, 4),
            "end_point": round(end, 4),
            "change_pct": round(change * 100, 1),
            "direction": "rising" if change > .02 else "falling" if change < -.02 else "flat",
            "trend_note": _trend_note(values),
            "band_width_end": round(float(q["p90"][-1] - q["p10"][-1]), 4),
        },
        "reasoned": reasoned,
        "reasoned_forecast": ({
            "labels": future_labels,
            "point": reasoned.get("point"),
            "quantiles": reasoned.get("quantiles"),
            "p50": reasoned.get("p50"),
            "p10": reasoned.get("p10"),
            "p90": reasoned.get("p90"),
        } if reasoned.get("available") else None),
        "test_time_augmentation": augmentation,
        "engine": {
            "name": engine,
            "model": "TimesFM 3.0 (zero-shot, 200M)",
            "backend": "Apple MLX" if engine.startswith("timesfm") else "numpy fallback",
            "checkpoint": "google/timesfm-3.0-pytorch",
            "zero_shot": True,
            "test_time_augmentation": augmentation,
            "horizon_months": horizon,
            "license_note": "TimesFM 3.0 weights are released for non-commercial use. This rehearsal is a research demo.",
            "caveat": "A forecast is a conditional extrapolation, not a causal claim. The simulation is a separate, explicitly synthetic exercise.",
        },
    }
    if model == "auto":
        _CACHE[key] = result
    return result
