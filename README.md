# Imprint Bharat

**A synthetic rehearsal of how India decides — across tier 1 to tier 4, 36 states and UTs, and the social rules that shape a purchase.**

Imprint Bharat is a local, auditable research instrument for testing a consumer or market decision before spending money on it. It combines:

- an agent-based simulation of up to 3,000 synthetic citizens across 48 occupations, stratified by state, tier, income, gender, age, digital access, religion, caste, ideology, thought process, economic band, schooling, settlement and Big Five personality — with a batched NumPy belief backend above 600 agents so 3,000 runs in seconds;
- a cited public-data context graph, so every agent carries inspectable sources;
- a reconstructed precedent library of Indian market decisions, used as a soft perception prior — not as rigid decision → outcome rules;
- Google TimesFM 3.0 for numeric forecasting and counterfactuals;
- conformal intervals, placebo tests, synthetic control, Bayesian combination and Monte Carlo decision distributions;
- a bounded self-calibration loop that tunes explicit simulator parameters against public category ranges and logs every adopted change.

## Start it

Python 3.10+ is required. The included environment uses 3.11.

```bash
cd imprint-bharat
./run.sh
```

Then open:

**http://127.0.0.1:7777**

The studio is at **http://127.0.0.1:7777/studio**.

Or run manually:

```bash
cd imprint-bharat
../.venv/bin/python -m uvicorn app.main:app --port 7777
```

Health check:

```bash
curl http://127.0.0.1:7777/api/health
```

`forecast.loaded: true` with `backend: timesfm3.mlx` means the foundation model is live. If the checkpoint or Apple-silicon MLX backend is unavailable, the app still runs and labels the forecast engine `fallback:damped-trend`. It never presents the fallback as TimesFM.

## The honest disclaimer

This is **a synthetic simulation, not a representative survey**. Its confidence number is a modelled stability score, **not a sampling error** and not a margin of polling error. It cannot tell you what "India thinks". It can help you:

- stress-test a hypothesis across segments you do not have in a room;
- find which objection, tier, state or supply constraint binds first;
- compare a decision against a no-decision counterfactual;
- see how similar past perceptions formed and decayed;
- decide what to validate with real people next.

The context graph is a curated seed, not a 10,000× trained corpus. `app/data/atlas.json` currently contains 64 sources, 147 curated facts, 6 regional packs, 16 norms, 19 category priors and 19 calibration anchors, plus derived state/tier/occupation/category nodes. The ingestion pipeline exists so the corpus can grow; it does not pretend the growth has already happened. Division analytics (`app/segments.py`) and the GTM playbook (`app/strategy.py`) are derived from the same run — no extra simulation — and `/api/strategy` returns the playbook on demand.

## What is in the box

| Path | Role |
| --- | --- |
| `app/engine.py` | Agent-based diffusion, appraisal, social graph, scenarios, run audit |
| `app/personas.py` | Stratified synthetic population |
| `app/content.py` | Posts, debate, focus-group and chat language |
| `app/atlas.py` | Sourced context graph, retrieval, per-agent priors, coverage audit |
| `app/perception.py` | Precedent retrieval, perception curves, soft priors |
| `app/causal.py` | TimesFM counterfactual, conformal, placebo, synthetic control, Bayes, Monte Carlo, NPV |
| `app/calibration.py` | Bounded coordinate search against public anchors, persisted history |
| `app/reasoning.py` | Visible deliberation: replicate, stress, challenge, revise, verify |
| `app/nn.py` | micrograd-style autograd + MLP; every agent is a small neural net |
| `app/cognition.py` | Prospect theory, mere exposure (neuroplasticity), Rogers diffusion, Bass p/q fit, bootstrap CIs, psychometrics |
| `app/memory.py` | Generative-Agents memory stream: retrieval (recency × importance × relevance) + reflection |
| `app/concordia.py` | Concordia-style Game Master: March & Olsen's three questions, GM-adjudicated Hinglish encounters |
| `app/mathcore.py` | Belief ODE (Euler/RK4), graph-Laplacian diffusion, TimesFM demand signal |
| `app/ingest.py` | PDF/HTML/CSV/JSON/TXT ingestion into the expandable corpus |
| `app/forecast.py` | TimesFM 3.0 loader, topic and arbitrary-series forecasts |
| `app/main.py` | FastAPI surface and static serving |
| `static/` | Landing page and studio UI |
| `tools/` | Reproducible seed generators for atlas, precedents, topics and map |

