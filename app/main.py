"""FastAPI surface for Imprint Simulation Engine."""
from __future__ import annotations

import threading
import zlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel, Field

from . import atlas, calibration, causal, content, engine, forecast, ingest, llm, perception, personas, reasoning, store
from . import query_interpreter, emergence

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

TOPIC_CARDS = (
    "id", "label", "category", "motion", "price", "price_note", "unit",
    "benefits", "objections", "triggers", "hashtags", "platforms",
    "ground_reality", "malpractices", "pro_claims", "con_claims",
)

RUN_STORE: list[dict] = []
MAX_RUNS = 200

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
    n_agents: int = Field(default=240, ge=40, le=1600)
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
    n_agents: int = Field(default=240, ge=40, le=800)
    rounds: int = Field(default=36, ge=12, le=96)
    seed: int = Field(default=42, ge=0, le=10_000_000)
    tier_mix: dict[str, float] | None = None
    scenario: str = "base"
    focus_state: str | None = None
    question: str | None = Field(default=None, max_length=400)
    replicates: int = Field(default=3, ge=1, le=6)


class ScenarioRequest(BaseModel):
    brief: str = Field(default="A ₹1.2 lakh electric scooter for tier-2 India", max_length=400)
    n_agents: int = Field(default=200, ge=40, le=800)
    rounds: int = Field(default=36, ge=12, le=120)
    seed: int = 42
    tier_mix: dict[str, float] | None = None
    focus_state: str | None = None


