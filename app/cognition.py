"""Cognitive and consumer-behavior mathematics.

From the expert debate: three upgrades to the decision engine.

1. Prospect Theory (Kahneman & Tversky 1979/1992)
   Value is reference-dependent and S-shaped. Losses loom ~2.25× larger than
   gains (λ = 2.25). Diminishing sensitivity: alpha = 0.88.

2. Mere Exposure / Neuroplasticity (Zajonc 1980; Hebb 1949)
   Repeated exposure increases liking without awareness. Effect grows with
   cumulative exposures up to saturation. Modelled as a habituation bonus.

3. Rogers Diffusion + Bass Model (Rogers 1962; Bass 1969)
   Adoption follows an S-curve: N(t) = M · (1 − exp(−(p + q·N(t−1)/M)·t)).
   p = innovator coefficient, q = imitation coefficient. Fitted from each run.
"""
from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# 1. Prospect theory
# ---------------------------------------------------------------------------

def prospect_value(x: float, reference: float = 0.0, lam: float = 2.25, alpha: float = 0.88) -> float:
    """S-shaped value function. x is outcome relative to reference."""
    d = x - reference
    if d >= 0:
        return d ** alpha
    return -lam * ((-d) ** alpha)


def diminishing_sensitivity(values: list[float]) -> float:
    """How strongly S-curve compresses gains (mean slope within gains)."""
    if not values:
        return 1.0
    slopes = [x ** 0.12 for x in values if x > 0]  # derivative of x^0.88 at x
    return float(sum(slopes) / len(slopes)) if slopes else 1.0


# ---------------------------------------------------------------------------
# 2. Mere exposure / habituation
# ---------------------------------------------------------------------------

def mere_exposure_bonus(exposures: int, peak: float = 0.35, half_life: float = 8.0) -> float:
    """Habituation curve — logarithmic growth, saturating.

    Each exposure adds a small positive delta; gains decay as exposure
    accumulates (diminishing returns). Zajonc's mere-exposure effect.
    """
    if exposures <= 0:
        return 0.0
    return peak * (1 - 0.5 ** (exposures / half_life))


def exposure_consolidation(exposure_counts: list[int], threshold: int = 5) -> float:
    """Fraction of agents with enough exposures to have formed a preference."""
    if not exposure_counts:
        return 0.0
    return sum(1 for e in exposure_counts if e >= threshold) / len(exposure_counts)


# ---------------------------------------------------------------------------
# 3. Rogers / Bass diffusion
# ---------------------------------------------------------------------------

def rogers_bucket(score: float) -> str:
    """Classify an adopter by innovativeness percentile (Rogers 1962)."""
    if score >= 0.84:
        return "Innovator"
    if score >= 0.66:
        return "Early adopter"
    if score >= 0.50:
        return "Early majority"
    if score >= 0.16:
        return "Late majority"
    return "Laggard"


def bass_cumulative(t: int, M: float, p: float, q: float) -> float:
    """Discrete Bass cumulative adoption at time t (Bass 1969)."""
    n = 0.0
    prev = 0.0
    for _ in range(t):
        rate = (p + q * (prev / M if M > 0 else 0)) * (M - prev)
        inc = min(max(0.0, rate), M - prev)
        n = prev + inc
        prev = n
    return n


def bass_fit(timeline: list[dict], market_potential: float) -> dict[str, Any]:
    """Fit (p, q) to simulated cumulative adoption via grid search.

    No SciPy needed: coarse-to-fine grid search minimizing squared error
    between model cumulative curve and simulated cumulative adoption.
    """
    if not timeline or market_potential <= 0:
        return {"p": None, "q": None, "r_squared": None, "peak_day": None, "interpretation": "Insufficient data"}
    cum = [t["adoption"] for t in timeline]
    cum = [c * market_potential for c in cum]  # scale to units
    best_sse = float("inf")
    best = {"p": 0.02, "q": 0.4}

    for p in [0.001, 0.005, 0.01, 0.02, 0.04, 0.06]:
        for q in [0.05, 0.1, 0.25, 0.5, 0.8, 1.2, 1.6]:
            sse = 0.0
            prev = 0.0
            for t_i, target in enumerate(cum, start=1):
                rate = (p + q * (prev / market_potential)) * (market_potential - prev)
                inc = min(max(0.0, rate), market_potential - prev)
                prev = prev + inc
                sse += (prev - target) ** 2
            if sse < best_sse:
                best_sse = sse
                best = {"p": p, "q": q}
    # R² against null model (mean)
    mean_c = sum(cum) / len(cum) if cum else 0
    ss_tot = sum((c - mean_c) ** 2 for c in cum)
    best_r2 = max(0.0, 1 - best_sse / ss_tot) if ss_tot > 0 else 0.0
    # peak: where adoption increment is maximal
    increments = [timeline[i]["new"] for i in range(len(timeline))]
    peak_day = increments.index(max(increments)) + 1 if increments and max(increments) > 0 else None
    return {
        "p": best["p"],
        "q": best["q"],
        "r_squared": round(best_r2, 3),
        "peak_day": peak_day,
        "interpretation": interpret_bass(best["p"], best["q"], best_r2),
    }


