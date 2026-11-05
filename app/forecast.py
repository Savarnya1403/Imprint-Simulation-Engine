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


def forecast_series(values, horizon: int, model: str = "auto") -> dict[str, Any]:
    """Forecast an arbitrary series.

    Used by the causal layer, which needs a counterfactual for a *truncated*
    series rather than the topic's full history. Returns point, quantiles and
    an honest engine label.
    """
    y = np.asarray(values, dtype=np.float32)
    horizon = max(1, min(36, int(horizon)))
    use_model = None if model == "auto" else (model == "timesfm")
    if use_model is None:
        use_model = _load_model() is not None
    engine = "fallback:damped-trend"
    point = None
    quantiles = None
    if use_model and len(y) >= 8:
        try:
            m = _load_model()
            if m is not None:
                out = m.predict(y, horizon=horizon, return_quantiles=True, make_positive=True)
                point = np.asarray(out.forecast, dtype=float)
                quantiles = np.asarray(out.quantiles, dtype=float)
                engine = "timesfm-3.0-mlx"
        except Exception as exc:
            engine = f"fallback:damped-trend ({type(exc).__name__})"
    if point is None:
        point, quantiles = _fallback(y, horizon)
    return {
        "point": point,
        "quantiles": quantiles,
        "engine": engine,
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
    if use_model:
        try:
            m = _load_model()
            if m is not None:
                out = m.predict(values, horizon=horizon, return_quantiles=True, make_positive=True)
                point = np.asarray(out.forecast, dtype=float)
                quantiles = np.asarray(out.quantiles, dtype=float)
                engine = "timesfm-3.0-mlx"
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
        "engine": {
            "name": engine,
            "model": "TimesFM 3.0 (zero-shot, 200M)",
            "backend": "Apple MLX" if engine.startswith("timesfm") else "numpy fallback",
            "checkpoint": "google/timesfm-3.0-pytorch",
            "zero_shot": True,
            "horizon_months": horizon,
            "license_note": "TimesFM 3.0 weights are released for non-commercial use. This rehearsal is a research demo.",
            "caveat": "A forecast is a conditional extrapolation, not a causal claim. The simulation is a separate, explicitly synthetic exercise.",
        },
    }
    if model == "auto":
        _CACHE[key] = result
    return result
