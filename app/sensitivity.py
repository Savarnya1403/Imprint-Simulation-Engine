"""Global sensitivity analysis over the behavioural parameters.

Calibration tunes six parameters. The obvious question nobody usually answers
is: which ones actually move the answer?

This module runs a Saltelli pick-freeze design (A, B, and A-with-column-j-from-B)
and reports

  * ST  — Jansen total-order index: variance explained by a parameter plus all
          its interactions. Stable enough at small N to rank parameters.
  * linear_share — that parameter's share of variance in a standardised linear
          response surface fitted to the same design. Stable at N≈6-16, which
          is the budget a live product can afford.
  * interaction — ST − linear_share.

First-order Saltelli indices are deliberately not reported: at N≈8-16 they
routinely return values above 1 or below 0, and publishing them would be
worse than publishing nothing.

Cost: N·(D+2) simulations. With N=6 and D=6 that is 48 fast runs.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import calibration, engine


def _eval(points: list[dict], brief: str, n_agents: int, rounds: int,
          scenario: str, focus_state: str | None, tier_mix: dict | None,
          seed: int, metric: str) -> np.ndarray:
    out = np.zeros(len(points))
    for i, params in enumerate(points):
        try:
            r = engine.run_simulation(
                brief, n_agents=n_agents, rounds=rounds, seed=seed,
                scenario=scenario, focus_state=focus_state, tier_mix=tier_mix,
                params=params, fast=True,
            )
            out[i] = float(r["summary"].get(metric, 0.0))
        except Exception:
            out[i] = np.nan
    return out


def decompose(fA: np.ndarray, fB: np.ndarray, fAB: list[np.ndarray],
              X_design: list[np.ndarray], names: list[str],
              lo: np.ndarray, hi: np.ndarray,
              metric: str = "conversion", n_base: int = 6) -> dict[str, Any]:
    """Turn a pick-freeze design into total-order and linear variance shares."""
    fA = np.nan_to_num(np.asarray(fA, dtype=float),
                       nan=float(np.nanmean(fA)) if np.isfinite(fA).any() else 0.0)
    fB = np.nan_to_num(np.asarray(fB, dtype=float),
                       nan=float(np.nanmean(fB)) if np.isfinite(fB).any() else 0.0)
    fAB = [np.nan_to_num(np.asarray(x, dtype=float),
                         nan=float(np.nanmean(x)) if np.isfinite(x).any() else 0.0)
           for x in fAB]

    # Variance of the model output is estimated from the two base samples only.
    # Including the AB samples in the denominator biases total-order indices down.
    var = float(np.var(np.concatenate([fA, fB]), ddof=1))
    if var <= 1e-12:
        return {
            "metric": metric, "available": False,
            "note": "Output has no variance at this setting; increase population or rounds.",
            "indices": [], "n_base": n_base,
            "evaluations": len(fA) + len(fB) + sum(len(x) for x in fAB),
        }

    # --- Linear response surface on the same design -----------------------
    X_all = np.vstack(X_design)
    y_all = np.concatenate([fA, fB] + fAB)
    Xz = (X_all - X_all.mean(axis=0)) / np.maximum(X_all.std(axis=0), 1e-9)
    Xd = np.column_stack([np.ones(len(Xz)), Xz])
    beta, *_ = np.linalg.lstsq(Xd, y_all, rcond=None)
    pred = Xd @ beta
    ss_res = float(np.sum((y_all - pred) ** 2))
    ss_tot = float(np.sum((y_all - y_all.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    coef = beta[1:]
    energy = float(np.sum(coef ** 2))
    shares = (coef ** 2 / energy) if energy > 1e-12 else np.zeros_like(coef)

    indices = []
    for j, name in enumerate(names):
        st = float(np.mean((fA - fAB[j]) ** 2) / (2 * var))
        linear_share = float(shares[j])
        indices.append({
            "param": name,
            "st": round(max(0.0, min(1.0, st)), 3),
            "linear_share": round(max(0.0, min(1.0, linear_share)), 3),
            "interaction": round(max(0.0, min(1.0, st - linear_share)), 3),
            "range": [float(lo[j]), float(hi[j])],
            "coef_sign": "positive" if coef[j] >= 0 else "negative",
        })

    indices.sort(key=lambda x: -x["st"])
    total_st = sum(i["st"] for i in indices)
    return {
        "metric": metric,
        "available": True,
        "n_base": n_base,
        "evaluations": len(y_all),
        "output": {
            "mean": round(float(np.mean(y_all)), 4),
            "sd": round(float(np.sqrt(var)), 4),
            "min": round(float(np.min(y_all)), 4),
            "max": round(float(np.max(y_all)), 4),
        },
        "indices": indices,
        "linear_fit_r2": round(r2, 3),
        "sum_total_order": round(total_st, 3),
        "interaction_share": round(max(0.0, 1.0 - float(np.sum(shares))), 3),
        "most_influential": indices[0]["param"] if indices else None,
        "inert": [i["param"] for i in indices if i["st"] < .05],
        "note": (
            "st is the Jansen total-order index: variance explained by a parameter "
            "plus all its interactions. linear_share is that parameter's share in a "
            "standardised linear response surface, which is stable at small sample "
            "sizes. interaction = st − linear_share. First-order Saltelli estimates "
            "are omitted because they are unusably noisy below N≈64. "
            "Parameters with st < 0.05 are not worth tuning."
        ),
    }


def sobol(
    brief: str,
    metric: str = "conversion",
    n_base: int = 6,
    n_agents: int = 150,
    rounds: int = 20,
    scenario: str = "base",
    focus_state: str | None = None,
    tier_mix: dict | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Pick-freeze design over the six behavioural parameters."""
    metric = metric if metric in ("conversion", "adoption", "sentiment") else "conversion"
    n_base = max(4, min(32, int(n_base)))
    names = list(calibration.SPECS)
    lo = np.array([calibration.SPECS[k][0] for k in names])
    hi = np.array([calibration.SPECS[k][1] for k in names])
    d = len(names)
    rng = np.random.default_rng(seed)

    A = lo + rng.random((n_base, d)) * (hi - lo)
    B = lo + rng.random((n_base, d)) * (hi - lo)

    def to_points(mat):
        return [{k: round(float(mat[i, j]), 4) for j, k in enumerate(names)}
                for i in range(mat.shape[0])]

    fA = _eval(to_points(A), brief, n_agents, rounds, scenario, focus_state, tier_mix, seed, metric)
    fB = _eval(to_points(B), brief, n_agents, rounds, scenario, focus_state, tier_mix, seed, metric)
    fAB, AB_mats = [], []
    for j in range(d):
        AB = A.copy()
        AB[:, j] = B[:, j]
        AB_mats.append(AB)
        fAB.append(_eval(to_points(AB), brief, n_agents, rounds, scenario, focus_state,
                         tier_mix, seed, metric))

    return decompose(fA, fB, fAB, [A, B] + AB_mats, names, lo, hi, metric, n_base)


