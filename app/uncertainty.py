"""Run-level uncertainty quantification.

A single simulation is one draw from two different distributions:

  * ALEATORIC — the simulator's own randomness (seed). Even with fixed
    parameters, two seeds disagree.
  * EPISTEMIC — our uncertainty about the six behavioural parameters.

Most agent-based demos report one run and one point estimate. That is not a
forecast. This module runs a small Latin-hypercube ensemble and reports:

  * percentile intervals for adoption / conversion
  * decision probabilities: P(SCALE), P(conversion ≥ target)
  * a one-way variance decomposition (ICC): how much of the spread is
    parameter uncertainty vs seed noise
  * which parameter is most correlated with the answer

The decomposition is a diagnostic, not a Bayesian posterior.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import calibration, engine


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.quantile(np.asarray(values, dtype=float), q))


def _summ(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "p10": None, "p50": None, "p90": None, "sd": None}
    arr = np.asarray(values, dtype=float)
    return {
        "mean": round(float(arr.mean()), 4),
        "p10": round(float(np.quantile(arr, .10)), 4),
        "p50": round(float(np.quantile(arr, .50)), 4),
        "p90": round(float(np.quantile(arr, .90)), 4),
        "sd": round(float(arr.std(ddof=1)) if len(arr) > 1 else 0.0, 4),
        "min": round(float(arr.min()), 4),
        "max": round(float(arr.max()), 4),
    }


def _lhs_draws(n: int, rng: np.random.Generator) -> list[dict[str, float]]:
    names = list(calibration.SPECS)
    lo = np.array([calibration.SPECS[k][0] for k in names])
    hi = np.array([calibration.SPECS[k][1] for k in names])
    d = len(names)
    u = np.zeros((n, d))
    for j in range(d):
        u[:, j] = (rng.permutation(n) + rng.random(n)) / max(1, n)
    out = []
    for i in range(n):
        out.append({k: round(float(lo[j] + u[i, j] * (hi[j] - lo[j])), 4)
                    for j, k in enumerate(names)})
    return out


def ensemble(
    brief: str,
    n_agents: int = 180,
    rounds: int = 24,
    scenario: str = "base",
    focus_state: str | None = None,
    tier_mix: dict | None = None,
    seeds: int = 6,
    param_draws: int = 6,
    seed0: int = 42,
    target_conversion: float = .50,
) -> dict[str, Any]:
    """Run a seed × parameter ensemble and decompose the resulting spread."""
    seeds = max(2, min(12, int(seeds)))
    param_draws = max(2, min(16, int(param_draws)))
    rng = np.random.default_rng(seed0)

    draws = [dict(calibration.load_params())] + _lhs_draws(param_draws - 1, rng)

    rows: list[dict] = []
    for di, params in enumerate(draws):
        for s in range(seeds):
            run_seed = seed0 + s
            try:
                r = engine.run_simulation(
                    brief, n_agents=n_agents, rounds=rounds, seed=run_seed,
                    scenario=scenario, focus_state=focus_state, tier_mix=tier_mix,
                    params=params, fast=True,
                )
                s_ = r["summary"]
                rows.append({
                    "draw": di,
                    "seed": run_seed,
                    "conversion": float(s_.get("conversion", 0)),
                    "adoption": float(s_.get("adoption", 0)),
                    "sentiment": float(s_.get("sentiment", 0)),
                    "verdict": s_.get("verdict", "—"),
                    "params": params,
                })
            except Exception as exc:
                rows.append({
                    "draw": di, "seed": run_seed, "conversion": None,
                    "adoption": None, "sentiment": None, "verdict": "error",
                    "params": params, "error": f"{type(exc).__name__}: {exc}",
                })

    ok = [r for r in rows if r["conversion"] is not None]
    conv = [r["conversion"] for r in ok]
    adopt = [r["adoption"] for r in ok]
    verdicts = [r["verdict"] for r in ok]

    # --- One-way variance decomposition (draw = group, seed = replicate) ---
    groups: dict[int, list[float]] = {}
    for r in ok:
        groups.setdefault(r["draw"], []).append(r["conversion"])
    group_means = [float(np.mean(v)) for v in groups.values() if v]
    within = [float(np.var(v, ddof=1)) for v in groups.values() if len(v) > 1]
    between = float(np.var(group_means, ddof=1)) if len(group_means) > 1 else 0.0
    aleatoric = float(np.mean(within)) if within else 0.0
    epi_share = between / (between + aleatoric) if (between + aleatoric) > 0 else 0.0

    # --- Which parameter co-moves with conversion? ---
    param_corr = []
    if len(ok) > 3:
        for name in calibration.SPECS:
            xs = np.array([r["params"][name] for r in ok], dtype=float)
            ys = np.array([r["conversion"] for r in ok], dtype=float)
            if xs.std() > 1e-9 and ys.std() > 1e-9:
                param_corr.append({
                    "param": name,
                    "corr": round(float(np.corrcoef(xs, ys)[0, 1]), 3),
                })
        param_corr.sort(key=lambda x: -abs(x["corr"]))

    n = max(1, len(ok))
    scale = sum(1 for v in verdicts if v == "SCALE") / n
    test_plus = sum(1 for v in verdicts if v in ("SCALE", "TEST")) / n
    p_target = sum(1 for c in conv if c >= target_conversion) / n
    width = (_pct(conv, .90) - _pct(conv, .10)) if conv else 0.0
    mean = float(np.mean(conv)) if conv else 0.0
    robust = bool(conv) and (width / max(1e-6, mean) < .35) and (p_target >= .8 or p_target <= .2)

    return {
        "brief": brief,
        "runs": len(rows),
        "seeds": seeds,
        "param_draws": param_draws,
        "population": n_agents,
        "rounds": rounds,
        "conversion": _summ(conv),
        "adoption": _summ(adopt),
        "decision": {
            "target_conversion": target_conversion,
            "p_at_or_above_target": round(p_target, 3),
            "p_scale": round(scale, 3),
            "p_scale_or_test": round(test_plus, 3),
            "verdicts": {v: verdicts.count(v) for v in sorted(set(verdicts))},
        },
        "variance": {
            "epistemic_sd": round(float(np.sqrt(max(0.0, between))), 4),
            "aleatoric_sd": round(float(np.sqrt(max(0.0, aleatoric))), 4),
            "epistemic_share": round(epi_share, 3),
            "note": (
                "Epistemic share is the fraction of total variance attributable to "
                "parameter uncertainty rather than seed noise. High values mean the "
                "answer depends on assumptions you can still change."
            ),
        },
        "param_corr": param_corr[:6],
        "robust": robust,
        "rows": [
            {k: r[k] for k in ("draw", "seed", "conversion", "adoption", "sentiment", "verdict")}
            for r in rows
        ],
        "note": (
            "Percentiles come from a small Latin-hypercube ensemble, not a posterior. "
            "They are a defensible range, not a confidence guarantee."
        ),
    }


__all__ = ["ensemble"]