## How TimesFM makes a MiroFish-style simulator smarter

MiroFish is qualitative and narrative: LLM agents react on a simulated social platform. It is good at mechanism, objection and who-says-what. It has no native numeric baseline. TimesFM fills that gap.

1. **Grounded seeds.** Forecast search interest, price, category penetration or mention volume. Put the forecast and its quantile range into the seed document, so agents react to a quantified expectation rather than a vibe.
2. **Counterfactual baseline.** Forecast the "no decision" world. The difference between the observed series and that baseline is the estimated effect. In this repo that is `app/causal.py`.
3. **Cheap extension.** Log per-round simulation metrics (adoption, sentiment, polarisation). TimesFM can extrapolate those curves past the expensive LLM rounds.
4. **A numeric tool for the report agent.** The final report can cite a forecast with an interval instead of only narrative.
5. **Backtesting.** Replay past decisions and compare simulated curves with TimesFM's pre-decision forecast and with what actually happened.

Important limits: TimesFM learns patterns in a series; it does not know that a price cut, a ban or a festival happened. Its quantiles are forecast quantiles, **not causal intervals**. Short per-round simulation series are weak input. Treat the combination as a scenario instrument until it has been backtested on decisions whose outcomes you know.

### Repos to pair, and in what context

| Need | Repo / tool | Context |
| --- | --- | --- |
| Sentiment and public-opinion seeds | **BettaFish** | Same team as MiroFish; generates the sentiment reports that seed the simulation |
| Local/private stack | **MiroFish-Offline** | Neo4j + Ollama instead of cloud memory and APIs |
| Forecast baselines | **Amazon Chronos**, **Salesforce Moirai**, **Nixtla statsforecast** | Check whether TimesFM actually beats a simple seasonal baseline on your series |
| Finance and macro series | **OpenBB**, **yfinance**, **FRED API** | Feed TimesFM with market, rate and macro covariates |
| Search demand | **pytrends** | State-level Google Trends for category interest |
| Event and tone series | **GDELT** | News volume and tone around a decision |
| Causal measurement after the fact | **CausalImpact / pycausalimpact**, **DoWhy**, **EconML** | Measure what really happened against a counterfactual |
| Rule-based simulation rigor | **Mesa** | Cheap, reproducible agents alongside LLM agents |
| Backtesting a traded decision | **vectorbt** | Only when the decision is a portfolio or trade |
| Financial text | **FinGPT** | Financial-news sentiment features |
| Indian calendar and confounders | Your own dated calendar | Diwali, Eid, Holi, Navratri, wedding season, Budget, RBI MPC, GST changes, elections, monsoon, IPL, festive sales |

A sensible pipeline for a market decision:

```
data feeds → TimesFM baseline → quantified seed document → MiroFish / Imprint simulation
          → simulated metric curves → causal layer → backtest → decision memo
```

## Causal layer

The estimand is the average effect of a decision on a KPI over a horizon, relative to the no-decision counterfactual:

```
τ_t = E[Y_t(1) − Y_t(0) | treated],   t ≥ T0
T_h = Σ τ_t
```

`app/causal.py` implements:

