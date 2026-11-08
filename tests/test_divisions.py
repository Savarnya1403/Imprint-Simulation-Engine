"""Division analytics, batched beliefs, strategy playbook, 3000-agent scale."""
from __future__ import annotations

import numpy as np
import pytest

from app import engine, personas, segments, store, strategy
from app.vectorbelief import BatchedMLP


def test_vectorbelief_is_deterministic_and_fast():
    np.random.seed(7)
    a = BatchedMLP(50)
    np.random.seed(7)
    b = BatchedMLP(50)
    assert np.allclose(a.W1, b.W1)
    X = np.random.rand(50, 6)
    out_a = a.forward_batch(X)
    out_b = b.forward_batch(X)
    assert np.allclose(out_a, out_b)
    assert np.all((out_a >= 0) & (out_a <= 1))


def test_population_covers_new_axes():
    agents = personas.build_population(1500, 42, None, store.topic_map()["generic"])
    occ = {a["occupation_id"] for a in agents}
    assert len(occ) >= 40, f"only {len(occ)} occupations"
    for key, minimum in [
        ("ideology", 4), ("thought_process", 4), ("economic_status", 5),
        ("education_band", 6), ("personality_cluster", 6), ("settlement", 4),
    ]:
        assert len({a[key] for a in agents}) >= minimum, key
    # Every agent carries the full diversity record.
    for a in agents[:20]:
        for k in ("ideology", "thought_process", "economic_status", "education_band",
                  "personality", "settlement", "age_band"):
            assert k in a


def test_divisions_reconcile_to_totals():
    r = engine.run_simulation(
        "Affordable childcare for tier-2 mothers", n_agents=400, rounds=20, seed=9, fast=True
    )
    div = r["divisions"]
    total_adopted = sum(1 for a in r["agents"] if a["adopted"])
    tier_sum = sum(x["adopted"] for x in div["axes"]["tier"])
    assert tier_sum == total_adopted
    assert div["overall"]["n"] == 400
    # Leaders must clear the addressable-mass bar.
    for row in div["leaders"]:
        assert row["addressable"] >= 12
        assert row["axis"] not in ("occupation_id", "language")


def test_strategy_playbook_structure():
    r = engine.run_simulation(
        "Affordable childcare for tier-2 mothers", n_agents=500, rounds=20, seed=5, fast=True
    )
    pb = r["strategy"]
    for k in ("beachhead", "next_wave", "avoid", "channels", "plan", "falsifiers", "risks"):
        assert k in pb, k
    assert len(pb["plan"]) == 3
    # Protected axes never appear as a targeting beachhead line.
    for line in pb["beachhead"]["lines"]:
        assert "Hindu" not in line or "converted (" in line  # diagnostic guard is in builder
    assert pb["equity_note"]


def test_3000_agents_fast_and_deterministic():
    r1 = engine.run_simulation(
        "A ₹1.2 lakh electric scooter for tier-2 India", n_agents=3000, rounds=18, seed=77, fast=True
    )
    r2 = engine.run_simulation(
        "A ₹1.2 lakh electric scooter for tier-2 India", n_agents=3000, rounds=18, seed=77, fast=True
    )
    assert r1["population"] == 3000
    assert r1["provenance"]["belief_backend"] == "batched-numpy"
    assert r1["provenance"]["fingerprint"] == r2["provenance"]["fingerprint"]
    assert r1["summary"] == r2["summary"]
    assert r1["diversity"]["occupation_id"] >= 40
