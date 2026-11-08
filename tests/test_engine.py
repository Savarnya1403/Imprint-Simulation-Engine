"""Engine-level checks: scenarios run, seeds reproduce, parameters bite."""
from __future__ import annotations

import statistics

import pytest

from app import calibration, engine


def test_all_scenarios_return_a_summary(brief):
    for spec in engine.SCENARIOS:
        r = engine.run_simulation(brief, n_agents=70, rounds=14, seed=7,
                                  scenario=spec["id"], fast=True)
        assert r["summary"]["scenario"] == spec["id"]
        assert 0 <= r["summary"]["adoption"] <= 1
        assert 0 <= r["summary"]["conversion"] <= 1
        assert len(r["timeline"]) == 14


def test_same_seed_reproduces_the_run(brief):
    a = engine.run_simulation(brief, n_agents=60, rounds=12, seed=123, fast=True)
    b = engine.run_simulation(brief, n_agents=60, rounds=12, seed=123, fast=True)
    assert a["provenance"]["fingerprint"] == b["provenance"]["fingerprint"]
    assert a["summary"] == b["summary"]
    assert a["timeline"] == b["timeline"]


def test_different_seeds_move_the_answer(brief):
    outs = [engine.run_simulation(brief, n_agents=90, rounds=14, seed=s, fast=True)["summary"]["adoption"]
            for s in (1, 2, 3)]
    fingerprints = [engine.run_simulation(brief, n_agents=90, rounds=14, seed=s, fast=True)["provenance"]["fingerprint"]
                    for s in (1, 2, 3)]
    assert len(set(fingerprints)) == 3
    # At least one seed must produce a different adoption outcome; identical
    # rounding on tiny runs is allowed, but not all three.
    assert len(set(outs)) > 1


def test_price_cut_helps_and_trust_shock_hurts(brief):
    kwargs = dict(brief=brief + " ", n_agents=90, rounds=18, seed=11, fast=True)
    base = engine.run_simulation(scenario="base", **kwargs)["summary"]["conversion"]
    cut = engine.run_simulation(scenario="price_cut", **kwargs)["summary"]["conversion"]
    shock = engine.run_simulation(scenario="trust_shock", **kwargs)["summary"]["conversion"]
    assert cut >= base
    assert shock <= base + 1e-9


def test_social_multiplier_is_monotone_across_seeds(brief):
    # N=240 gives the social field enough mass to be detected; at N=90 the
    # conversion is 3/10 agents and the test is underpowered (verified).
    def mean_conv(mult: float) -> float:
        vals = [engine.run_simulation(brief, n_agents=240, rounds=20, seed=s,
                                      params={**calibration.load_params(), "social_mult": mult},
                                      fast=True)["summary"]["conversion"]
                for s in (3, 4, 5)]
        return statistics.mean(vals)

    assert mean_conv(1.45) > mean_conv(0.75)


def test_addressable_pool_respects_ceiling(run_small):
    addressable = run_small["summary"]["addressable"]
    population = run_small["population"]
    assert 0 < addressable <= population
    # The ceiling is a share of the population; allow rounding of the mask.
    assert addressable <= int(round(run_small["summary"]["ceiling"] * population)) + 1


def test_provenance_contract(run_small):
    p = run_small["provenance"]
    assert p["engine"] == "imprint-core/3.1"
    assert len(p["fingerprint"]) == 16
    assert int(p["fingerprint"], 16) >= 0
    assert p["seed"] == run_small["seed"]
    assert set(p["params"]) == {
        "ceiling_mult", "price_sensitivity", "social_mult",
        "trust_weight", "hazard_mult", "atlas_strength",
    }


def test_cognitive_block_is_reported(run_small):
    cog = run_small["cognitive"]
    for key in ("dual_process_mean", "threshold_mean", "present_bias_mean", "trust_repair_days"):
        assert key in cog
    assert 0 <= cog["dual_process_mean"] <= 1
    assert 0 <= cog["threshold_mean"] <= 1


def test_invalid_scenario_falls_back_or_raises(brief):
    with pytest.raises(KeyError):
        engine.SCENARIO_MODS["not-a-scenario"]
