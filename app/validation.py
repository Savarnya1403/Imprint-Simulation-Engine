"""Research-grade validation battery.

Three independent kinds of evidence, all falsifiable:

1. KNOWN-ANSWER TESTS
   Analytic identities the cognitive primitives must satisfy. If prospect
   theory stops exhibiting loss aversion, or Bass stops converging to the
   market potential, the build is broken. These are unit tests with a UI.

2. REAL-SERIES BACKTEST
   Rolling-origin forecasts on the 19 category histories. Scored with MASE
   against a naive benchmark. A model that cannot beat naive on its own data
   has no business being used for a counterfactual. Reported honestly,
   including when it loses.

3. HELD-OUT CALIBRATION
   Calibrate the six behavioural parameters on half the anchor topics and
   score the other half. In-sample fit is not evidence; held-out error is.
   Expensive, so it is cached and run only when asked (`deep=1`).

Nothing here claims the simulator is true. It claims the simulator is
*checkable*, and it shows where it fails.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Any

import numpy as np

from . import cognition, forecast, store

_CACHE: dict[str, tuple[float, dict]] = {}
_LOCK = threading.Lock()
_TTL = 600.0  # seconds


def _cached(key: str, fn):
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < _TTL:
            return hit[1]
    value = fn()
    with _LOCK:
        _CACHE[key] = (now, value)
    return value


def _check(cid: str, label: str, passed: bool, detail: str,
           value: float | None = None, target: str | None = None) -> dict:
    return {
        "id": cid, "label": label, "ok": bool(passed), "detail": detail,
        "value": None if value is None else round(float(value), 4),
        "target": target,
    }


# ---------------------------------------------------------------------------
# 1. Known-answer tests
# ---------------------------------------------------------------------------

def known_answer_tests() -> dict[str, Any]:
    checks: list[dict] = []

    # --- Bass diffusion ---
    M, p, q = 1000.0, .03, .40
    far = cognition.bass_cumulative(400, M, p, q)
    checks.append(_check(
        "bass_asymptote", "Bass converges to market potential",
        abs(far - M) / M < .02,
        f"N(400)={far:.1f} vs M={M:.0f} (tol 2%)",
        abs(far - M) / M, "< 0.02",
    ))
    seq = [cognition.bass_cumulative(t, M, p, q) for t in range(1, 80)]
    mono = all(b >= a - 1e-9 for a, b in zip(seq, seq[1:]))
    checks.append(_check(
        "bass_monotone", "Cumulative adoption is non-decreasing",
        mono, f"{len(seq)} steps checked",
    ))

    # --- Prospect theory ---
    gain = cognition.prospect_value(1.0)
    loss = cognition.prospect_value(-1.0)
    ratio = loss / gain if gain else 0.0
    checks.append(_check(
        "loss_aversion", "Losses loom larger than gains (λ≈2.25)",
        abs(ratio + 2.25) < 1e-6, f"V(-1)/V(1) = {ratio:.4f}", ratio, "≈ -2.25",
    ))
    d1 = cognition.prospect_value(1.0) - cognition.prospect_value(0.0)
    d2 = cognition.prospect_value(2.0) - cognition.prospect_value(1.0)
    checks.append(_check(
        "diminishing_sensitivity", "Gains show diminishing sensitivity",
        d2 < d1, f"ΔV(0→1)={d1:.3f} > ΔV(1→2)={d2:.3f}",
    ))

    # --- Mere exposure ---
    e = [cognition.mere_exposure_bonus(i) for i in range(0, 40)]
    checks.append(_check(
        "mere_exposure_monotone", "Exposure bonus rises then saturates",
        e[0] == 0 and all(b >= a - 1e-9 for a, b in zip(e, e[1:])) and max(e) <= .3500001,
        f"bonus(0)={e[0]:.3f}, bonus(39)={e[-1]:.3f}, ceiling=0.35",
    ))

    # --- Quasi-hyperbolic discounting ---
    d0 = cognition.quasi_hyperbolic_discount(0)
    d1h = cognition.quasi_hyperbolic_discount(1)
    d2h = cognition.quasi_hyperbolic_discount(2)
    checks.append(_check(
        "present_bias", "β–δ discounting is present-biased and monotone",
        abs(d0 - 1) < 1e-9 and d1h < d0 and d2h < d1h,
        f"D(0)={d0:.3f}, D(1)={d1h:.3f}, D(2)={d2h:.3f}",
    ))

    # --- Social thresholds ---
    t_hi = cognition.social_threshold(conformity=.9, risk=.2, optimism=.7)
    t_lo = cognition.social_threshold(conformity=.1, risk=.8, optimism=.3)
    checks.append(_check(
        "threshold_bounds", "Conformity lowers the adoption threshold",
        0.05 <= t_hi < t_lo <= 0.90, f"high-conformity t={t_hi:.2f} < low t={t_lo:.2f}",
    ))
    g_lo = cognition.granovetter_gate(0.1, 0.5)
    g_hi = cognition.granovetter_gate(0.9, 0.5)
    checks.append(_check(
        "granovetter_switch", "Cascade gate rises through the threshold",
        g_lo < .1 and g_hi > .9, f"gate(0.1)={g_lo:.3f}, gate(0.9)={g_hi:.3f}",
    ))

    # --- Dual process ---
    b_lo = cognition.dual_process_blend(0)
    b_hi = cognition.dual_process_blend(100)
    checks.append(_check(
        "dual_process", "Deliberation weight rises with need for cognition",
        b_lo < b_hi and .2 <= b_lo <= .92 and .2 <= b_hi <= .92,
        f"NFC 0 → {b_lo:.2f}, NFC 100 → {b_hi:.2f}",
    ))

    # --- Trust repair ---
    g0 = -0.30
    g1 = cognition.trust_repair_step(g0, 30)
    g60 = g0
    for _ in range(60):
        g60 = cognition.trust_repair_step(g60, 30)
    checks.append(_check(
        "trust_repair", "Trust gap decays toward baseline",
        g0 < g1 < 0 and abs(g60) < abs(g0) * .2,
        f"gap day0={g0:.3f} → day1={g1:.3f} → day60={g60:.3f}",
    ))

    # --- Bootstrap ---
    rng = np.random.default_rng(7)
    sample = rng.normal(10.0, 1.0, 200)
    mean = float(np.mean(sample))
    ci = cognition.bootstrap_ci(sample.tolist(), n_boot=400)
    checks.append(_check(
        "bootstrap_ci", "Bootstrap CI brackets the sample mean",
        ci["lower"] is not None and ci["lower"] <= mean <= ci["upper"],
        f"95% CI [{ci['lower']}, {ci['upper']}] around sample mean {mean:.3f} "
        f"(population mean is 10.0; the sample mean is the right target)",
    ))

    # --- Sensitivity estimator ---
    from . import sensitivity
    rec = sensitivity.synthetic_recovery()
    checks.append(_check(
        "sensitivity_estimator",
        "Sensitivity decomposition recovers known variance shares",
        rec["ok"],
        f"y=3x₀+x₁ → estimated {rec['estimated']} (true 0.9 / 0.1 / 0.0)",
    ))

    passed = sum(1 for c in checks if c["ok"])
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "score": round(passed / max(1, len(checks)), 3),
        "note": "Analytic identities, not empirical accuracy. These catch broken maths, not a wrong model of India.",
    }


# ---------------------------------------------------------------------------
# 2. Real-series rolling-origin backtest
# ---------------------------------------------------------------------------

def _mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray) -> float:
    naive = np.mean(np.abs(np.diff(y_train))) if len(y_train) > 2 else 0.0
    if naive <= 1e-9:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / naive)


def _smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = denom > 1e-9
    if not mask.any():
        return float("nan")
    return float(np.mean(2 * np.abs(y_true[mask] - y_pred[mask]) / denom[mask]) * 100)


def _drift_forecast(train: np.ndarray, horizon: int, window: int = 12) -> np.ndarray:
    """Random walk with drift: the benchmark any trend forecast must beat."""
    d = np.diff(train[-max(2, window + 1):])
    slope = float(np.mean(d)) if len(d) else 0.0
    return train[-1] + slope * np.arange(1, horizon + 1, dtype=float)


def _direction_hit(train: np.ndarray, truth: np.ndarray, pred: np.ndarray) -> float | None:
    """Did the forecast get the direction of the 6-month move right?

    The engine consumes the forecast as a *trend signal*, not as a level
    forecast, so trend skill is the metric that matches its role.
    """
    if len(truth) < 2 or len(pred) < 1:
        return None
    actual = float(truth[-1] - train[-1])
    called = float(pred[-1] - train[-1])
    if abs(actual) < 1e-9 or abs(called) < 1e-9:
        return None
    return 1.0 if (actual > 0) == (called > 0) else 0.0


def real_series_backtest(horizon: int = 6, step: int = 6, min_train: int = 48) -> dict[str, Any]:
    """Rolling-origin forecast on every category history, scored vs naive.

    Tests both the fast surrogate and TimesFM (when loaded), because the
    engine consumes TimesFM in production. Reports level error (MASE) and
    trend skill separately: a series can be hard to level-forecast and still
    carry a usable direction signal.
    """

    def run() -> dict:
        # Force a model load attempt once: the backtest must test the layer
        # the engine actually uses, not only the surrogate.
        try:
            timesfm_loaded = forecast._load_model() is not None
        except Exception:
            timesfm_loaded = False

        rows = []
        for topic in store.topics():
            values = np.asarray((topic.get("history") or {}).get("values") or [], dtype=float)
            if len(values) < min_train + horizon + 1:
                continue
            origins = list(range(min_train, len(values) - horizon, step))
            if not origins:
                continue
            # Cap TimesFM origins per topic for runtime; spread them across time.
            if timesfm_loaded:
                picks = np.linspace(0, len(origins) - 1, min(4, len(origins)))
                tf_origins = sorted({origins[int(round(i))] for i in picks})
            else:
                tf_origins = []

            f_mase, f_dir, tf_mase, tf_dir, base_dir = [], [], [], [], []
            f_ratio, tf_ratio = [], []
            for t0 in origins:
                train, truth = values[:t0], values[t0:t0 + horizon]
                actual = float(truth[-1] - train[-1])
                if abs(actual) > 1e-9:
                    base_dir.append(1.0 if actual > 0 else 0.0)
                drift = _drift_forecast(train, horizon)
                drift_mae = float(np.mean(np.abs(truth - drift)))
                # --- surrogate (fast, deterministic) ---
                try:
                    pred = np.asarray(forecast.fast_forecast(train, horizon), dtype=float)
                except Exception:
                    pred = np.array([])
                if len(pred) == horizon and np.all(np.isfinite(pred)):
                    m = _mase(truth, pred, train)
                    if math.isfinite(m):
                        f_mase.append(m)
                    if drift_mae > 1e-9:
                        f_ratio.append(float(np.mean(np.abs(truth - pred))) / drift_mae)
                    d = _direction_hit(train, truth, pred)
                    if d is not None:
                        f_dir.append(d)
                # --- TimesFM on a capped number of origins ---
                if t0 in tf_origins:
                    try:
                        res = forecast.forecast_series(train, horizon, model="timesfm")
                        tpred = np.asarray(res.get("point", []), dtype=float)
                        engine = res.get("engine", "")
                    except Exception:
                        tpred, engine = np.array([]), "error"
                    if len(tpred) == horizon and np.all(np.isfinite(tpred)) and engine.startswith("timesfm"):
                        m = _mase(truth, tpred, train)
                        if math.isfinite(m):
                            tf_mase.append(m)
                        if drift_mae > 1e-9:
                            tf_ratio.append(float(np.mean(np.abs(truth - tpred))) / drift_mae)
                        d = _direction_hit(train, truth, tpred)
                        if d is not None:
                            tf_dir.append(d)

            if not f_mase and not tf_mase:
                continue
            rows.append({
                "topic_id": topic["id"],
                "label": topic["label"],
                "origins": max(len(f_mase), len(tf_mase)),
                "mase": round(float(np.median(f_mase)), 3) if f_mase else None,
                "mase_timesfm": round(float(np.median(tf_mase)), 3) if tf_mase else None,
                "beats_naive_share": round(sum(1 for m in f_mase if m < 1) / max(1, len(f_mase)), 3),
                "trend_hit": round(float(np.mean(f_dir)), 3) if f_dir else None,
                "trend_hit_timesfm": round(float(np.mean(tf_dir)), 3) if tf_dir else None,
                "trend_base": round(float(np.mean(base_dir)), 3) if base_dir else None,
                "trend_skill": (
                    round(float(np.mean(f_dir)) - float(np.mean(base_dir)), 3)
                    if f_dir and base_dir else None
                ),
                "vs_drift": round(float(np.median(f_ratio)), 3) if f_ratio else None,
                "vs_drift_timesfm": round(float(np.median(tf_ratio)), 3) if tf_ratio else None,
            })

        rows.sort(key=lambda r: (r["vs_drift_timesfm"] if r["vs_drift_timesfm"] is not None else 99,
                                 r["vs_drift"] if r["vs_drift"] is not None else 99))
        f_all = [r["mase"] for r in rows if r["mase"] is not None]
        tf_all = [r["mase_timesfm"] for r in rows if r["mase_timesfm"] is not None]
        f_dir_all = [r["trend_hit"] for r in rows if r["trend_hit"] is not None]
        tf_dir_all = [r["trend_hit_timesfm"] for r in rows if r["trend_hit_timesfm"] is not None]
        base_all = [r["trend_base"] for r in rows if r["trend_base"] is not None]
        skill_all = [r["trend_skill"] for r in rows if r["trend_skill"] is not None]
        ratio_all = [r["vs_drift"] for r in rows if r["vs_drift"] is not None]
        tf_ratio_all = [r["vs_drift_timesfm"] for r in rows if r["vs_drift_timesfm"] is not None]
        median_mase = round(float(np.median(f_all)), 3) if f_all else None
        median_tf = round(float(np.median(tf_all)), 3) if tf_all else None
        median_base = round(float(np.median(base_all)), 3) if base_all else None
        median_skill = round(float(np.median(skill_all)), 3) if skill_all else None
        median_ratio = round(float(np.median(ratio_all)), 3) if ratio_all else None
        median_tf_ratio = round(float(np.median(tf_ratio_all)), 3) if tf_ratio_all else None
        benchmark = median_tf_ratio if median_tf_ratio is not None else median_ratio
        return {
            "horizon": horizon,
            "step": step,
            "topics": rows,
            "n_topics": len(rows),
            "timesfm_loaded": timesfm_loaded,
            "median_mase": median_mase,
            "median_mase_timesfm": median_tf,
            "median_beats_naive_share": (
                round(float(np.median([r["beats_naive_share"] for r in rows])), 3) if rows else None
            ),
            "median_trend_hit": round(float(np.median(f_dir_all)), 3) if f_dir_all else None,
            "median_trend_hit_timesfm": round(float(np.median(tf_dir_all)), 3) if tf_dir_all else None,
            "median_trend_base": median_base,
            "median_trend_skill": median_skill,
            "median_vs_drift": median_ratio,
            "median_vs_drift_timesfm": median_tf_ratio,
            "verdict": (
                "beats a drift benchmark on the median category (still not causal)"
                if benchmark is not None and benchmark < 1.0
                else "does not beat a simple drift benchmark; the signal is a weak, "
                     "explicitly labelled prior"
            ),
            "note": (
                "MASE < 1 means the forecast beats a random walk in-sample scale. "
                "vs_drift compares absolute error to a random-walk-with-drift "
                "forecast; below 1 there is real added value. trend_skill is "
                "direction accuracy minus the always-up base rate, so monotone "
                "series cannot inflate it. Rolling-origin, no future leakage."
            ),
        }

    return _cached(f"backtest:{horizon}:{step}", run)


# ---------------------------------------------------------------------------
# 3. Held-out calibration (expensive, cached)
# ---------------------------------------------------------------------------

def held_out_calibration(budget: int = 10, n_agents: int = 180,
                         rounds: int = 22, seed: int = 11) -> dict[str, Any]:
    """Calibrate on half the anchors, score the held-out half.

    In-sample calibration can always lower a loss. The only question that
    matters is whether the tuned parameters generalise to a category the
    search never saw.
    """

    def run() -> dict:
        from . import calibration, engine

        anchors = calibration._anchor_rows()
        if len(anchors) < 4:
            return {"available": False, "note": "Need at least 4 anchors for a held-out split."}
        train = anchors[::2]
        test = anchors[1::2]
        if not test:
            return {"available": False, "note": "Split produced no held-out anchors."}

        def score(params, group):
            rows, sq, ae = [], 0.0, 0.0
            for a in group:
                try:
                    r = engine.run_simulation(
                        a["label"], n_agents=n_agents, rounds=rounds,
                        seed=seed, params=params, fast=True,
                    )
                    sim = float(r["summary"]["conversion"])
                except Exception as exc:
                    rows.append({**a, "simulated": None,
                                 "error": f"{type(exc).__name__}: {exc}"})
                    sq += 4.0
                    continue
                half = max(.05, (a["high"] - a["low"]) / 2)
                err = sim - a["target"]
                pen = (a["low"] - sim) ** 2 if sim < a["low"] else (sim - a["high"]) ** 2 if sim > a["high"] else 0.0
                sq += (err / half) ** 2 + 2.0 * pen
                ae += abs(err)
                rows.append({
                    "topic_id": a["topic_id"], "label": a["label"],
                    "target": a["target"], "low": a["low"], "high": a["high"],
                    "simulated": round(sim, 4), "error_pct_points": round(err * 100, 2),
                })
            n = max(1, len(group))
            return {"loss": round(sq / n, 4), "mae": round(ae / n, 4), "rows": rows}

        start = calibration.load_params()
        before = score(start, test)
        found = calibration._search(train, start, budget, n_agents, rounds, seed)
        after = score(found["params"], test)
        train_fit = found["evaluation"]
        improved = after["mae"] <= before["mae"] + 1e-9
        return {
            "available": True,
            "budget": budget,
            "n_agents": n_agents,
            "rounds": rounds,
            "train_topics": [a["topic_id"] for a in train],
            "test_topics": [a["topic_id"] for a in test],
            "train_loss": train_fit["loss"],
            "train_mae": train_fit["mae"],
            "heldout_before": before,
            "heldout_after": after,
            "generalises": bool(improved),
            "params": found["params"],
            "note": (
                "Held-out MAE is the honest number. If it rises after tuning, "
                "the search is fitting noise — do not adopt those parameters."
            ),
        }

    return _cached(f"holdout:{budget}:{n_agents}:{rounds}:{seed}", run)


# ---------------------------------------------------------------------------
# Public bundle
# ---------------------------------------------------------------------------

def battery(deep: bool = False) -> dict[str, Any]:
    known = known_answer_tests()
    backtest = real_series_backtest()
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "known_answer": known,
        "backtest": backtest,
        "summary": {
            "known_answer_score": known["score"],
            "known_answer_passed": f"{known['passed']}/{known['total']}",
            "median_mase": backtest["median_mase"],
            "median_mase_timesfm": backtest.get("median_mase_timesfm"),
            "forecast_beats_naive_share": backtest["median_beats_naive_share"],
            "trend_hit": backtest.get("median_trend_hit"),
            "trend_hit_timesfm": backtest.get("median_trend_hit_timesfm"),
            "trend_base": backtest.get("median_trend_base"),
            "trend_skill": backtest.get("median_trend_skill"),
            "vs_drift": backtest.get("median_vs_drift"),
            "vs_drift_timesfm": backtest.get("median_vs_drift_timesfm"),
            "forecast_verdict": backtest.get("verdict"),
        },
        "limits": [
            "Known-answer tests check the maths, not the model of India.",
            "A MASE below 1 is a low bar; it does not make the forecast causal.",
            "The level forecast may lose to a random walk; the engine uses the signal for trend only.",
            "No validation here substitutes for a real pilot with a comparison group.",
        ],
    }
    if deep:
        out["held_out"] = held_out_calibration()
    return out


__all__ = ["known_answer_tests", "real_series_backtest", "held_out_calibration", "battery"]