def synthetic_recovery(n_base: int = 12, seed: int = 3) -> dict[str, Any]:
    """Known-answer test for the estimator itself.

    On y = 3x₀ + x₁ (x uniform [0,1]), the true total-order shares are
    (0.9, 0.1, 0.0). If the decomposition cannot recover that, its numbers on
    the simulator are not trustworthy.
    """
    rng = np.random.default_rng(seed)
    names = ["x0", "x1", "x2"]
    lo, hi = np.zeros(3), np.ones(3)
    A = rng.random((n_base, 3))
    B = rng.random((n_base, 3))

    def f(M):
        return 3.0 * M[:, 0] + 1.0 * M[:, 1]

    fA, fB = f(A), f(B)
    fAB, mats = [], []
    for j in range(3):
        AB = A.copy()
        AB[:, j] = B[:, j]
        mats.append(AB)
        fAB.append(f(AB))
    out = decompose(fA, fB, fAB, [A, B] + mats, names, lo, hi, "synthetic", n_base)
    got = {i["param"]: i for i in out["indices"]}
    ok = (
        out["most_influential"] == "x0"
        and abs(got["x0"]["st"] - 0.9) < 0.25
        and abs(got["x1"]["st"] - 0.1) < 0.20
        and got["x2"]["st"] < 0.15
    )
    return {
        "ok": bool(ok),
        "expected": {"x0": 0.9, "x1": 0.1, "x2": 0.0},
        "estimated": {k: v["st"] for k, v in got.items()},
        "n_base": n_base,
    }


__all__ = ["sobol", "decompose", "synthetic_recovery"]
