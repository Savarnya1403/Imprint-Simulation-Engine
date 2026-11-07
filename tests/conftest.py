"""Test fixtures. Runs are small and fast on purpose: this is a maths test,
not a benchmark."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def brief() -> str:
    return "A ₹1.2 lakh electric scooter for tier-2 India"


@pytest.fixture(scope="session")
def run_small(brief):
    from app import engine

    return engine.run_simulation(brief, n_agents=80, rounds=16, seed=42, fast=True)