- **TimesFM counterfactual** on the truncated pre-period.
- **Rolling-origin conformal intervals** for the cumulative effect. One-step residuals scaled by `sqrt(h)` are not enough; the interval uses cumulative h-step errors from pre-period origins. Coverage is diagnostic, not guaranteed under non-stationarity.
- **Placebo in time**: move the decision date into the pre-period and compare the observed cumulative effect against those placebo draws.
- **Synthetic control**: donor series from other categories, projected-gradient simplex weights, in-space placebos. This is a robustness check on category series, **not** a proper donor pool of untreated states.
- **Bayesian combination**: normal-normal update of the simulation prior with the data estimate. A disagreement flag means reconcile, not average.
- **Block bootstrap Monte Carlo**: residual paths around the counterfactual, cumulative and relative distributions, probability of a positive effect, CVaR.
- **NPV distribution**: monthly value × margin × relative effect, discounted, minus cost. Illustrative, not a valuation and excludes competitor response.
- **Synthetic-truth harness**: inject a known step into a trend + AR(1) + fat-tail DGP, run the pipeline many times, and report bias, RMSE and interval coverage. Current local run is around 86–88% coverage at a nominal 90% after the cumulative-error fix. That validates the machinery, not reality.

India-specific confounders to add before trusting a real estimate: dated festival dummies rather than month dummies, Union Budget, RBI MPC dates, GST rate changes, election periods, monsoon progress, FPI/FII flows, INR/USD, Brent, India VIX, IPL and festive sale events. Beware GDP/IIP back-revisions, informal-sector undercount and uneven state reporting.

## Precedents: learn perception softly