def interpret_bass(p: float, q: float, r_squared: float) -> str:
    if r_squared < 0.3:
        return "Weak fit — simulated adoption is too slow for a clean Bass S-curve at this horizon."
    if q > 0.5 and q > 2 * p:
        return "Imitation-led adoption — word-of-mouth / social proof dominates."
    if p > 0.04 and q < 3 * p:
        return "Innovation-led adoption — heavy reliance on external seeding."
    return "Mixed-mode diffusion."




# ---------------------------------------------------------------------------
# 4. Psychometrics (mapped from existing traits)
# ---------------------------------------------------------------------------

def susceptibility_to_influence(traits: dict[str, float]) -> float:
    """Bearden-style susceptibility to interpersonal influence (0-100)."""
    # High conformity + status + social_radius = susceptible
    score = (
        traits.get("conformity", 0.5) * 0.45
        + traits.get("status", 0.5) * 0.25
        + traits.get("social_radius", 0.5) * 0.30
    )
    return round(score * 100, 1)


def need_for_cognition(traits: dict[str, float]) -> float:
    """Cacioppo & Petty need for cognition (0-100). Higher = deliberate."""
    # High education + inverse risk + conscientiousness
    score = (
        traits.get("education", 0.5) * 0.55
        + (1 - traits.get("risk", 0.5)) * 0.25
        + traits.get("patience", 0.5) * 0.20
    )
    return round(score * 100, 1)


def price_sensitivity_meter(price_trait: float, income: float) -> dict[str, Any]:
    """Van Westendorp-style sensitivity band (qualitative, bounded)."""
    # Low price_trait -> very sensitive; high income shifts band upward
    income_term = min(1.0, income / 100000.0) * 0.15
    low_band = round(0.35 - price_trait * 0.2 + income_term, 2)
    high_band = round(0.65 - price_trait * 0.2 + income_term, 2)
    return {
        "low_acceptance": max(0, low_band),
        "high_rejection": min(1, high_band),
        "sensitivity_index": round(price_trait * 100, 1),
        "note": "Higher index = lower tolerance for price. Map to van Westendorp bands only via measured survey.",
    }


# ---------------------------------------------------------------------------
# 5. Bootstrap uncertainty
# ---------------------------------------------------------------------------

def bootstrap_ci(samples: list[float], n_boot: int = 200, alpha: float = 0.05) -> dict[str, float]:
    """Percentile bootstrap CI for a metric."""
    if len(samples) < 3:
        return {"lower": None, "upper": None, "half_width": None}
    import random
    rng = random.Random(123)
    means = []
    for _ in range(n_boot):
        b = [samples[rng.randrange(len(samples))] for _ in range(len(samples))]
        means.append(sum(b) / len(b))
    means.sort()
    lo = means[int(alpha / 2 * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot) - 1]
    return {"lower": round(lo, 4), "upper": round(hi, 4), "half_width": round((hi - lo) / 2, 4)}


__all__ = [
    "prospect_value",
    "diminishing_sensitivity",
    "mere_exposure_bonus",
    "exposure_consolidation",
    "rogers_bucket",
    "bass_cumulative",
    "bass_fit",
    "susceptibility_to_influence",
    "need_for_cognition",
    "price_sensitivity_meter",
    "bootstrap_ci",
]
