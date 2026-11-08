"""Model card: what this system is, what it is not, and how to check it.

Written to be read by a research reviewer, a procurement team and a lawyer,
not just by the person who built it. Every claim points at code or a check.
"""
from __future__ import annotations

import time

from . import atlas, calibration, forecast, llm, store, validation


def card() -> dict:
    known = validation.known_answer_tests()
    backtest = validation.real_series_backtest()
    ev = store.evidence()
    anchors = calibration._anchor_rows()
    return {
        "identity": {
            "name": "Imprint Bharat",
            "engine": "imprint-core/3.1",
            "version": "0.2.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "owner": "Imprint Research",
        },
        "intended_use": [
            "Generate and stress-test hypotheses about how an Indian category could diffuse across tier, region and occupation.",
            "Find the binding constraint before spending on a real pilot.",
            "Produce a falsifiable next test with a named comparison group.",
            "Communicate uncertainty and assumptions to a non-technical decision maker.",
        ],
        "out_of_scope": [
            "It is not a representative survey and must never be reported as one.",
            "It is not a causal estimate of a campaign's effect.",
            "It does not predict individual behaviour or name real people.",
            "It is not a substitute for a pilot, a panel or primary qualitative work.",
            "It should not be used for credit, insurance, employment or policing decisions about real people.",
        ],
        "population": {
            "design": "Stratified synthetic sample by state, tier, occupation, gender, age, digital access, religion, caste, ideology, thought process, economic band, schooling, settlement and Big Five personality.",
            "public_inputs": [
                "State population, urbanisation and internet penetration (Census / TRAI).",
                "Tier and income distributions (NITI Aayog, RBI, HCES).",
                "Occupation archetypes and regional names.",
                f"{len(store.archetypes())} occupation archetypes with explicit trait ranges (up to 3,000 agents per run).",
                "16 behavioural biases with tier-specific base rates.",
                "19 category packs with 94-month public histories.",
                f"{len(ev)} evidence cards and {len(atlas.sources())} cited public sources, including Census 2011, NFHS-5, Time Use Survey 2024, Elderly in India 2021, NHA 2021-22, RBI FI-Index and Economic Survey 2023-24.",
                "Division analytics (adoption × TimesFM market trend) and a GTM playbook derived from the same run, not re-simulated.",
            ],
            "counts": {
                "states": len(store.states()),
                "archetypes": len(store.archetypes()),
                "biases": len(store.biases()),
                "topics": len(store.topics()),
                "evidence": len(ev),
                "atlas_nodes": len(atlas.all_nodes()),
                "sources": len(atlas.sources()),
            },
        },
        "methods": [
            {"name": "Belief updating", "detail": "Each agent is a 6-4-1 MLP; beliefs update by backprop on a cognitive-dissonance loss (nn.py / vectorbelief.py). Cohorts above ~600 run the same architecture batched in NumPy for speed; the backend is recorded per run."},
            {"name": "Diversity", "detail": f"{len(store.archetypes())} occupations plus ideology, thought process, economic band, schooling, settlement, age band and Big Five personality — all modelled as structural context with small explicit effects, never as identity claims."},
            {"name": "Divisions × TimesFM", "detail": "Per-division conversion, rejection, lead/lag and correlation with the TimesFM market-trend signal; the GTM playbook is derived from these divisions, not invented."},
            {"name": "Dual-process appraisal", "detail": "Need for cognition routes agents between deliberate attribute weighting (System 2) and an affective/social shortcut (System 1). Kahneman 2011; Petty & Cacioppo 1986."},
            {"name": "Prospect theory", "detail": "Reference-dependent value, λ = 2.25, α = 0.88. Kahneman & Tversky 1979/1992."},
            {"name": "Present bias", "detail": "Quasi-hyperbolic β–δ discounting suppresses delayed payoffs for costly-now categories. Laibson 1997."},
            {"name": "Social thresholds", "detail": "Heterogeneous Granovetter thresholds plus graph-Laplacian diffusion. Granovetter 1978."},
            {"name": "Trust repair", "detail": "Asymmetric collapse and exponential recovery with a precedent-derived half-life. Slovic 1993."},
            {"name": "Mere exposure", "detail": "Saturating habituation bonus from cumulative impressions. Zajonc 1980."},
            {"name": "Diffusion fits", "detail": "Rogers buckets and Bass (p, q) grid fit reported per run. Rogers 1962; Bass 1969."},
            {"name": "Demand signal", "detail": "TimesFM 3.0 zero-shot forecast used as an exogenous market trend, averaged over level, log and first-differenced views (test-time augmentation), with a labelled damped-trend fallback."},
            {"name": "Forecast reasoning", "detail": "Multi-hypothesis audit over the foundation path: drift, damped trend, mean reversion and seasonal naive scored by rolling-origin MAE; plausibility, non-negativity and band rules; no point-accuracy multiplier claimed (forecast_reasoning.py)."},
            {"name": "Uncertainty", "detail": "Seed × parameter Latin-hypercube ensemble with a one-way variance decomposition (uncertainty.py)."},
            {"name": "Sensitivity", "detail": "Saltelli first-order and total-order Sobol indices over the six behavioural parameters (sensitivity.py)."},
            {"name": "Causal layer", "detail": "Counterfactual forecast, rolling-origin conformal interval, in-time placebo and synthetic control — labelled as decision support, not identification (causal.py)."},
        ],
        "validation": {
            "known_answer": {
                "passed": known["passed"], "total": known["total"],
                "score": known["score"], "checks": known["checks"],
            },
            "backtest": {
                "median_mase": backtest["median_mase"],
                "median_mase_timesfm": backtest.get("median_mase_timesfm"),
                "median_mase_timesfm_aug3": backtest.get("median_mase_timesfm_aug3"),
                "median_mase_timesfm_reasoned": backtest.get("median_mase_timesfm_reasoned"),
                "median_beats_naive_share": backtest["median_beats_naive_share"],
                "median_trend_hit": backtest.get("median_trend_hit"),
                "median_trend_hit_timesfm": backtest.get("median_trend_hit_timesfm"),
                "median_trend_hit_timesfm_aug3": backtest.get("median_trend_hit_timesfm_aug3"),
                "median_trend_base": backtest.get("median_trend_base"),
                "median_trend_skill": backtest.get("median_trend_skill"),
                "median_vs_drift": backtest.get("median_vs_drift"),
                "median_vs_drift_timesfm": backtest.get("median_vs_drift_timesfm"),
                "median_vs_drift_timesfm_aug3": backtest.get("median_vs_drift_timesfm_aug3"),
                "median_vs_drift_timesfm_reasoned": backtest.get("median_vs_drift_timesfm_reasoned"),
                "coverage": backtest.get("median_coverage_timesfm"),
                "coverage_aug3": backtest.get("median_coverage_timesfm_aug3"),
                "coverage_reasoned": backtest.get("median_coverage_timesfm_reasoned"),
                "augmentation_delta": backtest.get("augmentation_delta"),
                "augmentation_verdict": backtest.get("augmentation_verdict"),
                "reasoning_delta": backtest.get("reasoning_delta"),
                "reasoning_verdict": backtest.get("reasoning_verdict"),
                "n_topics": backtest["n_topics"],
                "verdict": backtest.get("verdict"),
                "note": backtest["note"],
            },
            "calibration_anchors": [
                {"topic": a["topic_id"], "target": a["target"],
                 "range": [a["low"], a["high"]], "basis": a["basis"]}
                for a in anchors
            ],
            "calibration_note": (
                "Anchors are analyst ranges from public sources, not measured panels. "
                "Held-out calibration is available on demand and is the number to trust."
            ),
        },
        "uncertainty": {
            "reported": ["percentile intervals across seeds and parameter draws", "P(SCALE)", "P(conversion ≥ target)", "epistemic vs aleatoric variance share"],
            "not_reported": ["a sampling-error confidence interval", "a posterior probability that the hypothesis is true"],
        },
        "systems": {
            "timesfm": forecast.status(),
            "llm": llm.status(),
            "llm_role": "Optional narration only. The simulation never depends on an LLM being available.",
        },
        "limitations": [
            "Public distributions constrain the population, not behaviour. Behavioural parameters are modelled, not measured.",
            "Anchors are analyst ranges; calibrating to them is not causal identification.",
            "The social graph is synthetic homophily, not an observed network.",
            "WhatsApp — India's largest social channel — is under-observed in public data.",
            "Category histories are aggregated; they cannot identify within-category heterogeneity.",
            "TimesFM weights are non-commercial licensed; check before commercial deployment.",
            "The causal layer is a drift check unless a real decision date and comparison group are supplied.",
        ],
        "ethics": [
            "No real individuals are represented; names are synthetic and drawn from public name distributions.",
            "Caste, religion and region are structural context for in-group trust, never essentialist claims.",
            "Outputs must be shown with their uncertainty and with the falsifier that would overturn them.",
            "Do not deploy for decisions that materially affect a real person's access to credit, work or safety.",
        ],
        "reproducibility": {
            "contract": "brief + seed + scenario + tier mix + parameters + engine version reproduce a run exactly.",
            "fingerprint": "Every run carries a 16-character SHA-256 provenance fingerprint.",
        },
        "how_to_cite": (
            "Imprint Bharat (2026). Synthetic consumer rehearsal for India. "
            "Engine imprint-core/3.1. Report alongside its validation score and uncertainty interval."
        ),
    }


__all__ = ["card"]
