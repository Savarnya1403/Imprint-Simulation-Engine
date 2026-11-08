"""FastAPI surface for Imprint Bharat."""
from __future__ import annotations

import threading
import zlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import (atlas, calibration, causal, content, engine, forecast, ingest, llm,
               modelcard, perception, personas, reasoning, sensitivity, store,
               uncertainty, validation)

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

TOPIC_CARDS = (
    "id", "label", "category", "motion", "price", "price_note", "unit",
    "benefits", "objections", "triggers", "hashtags", "platforms",
    "ground_reality", "malpractices", "pro_claims", "con_claims",
)

RUN_STORE: list[dict] = []
MAX_RUNS = 200

# Full run bundles for export. Bounded: agents are excluded, so each bundle is
# small. This is what makes a run citable rather than ephemeral.
from collections import OrderedDict
RUN_BUNDLES: "OrderedDict[str, dict]" = OrderedDict()
MAX_BUNDLES = 24


def _store_run(result: dict) -> None:
    entry = {
        "run_id": result.get("run_id"),
        "brief": result.get("brief"),
        "topic": (result.get("topic") or {}).get("id"),
        "topic_label": (result.get("topic") or {}).get("label"),
        "category": (result.get("topic") or {}).get("category"),
        "seed": result.get("seed"),
        "population": result.get("population"),
        "rounds": result.get("rounds"),
        "scenario": result.get("scenario"),
        "summary": result.get("summary"),
        "verdict": (result.get("summary") or {}).get("verdict"),
        "adoption": (result.get("summary") or {}).get("adoption"),
        "conversion": (result.get("summary") or {}).get("conversion"),
        "sentiment": (result.get("summary") or {}).get("sentiment"),
        "confidence": (result.get("summary") or {}).get("confidence"),
    }
    RUN_STORE.insert(0, entry)
    if len(RUN_STORE) > MAX_RUNS:
        RUN_STORE.pop()

    rid = result.get("run_id")
    if rid:
        keep = ("run_id", "provenance", "brief", "question", "topic", "scenario",
                "scenario_label", "seed", "population", "rounds", "tier_mix",
                "focus_state", "price", "timeline", "summary", "cognitive",
                "report", "params", "meta", "audit", "context", "precedents",
                "divisions", "diversity", "strategy")
        RUN_BUNDLES[rid] = {k: result.get(k) for k in keep if k in result}
        RUN_BUNDLES.move_to_end(rid)
        while len(RUN_BUNDLES) > MAX_BUNDLES:
            RUN_BUNDLES.popitem(last=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load TimesFM in the background so the first page paint is instant.
    threading.Thread(target=forecast.warm, name="timesfm-warm", daemon=True).start()
    yield


app = FastAPI(title="Imprint Bharat", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class SimulateRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    n_agents: int = Field(default=240, ge=40, le=3000)
    rounds: int = Field(default=36, ge=12, le=120)
    seed: int = Field(default=42, ge=0, le=10_000_000)
    tier_mix: dict[str, float] | None = None
    scenario: str = "base"
    focus_state: str | None = None
    price_override: float | None = Field(default=None, ge=0, le=100_000_000)
    question: str | None = Field(default=None, max_length=400)


class ChatRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    agent_id: str | None = None
    agent: dict[str, Any] | None = None
    message: str = Field(default="Would you buy this? Why?", max_length=600)
    seed: int = 42
    tier_mix: dict[str, float] | None = None
    state: str | None = None


class FocusRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    question: str = Field(default="Would you adopt this? Why or why not?", max_length=400)
    seed: int = 42
    state: str | None = None


class CausalRequest(BaseModel):
    topic_id: str = "ev-car"
    pre_end: int = Field(default=72, ge=18, le=90)
    horizon: int = Field(default=12, ge=3, le=24)
    sim_effect_pct: float = Field(default=0.0, ge=-100, le=200)
    sim_sd_pct: float = Field(default=8.0, ge=1, le=50)
    baseline_value: float = Field(default=1_000_000, ge=0)
    margin: float = Field(default=.35, ge=0, le=1)
    cost: float = Field(default=0.0, ge=0)
    discount: float = Field(default=.01, ge=0, le=.2)


class CalibrationRequest(BaseModel):
    budget: int = Field(default=24, ge=4, le=90)
    n_agents: int = Field(default=420, ge=120, le=900)
    rounds: int = Field(default=28, ge=12, le=48)
    seed: int = Field(default=11, ge=0, le=10_000_000)
    topics: list[str] | None = None
    reset: bool = False


class IngestRequest(BaseModel):
    text: str = Field(min_length=40, max_length=2_000_000)
    title: str = Field(max_length=300)
    source_id: str | None = Field(default=None, max_length=80)
    org: str = Field(default="Uploaded document", max_length=200)
    url: str = Field(default="", max_length=600)
    year: int | None = Field(default=None, ge=1900, le=2100)
    geo: str = Field(default="India", max_length=80)
    dimension: str = Field(default="document", max_length=40)
    tags: list[str] = Field(default_factory=list)
    confidence: str = Field(default="medium", max_length=20)
    chunk_chars: int = Field(default=1400, ge=300, le=6000)


class ReasonRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    n_agents: int = Field(default=240, ge=40, le=1600)
    rounds: int = Field(default=36, ge=12, le=96)
    seed: int = Field(default=42, ge=0, le=10_000_000)
    tier_mix: dict[str, float] | None = None
    scenario: str = "base"
    focus_state: str | None = None
    question: str | None = Field(default=None, max_length=400)
    replicates: int = Field(default=3, ge=1, le=6)


class ScenarioRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    n_agents: int = Field(default=200, ge=40, le=1600)
    rounds: int = Field(default=36, ge=12, le=120)
    seed: int = 42
    tier_mix: dict[str, float] | None = None
    focus_state: str | None = None


class RobustnessRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    n_agents: int = Field(default=180, ge=40, le=1200)
    rounds: int = Field(default=24, ge=12, le=60)
    seed: int = Field(default=42, ge=0, le=10_000_000)
    tier_mix: dict[str, float] | None = None
    scenario: str = "base"
    focus_state: str | None = None
    seeds: int = Field(default=5, ge=2, le=12)
    param_draws: int = Field(default=5, ge=2, le=16)
    target_conversion: float = Field(default=.50, ge=0, le=1)


class SensitivityRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    metric: str = Field(default="conversion", pattern="^(conversion|adoption|sentiment)$")
    n_agents: int = Field(default=150, ge=40, le=800)
    rounds: int = Field(default=20, ge=12, le=48)
    seed: int = Field(default=42, ge=0, le=10_000_000)
    tier_mix: dict[str, float] | None = None
    scenario: str = "base"
    focus_state: str | None = None
    n_base: int = Field(default=6, ge=4, le=32)


@app.get("/")
def index():
    target = STATIC / "index.html"
    if not target.exists():
        return JSONResponse({"ok": False, "error": "static/index.html not built yet"}, status_code=404)
    return FileResponse(target)


@app.get("/studio")
def studio():
    target = STATIC / "studio.html"
    if not target.exists():
        return JSONResponse({"ok": False, "error": "static/studio.html not built yet"}, status_code=404)
    return FileResponse(target)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "imprint-bharat",
        "version": "0.1.0",
        "simulation_engine": "Imprint Reasoning Core v2",
        "forecast": forecast.status(),
        "topics": len(store.topics()),
        "agents_possible": 3000,
        "context": {"sources": len(atlas.sources()), "nodes": len(atlas.all_nodes())},
        "calibration": calibration.load_params(),
        "llm": llm.status(),
        "disclaimer": "Synthetic rehearsal, not a representative survey.",
    }


def _topic_cards() -> list[dict]:
    out = []
    for t in store.topics():
        card = {k: t[k] for k in TOPIC_CARDS if k in t}
        card["history_months"] = len((t.get("history") or {}).get("values") or [])
        card["evidence"] = len(t.get("evidence_ids") or [])
        out.append(card)
    return out


@app.get("/api/meta")
def meta():
    ev = store.evidence()
    return {
        "brand": {
            "name": "Imprint",
            "product": "Bharat",
            "tagline": "Consumer intelligence for the other 1.4 billion.",
            "descriptor": "An agent-based rehearsal of how India actually decides.",
        },
        "topics": _topic_cards(),
        "scenarios": engine.SCENARIOS,
        "tiers": store.tiers(),
        "biases": sorted(store.biases(), key=lambda b: b["id"]),
        "states": [
            {
                "name": s["name"],
                "region": s["region"],
                "population_m": s["population_m"],
                "internet_pct": s["internet_pct"],
                "cities": s["cities"],
                "map_name": s.get("map_name", s["name"]),
            }
            for s in store.states()
        ],
        "archetypes": [
            {"id": a["id"], "label": a["label"], "short": a["short"], "category": a["category"], "tiers": a["tiers"]}
            for a in store.archetypes()
        ],
        "evidence": ev,
        "evidence_count": len(ev),
        "forecast": forecast.status(),
        "method_note": (
            "Synthetic population calibrated to public state, tier, income, digital-access and "
            "occupation distributions. Behaviour is modelled with explicit, auditable parameters. "
            "This is a rehearsal, not a poll and not a forecast of individuals."
        ),
        "disclaimer": (
            "Imprint Bharat is a synthetic simulation. It is not a representative survey and its "
            "confidence score is not a sampling error. Use it to stress-test a hypothesis, then "
            "validate with real people."
        ),
    }


@app.get("/api/runs")
def list_runs(limit: int = Query(default=50, ge=1, le=200)):
    return {"runs": RUN_STORE[:limit]}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        result = engine.run_simulation(
            req.brief,
            n_agents=req.n_agents,
            rounds=req.rounds,
            seed=req.seed,
            tier_mix=req.tier_mix,
            scenario=req.scenario,
            focus_state=req.focus_state,
            price_override=req.price_override,
            question=req.question,
        )
        _store_run(result)
        return result
    except Exception as exc:  # pragma: no cover - surface a useful message
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/forecast")
def forecast_endpoint(
    topic_id: str = Query(default="ev-car"),
    brief: str | None = Query(default=None),
    horizon: int = Query(default=12, ge=3, le=36),
    model: str = Query(default="auto", pattern="^(auto|timesfm|fallback)$"),
):
    try:
        return forecast.forecast_topic(topic_id=topic_id, horizon=horizon, brief=brief, model=model)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/api/focus-group")
def focus_group(req: FocusRequest):
    result = engine.run_simulation(
        req.brief, n_agents=160, rounds=24, seed=req.seed, focus_state=req.state, question=req.question
    )
    return {
        "brief": req.brief,
        "topic": result["topic"],
        "question": req.question,
        "group": result["focus_group"],
        "summary": result["summary"],
        "panel": result["panel"],
        "agents": [a for a in result["agents"] if a["id"] in set(result["panel"])],
        "disclaimer": result["meta"]["data_note"],
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    topic = store.pick_topic(req.brief)
    tier_mix = req.tier_mix or {1: .10, 2: .15, 3: .28, 4: .47}
    population = personas.build_population(240, req.seed, tier_mix, topic, req.state)
    # Prefer the exact citizen snapshot from the run. Rebuilding the population is
    # only a fallback; it must never silently answer as a different person.
    agent = req.agent if req.agent and req.agent.get("traits") else None
    if agent is None:
        agent = next((a for a in population if a["id"] == req.agent_id), None)
    if agent is None and req.agent_id:
        try:
            idx = int(req.agent_id.replace("a", "")) % len(population)
            agent = population[idx]
        except Exception:
            agent = None
    if agent is None:
        agent = population[0]
    rng = __import__("random").Random((zlib.crc32(req.message.encode()) ^ req.seed) & 0xFFFFFFFF)
    reply = content.chat_reply(agent, req.message, topic, rng)
    llm_reply = llm.generate(
        f"Citizen: {agent['name']}, {agent['age']}, {agent['occupation']} in {agent['city']} (tier {agent['tier']}). "
        f"Topic: {topic['label']} priced at {topic.get('price')} {topic.get('unit')}. "
        f"Question: {req.message}\n"
        f"Answer as this citizen in 2 short sentences. Be specific about money, trust and local conditions. No labels, no markdown.",
        max_tokens=90, temperature=0.8,
        system="You are a realistic Indian consumer speaking in first person. Never repeat the prompt. Never use bullet points.",
    )
    if llm_reply:
        reply["reply"] = llm_reply
        reply["llm_used"] = True
    else:
        reply["llm_used"] = False
    reply["llm"] = llm.status()
    reply["agent"] = {
        "id": agent["id"],
        "name": agent["name"],
        "age": agent["age"],
        "gender": agent["gender"],
        "city": agent["city"],
        "state": agent["state"],
        "tier": agent["tier"],
        "occupation": agent["occupation"],
        "income_monthly": agent["income_monthly"],
        "household_income": agent["household_income"],
        "language": agent["language"],
        "look": agent["look"],
        "quote": agent["quote"],
        "bio": agent["bio"],
        "biases": dict(sorted(agent["biases"].items(), key=lambda kv: -kv[1])[:5]),
    }
    reply["topic"] = {"id": topic["id"], "label": topic["label"], "price": topic.get("price", 0), "unit": topic.get("unit", "")}
    reply["suggested"] = [
        "What would make you switch?",
        "Who do you trust on this?",
        "What does it cost your household?",
        "What would you tell your neighbour?",
    ]
    return reply


@app.post("/api/scenarios")
def scenarios(req: ScenarioRequest):
    curves = []
    for s in engine.SCENARIOS:
        r = engine.run_simulation(
            req.brief, n_agents=req.n_agents, rounds=req.rounds, seed=req.seed,
            tier_mix=req.tier_mix, scenario=s["id"], focus_state=req.focus_state,
        )
        curves.append({
            "id": s["id"],
            "label": s["label"],
            "desc": s["desc"],
            "icon": s["icon"],
            "adoption": r["summary"]["adoption"],
            "conversion": r["summary"]["conversion"],
            "sentiment": r["summary"]["sentiment"],
            "verdict": r["summary"]["verdict"],
            "series": [x["adoption"] for x in r["timeline"]],
            "conversion_series": [x["conversion"] for x in r["timeline"]],
        })
    baseline = curves[0]
    for c in curves:
        c["delta_adoption"] = round((c["adoption"] - baseline["adoption"]) * 100, 2)
    return {"brief": req.brief, "topic": store.pick_topic(req.brief)["label"], "curves": curves}


@app.post("/api/reason")
def reason(req: ReasonRequest):
    try:
        return reasoning.deliberate(
            req.brief,
            n_agents=req.n_agents,
            rounds=req.rounds,
            seed=req.seed,
            tier_mix=req.tier_mix,
            scenario=req.scenario,
            focus_state=req.focus_state,
            question=req.question,
            replicates=req.replicates,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


class StrategyRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    n_agents: int = Field(default=800, ge=40, le=3000)
    rounds: int = Field(default=36, ge=12, le=72)
    seed: int = Field(default=42, ge=0, le=10_000_000)
    tier_mix: dict[str, float] | None = None
    scenario: str = "base"
    focus_state: str | None = None


@app.post("/api/strategy")
def strategy_endpoint(req: StrategyRequest):
    """Run (fast) then derive the GTM playbook from its divisions."""
    try:
        from . import strategy as _strategy

        result = engine.run_simulation(
            req.brief,
            n_agents=req.n_agents,
            rounds=req.rounds,
            seed=req.seed,
            tier_mix=req.tier_mix,
            scenario=req.scenario,
            focus_state=req.focus_state,
            fast=True,
        )
        _store_run(result)
        pb = _strategy.playbook(result)
        return {
            "run_id": result.get("run_id"),
            "brief": req.brief,
            "population": req.n_agents,
            "rounds": req.rounds,
            "topic": result.get("topic"),
            "summary": result.get("summary"),
            "divisions": result.get("divisions"),
            "diversity": result.get("diversity"),
            "strategy": pb,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/strategy/{run_id}")
def strategy_for_run(run_id: str):
    bundle = RUN_BUNDLES.get(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Run not found or expired (last 24 kept).")
    try:
        from . import strategy as _strategy

        # Bundle retains divisions/report/timeline; playbook can rebuild from them.
        stub = {
            "topic": bundle.get("topic"),
            "summary": bundle.get("summary"),
            "report": bundle.get("report"),
            "timeline": bundle.get("timeline"),
            "divisions": bundle.get("divisions"),
            "agents": [],
        }
        return {"run_id": run_id, "strategy": _strategy.playbook(stub)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/evidence")
def evidence(q: str | None = None, topic_id: str | None = None, domain: str | None = None):
    rows = store.evidence()
    topic = store.topic_map().get(topic_id) if topic_id else None
    if topic:
        wanted = set(topic.get("evidence_ids") or [])
        rows = [e for e in rows if e["id"] in wanted or topic_id in (e.get("topics") or [])]
    if domain:
        rows = [e for e in rows if e["domain"].lower() == domain.lower()]
    if q:
        needle = q.lower()
        rows = [
            e for e in rows
            if needle in " ".join(str(v) for v in e.values()).lower()
        ]
    return {"count": len(rows), "evidence": rows, "domains": sorted({e["domain"] for e in store.evidence()})}


@app.get("/api/atlas")
def atlas_stats():
    try:
        return atlas.stats_for_ui()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/atlas/search")
def atlas_search(
    q: str = Query(default=""),
    dimension: str | None = Query(default=None),
    type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    rows = atlas.search(q, dimension=dimension, type=type, limit=limit)
    return {
        "query": q,
        "count": len(rows),
        "results": rows,
        "dimensions": atlas.dimensions(),
        "note": "Retrieved context nodes are inspectable. Derived nodes are modelled, not observed.",
    }


@app.get("/api/atlas/audit")
def atlas_audit():
    result = atlas.audit()
    result["corpus"] = ingest.stats()
    return result


@app.get("/api/precedents")
def precedent_library():
    rows = [perception.summarise(c) for c in perception.cases()]
    return {
        "count": len(rows),
        "cases": rows,
        "days": perception.raw().get("days"),
        "base_rates": perception.base_rates(),
        "provenance_note": perception.raw().get("provenance_note"),
        "note": (
            "Precedents are reconstructed perception arcs from public reporting. They are "
            "illustrative, not measured panels and not causal estimates."
        ),
    }


@app.get("/api/precedents/retrieve")
def precedent_retrieve(
    q: str = Query(default=""),
    topic_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    k: int = Query(default=4, ge=1, le=8),
):
    rows = perception.retrieve(q, topic_id=topic_id, category=category, k=k)
    return {
        "query": q,
        "count": len(rows),
        "cases": rows,
        "base_rates": perception.base_rates(),
        "note": (
            "Similarity is lexical and recency-weighted, not semantic embedding. "
            "Use these as analogies and wide priors."
        ),
    }


@app.get("/api/causal")
def causal_analysis(
    topic_id: str = Query(default="ev-car"),
    pre_end: int = Query(default=72, ge=18, le=90),
    horizon: int = Query(default=12, ge=3, le=24),
    sim_effect_pct: float = Query(default=0.0, ge=-100, le=200),
    sim_sd_pct: float = Query(default=8.0, ge=1, le=50),
    baseline_value: float = Query(default=1_000_000, ge=0),
    margin: float = Query(default=.35, ge=0, le=1),
    cost: float = Query(default=0.0, ge=0),
    discount: float = Query(default=.01, ge=0, le=.2),
):
    try:
        return causal.analyse(
            topic_id=topic_id, pre_end=pre_end, horizon=horizon,
            sim_effect_pct=sim_effect_pct, sim_sd_pct=sim_sd_pct,
            baseline_value=baseline_value, margin=margin, cost=cost, discount=discount,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/causal/topics")
def causal_topics():
    out = []
    for t in store.topics():
        vals = (t.get("history") or {}).get("values") or []
        out.append({
            "id": t["id"], "label": t["label"], "category": t.get("category", ""),
            "unit": t.get("unit", ""), "points": len(vals),
            "price": t.get("price", 0),
        })
    return {"topics": out, "default_pre_end": 72, "default_horizon": 12}


@app.get("/api/calibration")
def calibration_status():
    return calibration.status(full=True)


@app.post("/api/calibration")
def calibration_set(params: dict[str, float]):
    try:
        out = calibration.set_params(params)
        return {"ok": True, "params": out}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/api/calibration/run")
def calibration_run(req: CalibrationRequest):
    try:
        return calibration.run_calibration(
            budget=req.budget, n_agents=req.n_agents, rounds=req.rounds,
            seed=req.seed, topics=req.topics, reset=req.reset,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/corpus")
def corpus_stats():
    return ingest.stats()


@app.post("/api/ingest")
def corpus_ingest(req: IngestRequest):
    try:
        result = ingest.ingest_text(
            req.text, req.title, source_id=req.source_id, org=req.org, url=req.url,
            year=req.year, geo=req.geo, dimension=req.dimension, tags=req.tags,
            confidence=req.confidence, chunk_chars=req.chunk_chars,
        )
        return {"ok": True, "result": result, "corpus": ingest.stats()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/llm")
def llm_status():
    return llm.status()


@app.get("/api/topics/{topic_id}")
def topic_detail(topic_id: str):
    t = store.topic_map().get(topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Unknown topic")
    return t


# ---------------------------------------------------------------------------
# Research surface: model card, validation, uncertainty, sensitivity, export
# ---------------------------------------------------------------------------

@app.get("/api/model-card")
def model_card():
    try:
        return modelcard.card()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/validation")
def validation_battery(deep: bool = Query(default=False)):
    try:
        return validation.battery(deep=deep)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/api/robustness")
def robustness(req: RobustnessRequest):
    try:
        return uncertainty.ensemble(
            req.brief, n_agents=req.n_agents, rounds=req.rounds,
            scenario=req.scenario, focus_state=req.focus_state, tier_mix=req.tier_mix,
            seeds=req.seeds, param_draws=req.param_draws, seed0=req.seed,
            target_conversion=req.target_conversion,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/api/sensitivity")
def sensitivity_scan(req: SensitivityRequest):
    try:
        return sensitivity.sobol(
            req.brief, metric=req.metric, n_base=req.n_base, n_agents=req.n_agents,
            rounds=req.rounds, scenario=req.scenario, focus_state=req.focus_state,
            tier_mix=req.tier_mix, seed=req.seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/runs/{run_id}")
def run_bundle(run_id: str):
    bundle = RUN_BUNDLES.get(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Run not found or evicted from memory.")
    return bundle


def _fmt_pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _export_md(bundle: dict) -> str:
    summary = bundle.get("summary") or {}
    prov = bundle.get("provenance") or {}
    topic = bundle.get("topic") or {}
    params = bundle.get("params") or prov.get("params") or {}
    lines = [
        f"# Imprint run · {bundle.get('run_id', '—')}",
        "",
        f"**Brief.** {bundle.get('brief', '—')}",
        "",
        f"**Verdict.** {summary.get('verdict', '—')} "
        f"(confidence {summary.get('confidence', '—')})",
        "",
        summary.get("headline", ""),
        "",
        "## What the simulation reports",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Adoption | {_fmt_pct(summary.get('adoption'))} of {bundle.get('population', '—')} agents |",
        f"| Conversion | {_fmt_pct(summary.get('conversion'))} of addressable |",
        f"| Awareness | {_fmt_pct(summary.get('awareness'))} |",
        f"| Sentiment | {summary.get('sentiment', '—')} |",
        f"| Addressable pool | {summary.get('addressable', '—')} |",
        f"| Rejection rate | {_fmt_pct(summary.get('rejection_rate'))} |",
        f"| Tipping point | day {summary.get('tipping_point') or '—'} |",
        "",
        "## Provenance",
        "",
        f"- Engine: `{prov.get('engine', '—')}`",
        f"- Fingerprint: `{prov.get('fingerprint', '—')}`",
        f"- Seed: `{bundle.get('seed', '—')}`",
        f"- Scenario: `{bundle.get('scenario', 'base')}`",
        f"- Population / rounds: {bundle.get('population', '—')} / {bundle.get('rounds', '—')}",
        f"- Parameters: " + ", ".join(f"`{k}={v}`" for k, v in sorted(params.items())) if params else "- Parameters: —",
        "",
        "## Timeline",
        "",
        "| Day | Awareness | Adoption | Conversion | New | Sentiment | Trust |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in (bundle.get("timeline") or []):
        lines.append(
            f"| {row.get('day')} | {_fmt_pct(row.get('awareness'))} | "
            f"{_fmt_pct(row.get('adoption'))} | {_fmt_pct(row.get('conversion'))} | "
            f"{row.get('new', '—')} | {row.get('sentiment', '—')} | {row.get('trust', '—')} |"
        )
    cog = bundle.get("cognitive") or {}
    if cog:
        lines += [
            "",
            "## Cognitive layer",
            "",
            f"- Dual-process (deliberate weight): {cog.get('dual_process_mean', '—')}",
            f"- Granovetter threshold mean: {cog.get('threshold_mean', '—')}",
            f"- Present-bias weight: {cog.get('present_bias_mean', '—')}",
            f"- Trust repair half-life: {cog.get('trust_repair_days', '—')} days",
            f"- Belief backend: {prov.get('belief_backend', cog.get('belief_backend', '—'))}",
        ]
    div = bundle.get("divisions") or {}
    if div.get("leaders"):
        lines += ["", "## Divisions (leaders by conversion)", ""]
        for row in div["leaders"][:8]:
            lines.append(
                f"- {row.get('axis')}: {row.get('label')} — {row.get('conversion', 0) * 100:.0f}% converted "
                f"({row.get('adopted')}/{row.get('addressable')}, n={row.get('n')}, lead {row.get('lead_days')})"
            )
    st = bundle.get("strategy") or {}
    if st and not st.get("error"):
        lines += ["", "## GTM playbook", ""]
        lines.append(f"- Beachhead tier: {st.get('beachhead', {}).get('tier', '—')}")
        for line_ in st.get("beachhead", {}).get("lines", [])[:4]:
            lines.append(f"- {line_}")
        lines.append(f"- Top blocker: {st.get('top_blocker', '—')}")
        lines.append(f"- Channels: {', '.join(st.get('channels', []))}")
        for p in st.get("plan", []):
            lines.append(f"- {p.get('window')}: {p.get('goal')} — metric: {p.get('metric')}; stop: {p.get('stop_rule')}")
    lines += [
        "",
        "## Limits",
        "",
        "This is a synthetic rehearsal, not a survey or a causal estimate. "
        "Every number above should travel with its uncertainty interval and the "
        "falsifier that would overturn it. See `/api/model-card`.",
        "",
    ]
    return "\n".join(lines)


def _timeline_csv(bundle: dict) -> str:
    rows = bundle.get("timeline") or []
    cols = ["day", "awareness", "adoption", "conversion", "addressable", "new",
            "rejected", "sentiment", "polarization", "trust", "wom"]
    out = [",".join(cols)]
    for r in rows:
        out.append(",".join(str(r.get(c, "")) for c in cols))
    return "\n".join(out) + "\n"


@app.get("/api/runs/{run_id}/export")
def export_run(run_id: str, format: str = Query(default="md")):
    bundle = RUN_BUNDLES.get(run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Run not found or evicted from memory.")
    fmt = (format or "md").lower().strip()
    if fmt == "json":
        body = JSONResponse(bundle).body
        media = "application/json"
        ext = "json"
    elif fmt == "csv":
        body = _timeline_csv(bundle).encode("utf-8")
        media = "text/csv"
        ext = "csv"
    elif fmt in ("md", "markdown"):
        body = _export_md(bundle).encode("utf-8")
        media = "text/markdown"
        ext = "md"
    else:
        raise HTTPException(status_code=400, detail="format must be md, json or csv")
    return Response(
        content=body, media_type=media,
        headers={"Content-Disposition": f'attachment; filename="imprint-{run_id}.{ext}"'},
    )

