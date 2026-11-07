"""HTTP surface: the research endpoints and the export contract."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def run_id(client, brief):
    res = client.post("/api/simulate", json={
        "brief": brief, "n_agents": 80, "rounds": 14, "seed": 42,
    })
    assert res.status_code == 200, res.text
    return res.json()["run_id"]


def test_health(client):
    d = client.get("/api/health").json()
    assert d["ok"] is True


def test_model_card(client):
    d = client.get("/api/model-card").json()
    assert d["identity"]["engine"] == "imprint-core/3.1"
    assert d["intended_use"] and d["out_of_scope"] and d["limitations"]
    assert d["validation"]["known_answer"]["score"] == 1.0


def test_validation(client):
    d = client.get("/api/validation").json()
    assert d["summary"]["known_answer_score"] == 1.0
    assert d["backtest"]["n_topics"] >= 10


def test_topic_detail(client):
    ok = client.get("/api/topics/ev-scooter")
    assert ok.status_code == 200
    assert ok.json()["id"] == "ev-scooter"
    assert client.get("/api/topics/nope").status_code == 404


def test_run_bundle_roundtrip(client, run_id):
    d = client.get(f"/api/runs/{run_id}").json()
    assert d["run_id"] == run_id
    assert d["provenance"]["fingerprint"]
    assert client.get("/api/runs/does-not-exist").status_code == 404


@pytest.mark.parametrize("fmt,marker", [
    ("md", "## Provenance"),
    ("json", "\"provenance\""),
    ("csv", "day,awareness"),
])
def test_export_formats(client, run_id, fmt, marker):
    res = client.get(f"/api/runs/{run_id}/export", params={"format": fmt})
    assert res.status_code == 200
    assert marker in res.text
    assert "attachment" in res.headers["content-disposition"]


def test_export_rejects_unknown_format(client, run_id):
    assert client.get(f"/api/runs/{run_id}/export", params={"format": "xls"}).status_code == 400


def test_robustness_bounds(client, brief):
    res = client.post("/api/robustness", json={
        "brief": brief, "n_agents": 60, "rounds": 12, "seed": 5,
        "seeds": 2, "param_draws": 2,
    })
    assert res.status_code == 200, res.text
    d = res.json()
    c = d["conversion"]
    assert d["runs"] == 4
    assert c["p10"] <= c["p50"] <= c["p90"]
    assert 0 <= d["decision"]["p_at_or_above_target"] <= 1
    assert 0 <= d["variance"]["epistemic_share"] <= 1


def test_sensitivity_endpoint(client, brief):
    res = client.post("/api/sensitivity", json={
        "brief": brief, "n_agents": 60, "rounds": 12, "seed": 5, "n_base": 4,
    })
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["available"] in (True, False)
    if d["available"]:
        assert d["indices"] and d["evaluations"] == 4 * (6 + 2)
        assert 0 <= d["indices"][0]["st"] <= 1