class QueryRequest(BaseModel):
    """Universal simulation query — accepts any natural language question or hypothesis."""
    query: str = Field(
        min_length=10,
        max_length=800,
        description="Any natural language query. Examples: "
        "'How would US senators vote on UBI?', "
        "'Will a 4-day work week reduce productivity?', "
        "'How does demonetization affect rural India?'",
    )
    seed: int = Field(default=42, ge=0, le=10_000_000)
    n_agents: Optional[int] = Field(default=None, ge=40, le=1600, description="Override agent count (default: auto from spec)")
    deep_reason: bool = Field(default=True, description="Run full deliberation + Claude analysis")
    all_scenarios: bool = Field(default=False, description="Run all 5 scenarios (slower but richer)")


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
    llm_st = llm.status()
    return {
        "ok": True,
        "service": "imprint-simulation-engine",
        "version": "2.0.0",
        "simulation_engine": "Imprint Universal Reasoning Core v2",
        "capabilities": {
            "universal_query": True,
            "india_market": True,
            "dynamic_domains": ["market", "politics", "social", "finance", "technology", "organizational", "historical", "science", "custom"],
            "emergence_metrics": True,
            "awi_tracking": True,
            "coalition_tracking": True,
            "concordia_gm": True,
            "timesfm_forecast": True,
            "claude_deliberation": llm_st.get("available") and llm_st.get("backend") == "anthropic",
        },
        "forecast": forecast.status(),
        "topics": len(store.topics()),
        "agents_possible": 1600,
        "context": {"sources": len(atlas.sources()), "nodes": len(atlas.all_nodes())},
        "calibration": calibration.load_params(),
        "llm": llm_st,
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
        result = reasoning.deliberate(
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
        # Enrich with Claude analysis if available
        return reasoning.claude_enrich(result, query=req.brief, domain="market")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/api/query")
def universal_query(req: QueryRequest):
    """Universal simulation endpoint — accepts any natural language query.

    The engine:
    1. Interprets the query with Claude Opus 4.7 to build a SimulationSpec
    2. Generates an appropriate agent population (India or universal)
    3. Runs the multi-agent simulation with the full reasoning loop
    4. Computes Emergence World AWI metrics
    5. Returns a Claude-enriched analysis memo

    Examples:
      POST /api/query {"query": "How will Indian farmers react to crop insurance mandate?"}
      POST /api/query {"query": "Will a 4-day work week be adopted by Silicon Valley firms?"}
      POST /api/query {"query": "How does social media ban affect teenage wellbeing?"}
    """
    import time
    t0 = time.perf_counter()

    try:
        # --- Step 1: Interpret query → SimulationSpec ---
        spec = query_interpreter.interpret(req.query)
        domain = spec.get("domain", "market")
        is_india = spec.get("is_india_context", False)

        # --- Step 2: Build simulation kwargs from spec ---
        sim_kwargs = query_interpreter.spec_to_simulate_kwargs(spec)
        n = req.n_agents if req.n_agents else sim_kwargs.get("n_agents", 240)
        rounds = sim_kwargs.get("rounds", 36)
        brief = sim_kwargs.get("brief", req.query)

        # --- Step 3: Run base simulation ---
        base_result = engine.run_simulation(
            brief,
            n_agents=n,
            rounds=rounds,
            seed=req.seed,
            scenario="base",
            _simulation_spec=spec if not is_india else None,
        )
        _store_run(base_result)

        # --- Step 4: Run all scenarios if requested ---
        scenario_results = None
        if req.all_scenarios:
            scenario_results = []
            spec_scenarios = spec.get("scenarios", [])[:5]
            for sc in spec_scenarios:
                sc_id = sc.get("id", "base")
                try:
                    r = engine.run_simulation(
                        brief, n_agents=n, rounds=rounds, seed=req.seed,
                        scenario=sc_id if sc_id in engine.SCENARIO_MODS else "base",
                        fast=True,
                    )
                    scenario_results.append({
                        "scenario": sc,
                        "adoption": r["summary"]["adoption"],
                        "conversion": r["summary"]["conversion"],
                        "sentiment": r["summary"]["sentiment"],
                        "verdict": r["summary"]["verdict"],
                    })
                except Exception:
                    pass

        # --- Step 5: Compute AWI emergence metrics ---
        stances = [float(a.get("stance", 0.5)) for a in (base_result.get("agents") or [])]
        adopted = [bool(a.get("adopted")) for a in (base_result.get("agents") or [])]

        energy_sys = emergence.EnergySystem(n=len(stances), seed=req.seed)
        coalition_tracker = emergence.CoalitionTracker()
        em_detector = emergence.EmergenceDetector()

        # Feed timeline into emergence detector
        for i, row in enumerate(base_result.get("timeline", [])):
            em_detector.observe(
                round_num=i,
                adoption_rate=float(row.get("adoption", 0)),
                stances=stances,
                energy_sys=energy_sys,
            )

        awi = emergence.compute_awi(
            agents=base_result.get("agents", []),
            adopted_mask=adopted,
            stances=stances,
            energy_sys=energy_sys,
            coalition_tracker=coalition_tracker,
            round_num=rounds,
            total_rounds=rounds,
            emergence_detector=em_detector,
        )

        # --- Step 6: Deep deliberation + Claude enrichment ---
        deliberation = None
        if req.deep_reason:
            try:
                deliberation = reasoning.deliberate(
                    brief,
                    n_agents=n,
                    rounds=rounds,
                    seed=req.seed,
                    scenario="base",
                    replicates=2,
                )
                deliberation = reasoning.claude_enrich(deliberation, query=req.query, domain=domain)

                # Inject domain-specific hypotheses from Claude if available
                claude_hyps = reasoning.generate_domain_hypotheses(req.query, domain, base_result)
                if claude_hyps:
                    deliberation["claude_hypotheses"] = claude_hyps
            except Exception as exc:
                deliberation = {"error": f"{type(exc).__name__}: {exc}"}

        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        return {
            "query": req.query,
            "domain": domain,
            "is_india_context": is_india,
            "simulation_spec": {
                "interpreter_mode": spec.get("interpreter_mode", "deterministic"),
                "brief": brief,
                "motion": spec.get("motion", ""),
                "language": spec.get("language", "en"),
                "population_context": (spec.get("population_spec") or {}).get("context", ""),
                "segments": (spec.get("population_spec") or {}).get("segments", []),
                "scenarios_available": spec.get("scenarios", []),
                "hypotheses": spec.get("hypotheses", []),
            },
            "simulation_result": {
                "run_id": base_result.get("run_id"),
                "n_agents": n,
                "rounds": rounds,
                "summary": base_result.get("summary"),
                "topic": base_result.get("topic"),
                "timeline": base_result.get("timeline"),
                "encounters": base_result.get("encounters"),
            },
            "emergence_metrics": {
                "awi": awi.to_dict(),
                "awi_status": awi.status_label(),
                "emergence_events": em_detector.to_dict(),
                "energy": energy_sys.to_dict(),
            },
            "scenario_comparison": emergence.compare_scenarios(
                [base_result] + ([r for r in (scenario_results or [])
                                  if isinstance(r, dict) and "summary" in r])
            ) if scenario_results else None,
            "scenarios": scenario_results,
            "deliberation": deliberation,
            "llm": llm.status(),
            "elapsed_ms": elapsed_ms,
            "disclaimer": (
                "This is a synthetic simulation, not a representative survey or poll. "
                "Confidence scores are modelled stability metrics, not sampling errors. "
                "Use to stress-test hypotheses and decide what to validate with real data."
            ),
        }

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
def topic_detail(topic_id: str):
    t = store.topic_map().get(topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Unknown topic")
    return t
