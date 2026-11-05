"""Causal layer: TimesFM counterfactual, conformal intervals, placebos,
synthetic control, Bayesian combination with the simulation prior, and Monte
Carlo decision distributions.

This is decision support, not identification. The module is explicit about what
is estimated, what is assumed, and what is only a prior.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np

from . import forecast, perception, store

Q = 1.2816  # 90% normal quantile, used only for a labelled approximation


def _series(topic_id: str) -> tuple[str, list[str], np.ndarray, dict]:
    topic = store.topic_map().get(topic_id)
    if not topic:
        topic = store.pick_topic("")
    hist = topic.get("history") or {}
    values = np.asarray(hist.get("values") or [], dtype=float)
    labels = list(hist.get("labels") or [])
    if len(values) < 18:
        raise ValueError("The series needs at least 18 observations for a counterfactual.")
    if len(labels) != len(values):
        labels = [f"t{i+1:02d}" for i in range(len(values))]
    return topic["id"], labels, values, topic


def _one_step_errors(y: np.ndarray, pre_end: int, max_origins: int = 24) -> np.ndarray:
    """Rolling-origin one-step errors from a fast surrogate.

    Using the foundation model for every origin would make the interval audit
    unusably slow. The surrogate is labelled; the live counterfactual uses
    TimesFM.
    """
    errs = []
    start = max(6, pre_end - max_origins)
    for t in range(start, pre_end):
        pred = forecast.fast_forecast(y[:t], 1)[0]
        errs.append(float(y[t] - pred))
    return np.asarray(errs, dtype=float)


def _rolling_cum_errors(y: np.ndarray, pre_end: int, horizon: int, max_origins: int = 20, min_train: int = 8) -> np.ndarray:
    """Cumulative h-step forecast errors from rolling origins inside the pre-period.

    This is the right object for a cumulative-effect interval: it captures the
    bias and autocorrelation that a one-step residual scaled by sqrt(h) misses.
    """
    last = pre_end - horizon
    if last < min_train:
        return np.array([])
    first = max(min_train, last - max_origins + 1)
    errs = []
    for t0 in range(first, last + 1):
        cf = forecast.fast_forecast(y[:t0], horizon)
        obs = y[t0:t0 + horizon]
        if len(obs) != horizon:
            continue
        errs.append(float(np.sum(obs - cf)))
    return np.asarray(errs, dtype=float)


def _conformal_halfwidth(y: np.ndarray, pre_end: int, horizon: int, alpha: float = .10) -> float:
    """Split-conformal-style half-width for the cumulative effect.

    Approximate by construction: rolling-origin errors are not exchangeable under
    non-stationarity, so the coverage is a diagnostic, not a guarantee.
    """
    errors = _rolling_cum_errors(y, pre_end, horizon)
    if len(errors) == 0:
        return 0.0
    # finite-sample conformal quantile
    n = len(errors)
    k = min(n, int(math.ceil((n + 1) * (1 - alpha))))
    return float(np.sort(np.abs(errors))[k - 1])


def _placebo_time(y: np.ndarray, pre_end: int, horizon: int, observed_cum: float, n: int = 12) -> dict:
    h = min(horizon, len(y) - pre_end)
    if h < 1:
        return {"p_value": None, "n": 0, "effects": [], "note": "No post-period points."}
    candidates = list(range(max(8, pre_end - 30), max(9, pre_end - h - 2)))
    if len(candidates) > n:
        # deterministic spread across the pre-period
        idx = np.linspace(0, len(candidates) - 1, n).round().astype(int)
        candidates = [candidates[i] for i in idx]
    effects = []
    for t0 in candidates:
        cf = forecast.fast_forecast(y[:t0], h)
        obs = y[t0:t0 + h]
        if len(obs) != h:
            continue
        effects.append(float(np.sum(obs - cf)))
    if not effects:
        return {"p_value": None, "n": 0, "effects": [], "note": "Insufficient pre-period for placebo dates."}
    extreme = sum(1 for e in effects if abs(e) >= abs(observed_cum))
    p = (1 + extreme) / (1 + len(effects))
    return {
        "p_value": round(p, 3),
        "n": len(effects),
        "effects": [round(e, 4) for e in effects],
        "observed": round(observed_cum, 4),
        "note": (
            "Randomisation-in-time placebo. Low power with a short series; a high "
            "p-value is not proof of no effect, and a low one is not proof of causality."
        ),
    }


def _project_simplex(v: np.ndarray) -> np.ndarray:
    u = np.sort(v)[::-1]
    css = np.cumsum(u)
    rho = np.nonzero(u * np.arange(1, len(v) + 1) > (css - 1))[0][-1]
    theta = (css[rho] - 1) / (rho + 1.0)
    return np.maximum(v - theta, 0)


def _simplex_weights(A: np.ndarray, b: np.ndarray, iters: int = 2500) -> np.ndarray:
    """Non-negative weights summing to one, via projected gradient."""
    n = A.shape[1]
    if n == 0:
        return np.array([])
    w = np.full(n, 1.0 / n)
    # Lipschitz bound of A^T A
    L = float(np.linalg.norm(A, 2) ** 2) or 1.0
    step = 1.0 / L
    for _ in range(iters):
        grad = A.T @ (A @ w - b)
        w = _project_simplex(w - step * grad)
    return w


def _synthetic_control(topic_id: str, pre_end: int, horizon: int) -> dict:
    """Augmented synthetic control using other topic series as donors.

    Donors are normalised to the treated pre-period mean. This is a robustness
    check, not a substitute for a proper donor pool of untreated regions.
    """
    _, _, y, _ = _series(topic_id)
    donors = []
    names = []
    for t in store.topics():
        if t["id"] == topic_id:
            continue
        vals = np.asarray((t.get("history") or {}).get("values") or [], dtype=float)
        if len(vals) < pre_end + 2:
            continue
        donors.append(vals[:pre_end + horizon])
        names.append(t["id"])
    if len(donors) < 3:
        return {"available": False, "note": "Not enough donor series."}
    D = np.column_stack(donors)
    m = min(len(y), D.shape[0])
    pre_end = min(pre_end, m - 1)
    h = min(horizon, m - pre_end)
    y_pre = y[:pre_end]
    D_pre = D[:pre_end]
    scale = float(np.mean(y_pre)) or 1.0
    Dn = D_pre / np.maximum(D_pre.mean(axis=0), 1e-9) * scale
    w = _simplex_weights(Dn, y_pre)
    cf_pre = Dn @ w
    cf_post = (D[pre_end:pre_end + h] / np.maximum(D_pre.mean(axis=0), 1e-9) * scale) @ w
    obs_post = y[pre_end:pre_end + h]
    att = float(np.mean(obs_post - cf_post))
    # in-space placebo: each donor as pseudo-treated
    placebo = []
    for j in range(min(8, D.shape[1])):
        others = [k for k in range(D.shape[1]) if k != j]
        if len(others) < 2:
            continue
        Dj = D[:, others]
        yj = D[:, j]
        sc = float(np.mean(yj[:pre_end])) or 1.0
        Djn = Dj[:pre_end] / np.maximum(Dj[:pre_end].mean(axis=0), 1e-9) * sc
        wj = _simplex_weights(Djn, yj[:pre_end])
        cfj = (Dj[pre_end:pre_end + h] / np.maximum(Dj[:pre_end].mean(axis=0), 1e-9) * sc) @ wj
        placebo.append(float(np.mean(yj[pre_end:pre_end + h] - cfj)))
    extreme = sum(1 for e in placebo if abs(e) >= abs(att))
    p = (1 + extreme) / (1 + len(placebo)) if placebo else None
    top = sorted(zip(names, w), key=lambda x: -x[1])[:5]
    return {
        "available": True,
        "att": round(att, 4),
        "att_relative_pct": round(att / (float(np.mean(cf_post)) or 1) * 100, 2),
        "p_value": p,
        "donors": [{"topic": n, "weight": round(float(v), 3)} for n, v in top],
        "pre_fit_mape": round(float(np.mean(np.abs((y_pre - cf_pre) / np.maximum(np.abs(y_pre), 1e-9))) * 100), 2),
        "note": "Synthetic control on category series, not untreated regions. Donor exogeneity is not guaranteed.",
    }


def _bayes(prior_mean: float, prior_sd: float, est: float, se: float) -> dict:
    prior_sd = max(1e-6, prior_sd)
    se = max(1e-6, se)
    prec = 1 / prior_sd ** 2 + 1 / se ** 2
    mean = (prior_mean / prior_sd ** 2 + est / se ** 2) / prec
    sd = math.sqrt(1 / prec)
    disagree = abs(prior_mean - est) > 2 * math.sqrt(prior_sd ** 2 + se ** 2)
    return {
        "prior_mean": round(prior_mean, 3),
        "prior_sd": round(prior_sd, 3),
        "estimate": round(est, 3),
        "estimate_se": round(se, 3),
        "posterior_mean": round(mean, 3),
        "posterior_sd": round(sd, 3),
        "disagreement": disagree,
        "note": (
            "Normal-normal combination. The simulation is a prior, not evidence. "
            "A disagreement flag means reconcile before using the posterior."
        ),
    }


def _block_bootstrap(errors: np.ndarray, horizon: int, paths: int = 600, block: int = 3) -> np.ndarray:
    if len(errors) == 0:
        return np.zeros((paths, horizon))
    e = errors - errors.mean()
    n = len(e)
    block = max(1, min(block, n))
    out = np.zeros((paths, horizon))
    for p in range(paths):
        i = 0
        while i < horizon:
            start = np.random.randint(0, max(1, n - block + 1))
            seg = e[start:start + block]
            take = min(len(seg), horizon - i)
            out[p, i:i + take] = seg[:take]
            i += take
    return out


def _npv(effect_pct: np.ndarray, baseline_value: float, margin: float, cost: float, discount: float) -> dict:
    if len(effect_pct) == 0:
        return {}
    horizon = len(effect_pct[0]) if effect_pct.ndim > 1 else len(effect_pct)
    t = np.arange(1, horizon + 1)
    disc = 1 / (1 + discount) ** t
    if effect_pct.ndim == 1:
        effect_pct = effect_pct[:, None]
    monthly = baseline_value * margin * (effect_pct / 100)
    if monthly.ndim == 1:
        monthly = monthly[None, :]
    npvs = monthly @ disc - cost
    return {
        "mean": round(float(np.mean(npvs)), 2),
        "p05": round(float(np.quantile(npvs, .05)), 2),
        "p50": round(float(np.quantile(npvs, .50)), 2),
        "p95": round(float(np.quantile(npvs, .95)), 2),
        "prob_positive": round(float(np.mean(npvs > 0)), 3),
        "cvar5": round(float(np.mean(np.sort(npvs)[:max(1, int(len(npvs) * .05))])), 2),
        "cost": cost,
        "baseline_monthly_value": baseline_value,
        "margin": margin,
        "note": "Illustrative NPV of the estimated effect. It is not a valuation and excludes competitive response.",
    }


def monte_carlo_validation(runs: int = 80, seed: int = 7) -> dict:
    """Synthetic-truth harness: does the machinery recover a known effect?

    The DGP has trend, AR(1) noise and an injected step. The counterfactual uses
    the fast surrogate, so this validates the pipeline rather than TimesFM.
    """
    rng = np.random.default_rng(seed)
    pre, h = 48, 12
    taus = np.linspace(0, .12, runs)
    est, cover, truth = [], [], []
    for tau in taus:
        t = np.arange(pre + h)
        trend = .3 + .002 * t
        noise = np.zeros(len(t))
        for i in range(1, len(t)):
            noise[i] = .55 * noise[i - 1] + rng.normal(0, .012)
        step = np.where(t >= pre, tau * (1 + (t - pre) / max(1, h)), 0)
        y = trend + noise + step
        cf = forecast.fast_forecast(y[:pre], h)
        obs = y[pre:pre + h]
        cum = float(np.sum(obs - cf))
        half = _conformal_halfwidth(y, pre, h)
        est.append(cum)
        truth.append(float(np.sum(step[pre:pre + h])))
        cover.append(abs(cum - truth[-1]) <= half)
    est = np.asarray(est)
    truth = np.asarray(truth)
    bias = float(np.mean(est - truth))
    rmse = float(np.sqrt(np.mean((est - truth) ** 2)))
    return {
        "runs": runs,
        "bias": round(bias, 4),
        "rmse": round(rmse, 4),
        "coverage_90": round(float(np.mean(cover)), 3),
        "mean_true_cumulative": round(float(np.mean(truth)), 4),
        "mean_estimate": round(float(np.mean(est)), 4),
        "note": (
            "Synthetic DGP with AR(1) noise and a known step. Validates the machinery, "
            "not whether reality matches the DGP. Coverage is approximate under non-stationarity."
        ),
    }


def analyse(
    topic_id: str = "ev-car",
    pre_end: int = 72,
    horizon: int = 12,
    sim_effect_pct: float = 0.0,
    sim_sd_pct: float = 8.0,
    baseline_value: float = 1_000_000,
    margin: float = .35,
    cost: float = 0.0,
    discount: float = .01,
) -> dict[str, Any]:
    topic_id, labels, y, topic = _series(topic_id)
    n = len(y)
    pre_end = max(18, min(int(pre_end), n - 4))
    horizon = max(3, min(int(horizon), 24))
    h = min(horizon, n - pre_end)
    if h < 3:
        raise ValueError("Need at least 3 post-period observations; reduce pre_end.")

    fc = forecast.forecast_series(y[:pre_end], h, model="auto")
    cf = np.asarray(fc["point"], dtype=float)
    q = np.asarray(fc["quantiles"], dtype=float)
    obs = y[pre_end:pre_end + h]
    effects = obs - cf
    cum = float(np.sum(effects))
    cum_obs = float(np.sum(obs))
    rel = cum / (float(np.sum(cf)) or 1) * 100
    errs = _one_step_errors(y, pre_end)
    half = _conformal_halfwidth(y, pre_end, h)
    mape = float(np.mean(np.abs(errs / np.maximum(np.abs(y[pre_end - len(errs):pre_end]), 1e-9))) * 100) if len(errs) else 0.0

    placebo = _placebo_time(y, pre_end, h, cum)
    sc = _synthetic_control(topic_id, pre_end, h)

    baseline = float(np.mean(cf)) or 1.0
    estimate_pct = rel
    se_pct = (half / (abs(cum_obs) or 1)) * 100 if cum_obs else 0.0
    se_pct = max(1.0, min(40.0, se_pct))
    bayes = _bayes(sim_effect_pct, sim_sd_pct, estimate_pct, se_pct)

    boot = _block_bootstrap(errs, h, paths=600, block=3)
    cf_paths = cf[None, :] + boot
    effect_paths = obs[None, :] - cf_paths
    cum_paths = effect_paths.sum(axis=1)
    # Add counterfactual model uncertainty from the rolling-origin cumulative
    # errors. Without this, the Monte Carlo only reflects residual noise and is
    # overconfident relative to the conformal interval.
    cum_model_err = _rolling_cum_errors(y, pre_end, h)
    if len(cum_model_err):
        rng = np.random.default_rng(12345)
        # Centre the surrogate errors: the live point estimate uses TimesFM, so
        # the fast surrogate contributes uncertainty, not a level shift.
        bias = rng.choice(cum_model_err - cum_model_err.mean(), size=len(cum_paths), replace=True)
        cum_paths = cum_paths + bias
        effect_paths = effect_paths + (bias / h)[:, None]
    rel_paths = cum_paths / np.maximum(cf_paths.sum(axis=1), 1e-9) * 100
    period_rel_paths = effect_paths / np.maximum(cf_paths, 1e-9) * 100
    npv = _npv(period_rel_paths, baseline_value, margin, cost, discount)

    observed_vs_cf = []
    for i in range(h):
        observed_vs_cf.append({
            "label": labels[pre_end + i] if pre_end + i < len(labels) else f"t+{i+1}",
            "observed": round(float(obs[i]), 4),
            "counterfactual": round(float(cf[i]), 4),
            "effect": round(float(effects[i]), 4),
            "p10": round(float(q[i, 0]), 4),
            "p90": round(float(q[i, -1]), 4),
        })

    prior = perception.prior_for_simulation(
        " ".join([topic.get("label", ""), topic.get("motion", ""), " ".join(topic.get("objections", []))]),
        topic,
    )

    return {
        "topic": {"id": topic_id, "label": topic["label"], "unit": topic.get("unit", ""), "category": topic.get("category", "")},
        "series": {
            "labels": labels,
            "values": [round(float(v), 4) for v in y],
            "pre_end": pre_end,
            "post_end": pre_end + h,
        },
        "counterfactual": {
            "labels": labels[pre_end:pre_end + h],
            "point": [round(float(v), 4) for v in cf],
            "p10": [round(float(v), 4) for v in q[:, 0]],
            "p90": [round(float(v), 4) for v in q[:, -1]],
            "engine": fc["engine"],
            "pre_fit_mape_pct": round(mape, 2),
        },
        "att": {
            "cumulative": round(cum, 4),
            "mean_per_period": round(cum / h, 4),
            "relative_pct": round(rel, 2),
            "conformal_halfwidth": round(half, 4),
            "conformal_low": round(cum - half, 4),
            "conformal_high": round(cum + half, 4),
            "conformal_relative_low": round((cum - half) / (float(np.sum(cf)) or 1) * 100, 2),
            "conformal_relative_high": round((cum + half) / (float(np.sum(cf)) or 1) * 100, 2),
            "note": "Conformal interval is approximate: rolling-origin cumulative errors, not a guarantee under non-stationarity. TimesFM quantiles are not causal intervals.",
        },
        "observed_vs_cf": observed_vs_cf,
        "placebo_time": placebo,
        "synthetic_control": sc,
        "bayesian": bayes,
        "monte_carlo": {
            "paths": 600,
            "cumulative_p10": round(float(np.quantile(cum_paths, .10)), 4),
            "cumulative_p50": round(float(np.quantile(cum_paths, .50)), 4),
            "cumulative_p90": round(float(np.quantile(cum_paths, .90)), 4),
            "relative_p10": round(float(np.quantile(rel_paths, .10)), 2),
            "relative_p50": round(float(np.quantile(rel_paths, .50)), 2),
            "relative_p90": round(float(np.quantile(rel_paths, .90)), 2),
            "prob_positive": round(float(np.mean(cum_paths > 0)), 3),
            "cvar5": round(float(np.mean(np.sort(rel_paths)[:max(1, int(len(rel_paths) * .05))])), 2),
            "note": "Block bootstrap of residual noise plus rolling-origin counterfactual bias. It still does not include structural model uncertainty.",
        },
        "npv": npv,
        "precedents": prior,
        "validation": monte_carlo_validation(60),
        "caveats": [
            "The counterfactual is a forecast, not an identified no-treatment outcome.",
            "TimesFM does not know about the decision or the news; its quantiles are not causal intervals.",
            "Conformal coverage is approximate under non-stationarity and short pre-periods.",
            "Placebo tests are low-power with 94 monthly points; treat p-values as diagnostics, not proof.",
            "Precedent arcs are reconstructed from public reporting, not a measured panel.",
            "The simulation prior is a wide hypothesis. If it disagrees with the data, reconcile before deciding.",
        ],
    }