`app/data/precedents.json` contains 16 reconstructed Indian cases (Jio 2016, demonetisation, Maggi, WhatsApp privacy, Netflix mobile, Airtel minimum recharge, Patanjali, BYJU'S, Nano, Fair & Lovely, ONDC, UPI, GST, farm laws, ride-hailing surge, platform fees). Each has a perception arc from day −14 to +60, outcome range, mechanisms, segments and caveats.

The simulation does **not** learn "decision X caused outcome Y". With sixteen cases that would overfit. Instead:

1. **Retrieve** analogous cases by lexical similarity and recency.
2. **Prior**: their peak opposition and half-life produce a bounded trust-shock scale and recovery window.
3. **Expose** the adjustment and its caveats in the run report.
4. **Calibrate later**, when real outcome and perception data exist, against the simulation's own curves.

The arcs are reconstructed from public reporting. They are illustrative, not measured panels, not representative surveys, and not causal estimates.

## Self-calibration, stated honestly

The "self-improving" loop is **not** foundation-model fine-tuning. It is a bounded coordinate search over six explicit parameters:

```
ceiling_mult, price_sensitivity, social_mult, trust_weight, hazard_mult, atlas_strength
```

It scores fast simulations against public category ranges (7 high-addressability categories by default), adopts a change only if it lowers the normalised squared-error objective, and persists the run in `app/data/calibration.json`. The engine loads the adopted parameters on the next run. History is visible in the Calibration tab.

The anchors are analyst ranges derived from public industry, regulator and consulting sources. A good score means "consistent with these ranges under this objective", not "correct".

## Self-reasoning: what "70× better" actually means

There is no literal 70× multiplier in this repository. A simulation cannot buy a 70× accuracy guarantee by adding a module, and claiming one would be dishonest.

What exists is an **auditable deliberation loop** in `app/reasoning.py`:

```
frame → retrieve → simulate → replicate → stress → challenge → revise → verify
```

Each run then:

1. **Replicates** the brief on 3–6 extra seeds and reports verdict agreement and conversion CV.
2. **Stresses** two dominant weights by ±25% and counts verdict flips.
3. **Ranks competing explanations** (price, trust, supply, social proof, awareness) using objection text, category priors, trait correlations and retrieved precedents — each with a stated falsifier.
4. **Checks itself** on ten visible criteria: seed stability, assumption robustness, evidence coverage, precedent similarity, addressable sample size, objection concentration, causal-sign agreement, calibration visibility, hypothesis clarity and confidence inflation.
5. **Revises** the verdict and confidence. Error-level failures cap confidence; a scale call is downgraded to a test when the conclusion does not survive replication or stress; three or more failures trigger a reframe.
6. **Writes a decision memo** with the binding constraint, what would change its mind, and the next real-world test.
7. **Discloses limits** rather than hiding them.

The quality claim is inspectable behaviour: the system is allowed to lower its own confidence, disagree with its own causal check, and refuse to scale. The Reasoning tab shows every step, including the checks it failed. That is more useful than a multiplier you cannot audit, and it is the honest reading of "70× better" — many independent quality gates, not one magical factor.

## Generative encounters: Stanford × Concordia

Two research patterns are woven into the simulation (both Apache-2.0):

- **Generative Agents (Stanford, Park et al. 2023)** — `app/memory.py`. Each agent accumulates a timestamped memory stream; retrieval scores memories by recency × importance × relevance; a reflection step derives firm beliefs by the agent. The agent drawer shows MEMORY STREAM and REFLECTION entries alongside traits and biases.
- **Concordia Game Master (Google DeepMind)** — `app/concordia.py`. Agents don't just emit widgets; they meet (2–3 GM-adjudicated encounters per run). March & Olsen's three questions (*What kind of situation is this? What kind of person am I? What does a person such as I do here?*) frame each encounter; the GM resolves it in natural Hinglish with an outcome (convinced / sceptical / indifferent) that nudges stance. Encounters and reflections appear as **GENERATIVE ENCOUNTERS** cards in the World view and in each citizen file.

LLM policy: local tiny models (llama.cpp, `IMPRINT_LLM_LOCAL=1`) are opt-in for development; hosted OpenAI-compatible endpoints (`IMPRINT_LLM_BASE_URL`) get the full pipeline. If neither is set, every generative step falls back to a deterministic, seed-reproducible template — the simulation is never LLM-dependent.

## Cognitive science: what improved under the expert debate

A research panel of one examines the engine; the winning changes landed in `app/cognition.py` and the decision loop:

1. **Prospect Theory (Kahneman & Tversky)** — value is reference-dependent and S-shaped; λ = 2.25, α = 0.88. Losses loom ~2.25× larger than gains. The S-curve is visualised in the Perception tab.
2. **Mere Exposure / Neuroplasticity (Zajonc 1980; Hebb 1949)** — cumulative exposures rewire preference. `mere_exposure_bonus(e)` adds a saturating, logarithmic habituation lift to each agent's adoption probability; `consolidation_rate` reports how many agents are past the memory threshold. The curve is in the Perception tab.
3. **Rogers Diffusion + Bass model (Rogers 1962; Bass 1969)** — adopters are classified into innovators / early adopters / majority waves by rank-order of adoption day; Bass p (innovator) and q (imitation) are fitted on the simulated curve by grid search. R² < 0.3 is reported as "weak fit" — honest, not hidden.
4. **Psychometrics** — Bearden interpersonal-influence susceptibility (`conformity·0.45 + status·0.25 + social_radius·0.30`), Cacioppo & Petty need-for-cognition. Reported per tier.
5. **Bootstrap CIs** — adoption proportion gets a 100-replica percentile bootstrap CI; visible in the Perception tab metrics.
6. **Bayesian anchoring** — category priors from the Atlas (60 sources) still anchor the priors; new Bass coefficients are explicitly labelled as simulation outputs, not measured values.

Front-end: **Perception tab** shows the S-curve, the Rogers chart, the Bass fit, the mere-exposure habituation curve, and the psychometric indices — simple enough for anyone to read, quantitative enough for a researcher to interrogate.

## Expand the corpus

Files can be ingested from the CLI:

```bash
cd imprint-bharat
../.venv/bin/python -m app.ingest report.pdf --org NITI --year 2024 --dimension income --tags "rural,consumption"
../.venv/bin/python -m app.ingest data.csv --org "Industry body" --dimension category
../.venv/bin/python -m app.ingest --stats
```

Supported: `.txt`, `.md`, `.csv`, `.json`, `.jsonl`, `.html`, and `.pdf` when `pypdf` is installed. PDF support fails loudly if `pypdf` is missing rather than producing garbage. Ingested chunks are retrievable context with a source and confidence label; they are **not automatically verified facts**.

The studio also has a `POST /api/ingest` endpoint for plain text.

## API surface

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health, TimesFM state, context count, active calibration |
| GET | `/api/meta` | Topics, states, tiers, scenarios, evidence |
| POST | `/api/simulate` | Run the agent-based rehearsal |
| POST | `/api/focus-group` | Focus group on the current brief |
| POST | `/api/chat` | Ask one citizen |
| POST | `/api/scenarios` | Seven scenario fan |
| GET | `/api/forecast` | TimesFM topic forecast |
| GET | `/api/evidence` | Curated evidence cards |
| GET | `/api/atlas` | Context graph stats, sources, audit |
| GET | `/api/atlas/search` | Search context nodes |
| GET | `/api/atlas/audit` | Integrity checks and corpus stats |
| GET | `/api/precedents` | Precedent library and base rates |
| GET | `/api/precedents/retrieve` | Retrieve analogous cases |
| GET | `/api/causal` | Counterfactual analysis |
| GET | `/api/calibration` | Current parameters and history |
| POST | `/api/calibration/run` | Run bounded calibration |
| POST | `/api/reason` | Run the deliberation, replication and stress loop |
| GET | `/api/corpus` | Ingested corpus stats |
| POST | `/api/ingest` | Ingest plain text |

Example:

```bash
curl "http://127.0.0.1:7777/api/causal?topic_id=ev-scooter&pre_end=72&horizon=12&sim_effect_pct=4"
curl -X POST http://127.0.0.1:7777/api/reason \
  -H 'Content-Type: application/json' \
  -d '{"brief":"A ₹1.2 lakh electric scooter for tier-2 India","n_agents":240,"rounds":36,"seed":42}'
```

## TimesFM licence and provenance

The live path uses `timesfm3.mlx` with checkpoint `google/timesfm-3.0-pytorch` and `local_files_only=True`.

**The TimesFM 3.0 checkpoint is non-commercial.** Check the upstream licence before any commercial deployment. Imprint's own code is a research prototype; review licences for every data source and model before production use.

## Hosting (website)

The app is a standard FastAPI service. For a public site:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Put it behind nginx/Caddy/Cloudflare. No build step; static files are served by FastAPI.

### LLM / NLP for hosted users

The deterministic core works for every visitor without any model. For richer citizen replies and debate challenges, configure a **hosted** OpenAI-compatible endpoint (so end users never need to install anything):

```bash
export IMPRINT_LLM_BASE_URL="https://api.groq.com/openai/v1"   # or OpenRouter, Together, HF, Ollama, LM Studio
export IMPRINT_LLM_MODEL="llama-3.1-8b-instant"
export IMPRINT_LLM_API_KEY="your-key"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The key stays on the server; visitors just use the site. If unset, the app falls back to the built-in deterministic NLP (keyword + template replies). Do not commit `models/` or API keys.

> The local TinyLlama GGUF is **opt-in** (`IMPRINT_LLM_LOCAL=1`) for local development only. It is off by default because llama.cpp can be unstable on some machines; hosted endpoints (Groq, OpenRouter) are the supported production path.

- `/api/health` confirms the forecast backend.
- Every simulation run carries an `audit` object: adoption and conversion bounds, addressable accounting, sentiment bounds, tier coverage, context coverage, evidence attachment and seed replay.
- The Atlas tab runs integrity checks: source resolution, duplicate facts, source coverage, recency, confidence labelling, anchor linkage and state coverage.
- The Causal tab reports pre-period fit, placebo p-value, synthetic-control p-value, Bayesian disagreement and synthetic-truth coverage.
- The Calibration tab persists before/after loss, evaluations and adopted parameters.
- The Reasoning tab reports the eight-step trace, seed agreement, stress flips, ten self-checks, the revised confidence, the decision memo and the next test.

## What is not claimed

- Not a 10,000× trained model.
- Not a literal 70× improvement. The reasoning layer is a set of visible checks, not a multiplier guarantee.
- Not a representative survey, poll or census.
- Not causal identification from observational simulation.
- Not a substitute for talking to real people, reading the actual data, or running a real experiment.
- Not a valuation, investment recommendation or guarantee of demand.

Use it to rehearse, surface objections and decide what to test next.
