# Imprint Bharat — Research symposium & roadmap

**Imprint Research** · Head of Research + 10 subordinate researchers  
**Engine**: `imprint-core/3.1` · **Repo**: `Savarnya1403/Imprint-Simulation-Engine`  
**Status**: scenarios fixed, calibration wired, validation battery green, uncertainty/sensitivity/model-card endpoints live, tests passing.

---

## 1. Premise

Imprint is a synthetic consumer-rehearsal engine for India. It answers the question *"what would happen if we launched X?"* with an agent-based model of ~100–1,600 synthetic agents stratified by state, tier, occupation, income, and digital access.

The contract with the user is honest:

- **Real and stochastic**: same brief, different seed → different run. Same seed → bit-for-bit identical run (provenance fingerprint included).
- **Region/tier variation**: built-in tier mix, focus state, region-shift factors per category.
- **Complex maths backend, simple frontend**: belief ODEs integrated by RK4, per-agent nano-MLPs updated by gradient descent on a cognitive-dissonance loss, graph-Laplacian social diffusion, annealed temperature, TimesFM demand signal. The UI stays a warm, dense editorial studio.
- **Indian public data**: Census/state population, TRAI internet penetration, NITI Aayog/RBI/HCES income and tier distributions, 19 category histories (~94 months each), 50 evidence cards and 64 public sources. All cited in the atlas and model card.
- **No fake multipliers**: never claim 10,000×/500×/70× gains. Every number ships with uncertainty and a falsifier.

---

## 2. The ten researchers (who we convened)

Each researcher owns a domain and can be outvoted by evidence. Their names are roles, not people.

| # | Role | What they argue |
|---|------|-----------------|
| 1 | **Simulation lead** | The ABM must be deterministic-per-seed and the calibration knobs must actually move conversion. |
| 2 | **Cognitive modeller** | Prospect theory (λ = 2.25), β–δ present bias, Granovetter thresholds, Slovic trust repair, dual-process appraisal — each must satisfy an analytic identity. |
| 3 | **Forecaster** | TimesFM 3.0 as an exogenous demand trend, backtested rolling-origin against drift; the level forecast does not beat naive, so it is used for trend only and labelled as such. |
| 4 | **Causal analyst** | Counterfactuals, conformal intervals, in-time placebos, synthetic control — decision support, never identification without a real decision date and comparison group. |
| 5 | **Validation lead** | Known-answer battery (12/12), held-out calibration on demand, no in-sample-only claims. |
| 6 | **Uncertainty analyst** | Seed × parameter Latin-hypercube ensemble; percentile intervals, P(SCALE), P(conversion ≥ target), epistemic vs aleatoric variance split. |
| 7 | **Sensitivity analyst** | Jansen total-order + linear response surface over the six behavioural parameters; ST < 0.05 = not worth tuning. |
| 8 | **Ethics & limits** | No real individuals, no credit/insurance/employment decisions, synthetic names, region as structural context never essentialist. |
| 9 | **Product / UX** | Keep the warm studio design (`landing.css` + `studio.css`, no `theme.css` regression); Research tab is restrained and additive. |
| 10 | **Ops / reproducibility** | 16-char SHA-256 fingerprint on every run, bounded run bundles (max 24), markdown/json/csv export, REST-API git flow because `git push` is server-blocked. |

---

## 3. Audit findings (what we found broken)

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 1 | Every non-base scenario returned HTTP 500 `NameError: name 'scenario' is not defined`. | Critical | `_run_math_simulation` now takes `scenario`; event computation moved before trust. All 7 scenarios return 200. |
| 2 | Calibration largely inert: `price_sensitivity`, `social_mult`, `trust_weight`, `atlas_strength`, `precedent` were accepted but unused; only `ceiling_mult`/`hazard_mult` had effect. | Critical | All six wired: `price_sensitivity` steepens affordability and gates the addressable mask; `social_mult` scales the social field; `trust_weight` scales trust; `atlas_strength` scales structural shifts; precedent adds bounded shift + recovery window. |
| 3 | Non-deterministic per seed: MLP weights drew from global `random`, belief ODE noise from global `np.random`. Same seed ≠ same run. | High | `run_simulation` now seeds Python `random` and NumPy global streams; `provenance.fingerprint` proves reproducibility. Verified by test. |
| 4 | Validation was in-sample only: no falsifiable check that the maths behaves, no backtest, no held-out calibration. | High | Added `validation.py` (known-answer battery, rolling-origin MASE backtest vs drift, held-out calibration on demand) and `uncertainty.py` / `sensitivity.py`. |
| 5 | Cognitive primitives existed but were not exposed or wired into decisions. | Medium | 8 new primitives (`dual_process_blend`, `social_threshold`/`granovetter_gate`, `present_bias_weight`, `trust_repair_step`, `construal_weights`, …) wired into the engine; stats reported per run. |
| 6 | No model card, no export, no run retrieval. | Medium | `modelcard.py`, six new FastAPI endpoints (`/api/model-card`, `/api/validation`, `/api/robustness`, `/api/sensitivity`, `/api/runs/{id}`, `/api/runs/{id}/export`), Research/Validation UI tab. |

Benchmarks after wiring (n=300, rounds=36, seeds 42/43/44): EV scooter conv 0.35–0.53 TEST; quick commerce 0.43–0.46 TEST; AI tutor 0.28–0.50 HOLD/TEST; rooftop solar 0.36–0.50 TEST; rural credit 0.29–0.55 TEST/HOLD. Parameter effects: default conv 0.167; `social_mult=1.5` → 0.444; `trust_weight=1.5` → 0.278; `price_sensitivity` direction noisy across seeds (0.413 / 0.384 / 0.428 for ps 0.6/1.0/1.6 at n=400) — documented as an open question below.

### 3.1 Forecasting: what worked, what did not

The forecast layer is scored like everything else — rolling-origin, no lookahead, 19 category histories, horizon 6 months, four origins per topic (`min_train=48`). Error is absolute error relative to a random-walk-with-drift benchmark; below 1.0 means the model adds value.

| Path | median vs drift | median MASE | 80% band coverage | Topics better than raw |
|---|---|---|---|---|
| Raw TimesFM 3.0 | 0.961 | 1.864 | 58.3% | — |
| Fixed 0.75 blend with cheap ensemble | 0.870 | — | — | 8/19 (mixed; median improved, most topics worse) |
| **Test-time augmentation (`aug3`)** | **0.764** | **1.306** | **79.2%** | **14/19 (2 worse)** |
| `aug3` + reasoning/critique | 0.764 | 1.306 | 83.3% | point path unchanged |

**Adopted: `aug3`.** TimesFM is a univariate foundation model and is not invariant to a monotone transform of its input. We forecast the level, the log of the level and the first difference, invert each view exactly (exp / cumulative sum), and average. Each view is visible in the API response under `test_time_augmentation.views`; a failed view is named and dropped rather than silently absorbed. This is an ensemble, not a reasoning model, and it is labelled as such.

**Rejected: a fixed 0.75 foundation/ensemble blend.** It lowered the median error (0.961 → 0.870) but helped only 8 of 19 topics, with most categories worse. That is a mixed, unstable result rather than a robust gain, so it is available as `blend_weight` for sensitivity analysis but is not the default. No multiplier is claimed.

**Reasoning/critique layer.** The default is `foundation_first_with_critique`: the foundation path is kept and four cheap hypotheses (drift, damped trend, mean reversion, seasonal naive) audit it. The rules are named — implausible-trend gate, non-negativity clamp, band cap, direction-disagreement penalty, thin-history warning — and each firing is returned in `reasoned.critique`. On the current series no point-rule fires, so the point path is unchanged; the honest contribution is interval calibration, where 80% coverage rises from 79.2% to 83.3%. The layer is reported as an audit trail, not a point-accuracy claim.

Reproduce:

```bash
../.venv/bin/python - <<'PY'
from app import validation
b = validation.real_series_backtest()
for k in ("median_vs_drift_timesfm", "median_vs_drift_timesfm_aug3",
          "median_coverage_timesfm_aug3", "median_coverage_timesfm_reasoned",
          "augmentation_delta", "reasoning_verdict"):
    print(k, b.get(k))
PY
```

### 3.2 Evidence corpus: what was added

The context layer is only as good as its public record. We added four official sources and 24 curated facts, and wired 12 new evidence cards into the topic packs that depend on them. Every figure below was checked against the publishing body before entry; projections are labelled `medium` confidence and are never presented as observations.

| Source | Year | New facts | Why it changes the simulation |
|---|---|---|---|
| Time Use Survey 2024 (MoSPI) | 2025 | 5 | Unpaid care is the binding constraint on women's paid work: 289 vs 88 minutes/day; 83.9% of women 15-59 do domestic work. |
| Elderly in India 2021 (MoSPI) | 2021 | 4 | 138 million people 60+ (10.1%), projected 13.1% by 2031, with Kerala at 16.5%. |
| Economic Survey 2023-24 (Ministry of Finance) | 2024 | 3 | 78.5 lakh non-farm jobs/year needed to 2030; agriculture's workforce share projected to fall to 25% by 2047. |
| India's Booming Gig and Platform Economy (NITI Aayog) | 2022 | 1 | 7.7 million gig workers in 2020-21, projected 23.5 million by 2029-30. |

We also filled gaps in existing sources: NFHS-5 nutrition and insurance (stunting 35.5%, women's anaemia 57.0%, household health-insurance coverage 41.0%), NHA 2021-22 (health spending 3.83% of GDP; OOPE 39.4%, correcting the older 47.1% card), RBI's FI-Index (64.2 for March 2024), and Census 2011 literacy (74.04%), disability (2.21%) and slum population (65.5 million). `atlas.audit()` now reports 64 sources, 147 facts and 291 nodes, with zero unresolved references and zero duplicate ids.

One attribution error was corrected: `job_gig` had been pointing at the Aspirational Districts source. It now resolves to the NITI Aayog gig report.

### 3.3 Diversity at scale: 48 occupations × 12 axes, 3,000 agents

The population grew from 33 to 48 occupations (adding domestic work, long-haul driving, barber/salon, pharma, tuition, temple work, security, dairy, fisherfolk, powerloom, BPO, guesthouses, trades, online resale and FPO entrepreneurship — each with explicit tier and income priors) and from five diversity axes to twelve: ideology, thought process, economic band, schooling band, settlement, age band and Big Five personality (Openness / Conscientiousness / Extraversion / Agreeableness / Neuroticism with a six-cluster label) now sit alongside religion, caste, region and state. Every axis has a small, explicit effect on trust, risk or conformity — for example ideology shifts `trust_gov`/`trust_media` by at most 0.05 — and is documented as structural context, never as an identity claim. Protected axes (religion, caste, ideology) are diagnostic only: the playbook never recommends targeting or excluding by them.

At 3,000 agents a 240-agent rehearsal that previously capped at 1,600 now runs in about 1.4 seconds. Above ~600 agents the belief network switches from the micrograd object graph to the same 6-4-1 architecture batched in NumPy (`app/vectorbelief.py`); the backend is recorded per run (`provenance.belief_backend`). Generative memory is sampled to 600 agents at large cohorts so the payload stays bounded. Division analytics (`app/segments.py`) reconcile exactly to run totals and add TimesFM market correlation and lead/lag per division; the GTM playbook (`app/strategy.py`) is derived from those divisions — beachhead, next wave, messaging, channels, pricing read, 90-day plan with stop rules, and falsifiers — and is served at `/api/strategy`. The Reasoning loop gained a `Divide` step.

Two honest corrections came with the scale-up. The social multiplier's hazard channel was a 1–2% nudge at low adoption, so at N=90 it was undetectable (the monotone test was underpowered); the hazard now carries an explicit `social_hazard` factor that is near-neutral at the calibrated default but moves ~20% across the grid. The monotone test was re-powered to N=240 (verified monotone 0.38 → 0.46) rather than weakened.

Reproduce:

```python
from app import engine
r = engine.run_simulation("A ₹1.2 lakh electric scooter for tier-2 India", n_agents=3000, rounds=24, seed=42)
print(r["provenance"]["belief_backend"], r["diversity"]["occupation_id"], r["strategy"]["beachhead"])
```

---

## 4. Open disagreements (recorded, not resolved by fiat)

1. **TimesFM licence** — weights are non-commercial (google/timesfm-3.0-pytorch). The module falls back to a labelled damped-trend baseline. Researcher 9 wants the fallback labelled everywhere it surfaces; researcher 3 wants a commercial licence check before any paid deployment. *Acceptance: model card lists the licence and the fallback path; backend `status()` reports backend.*
2. **β–δ power** — present bias only bites above ₹25,000 upfront and is cube-root tempered so it stays a nudge. Researcher 2 wants stronger discounting for durables; researcher 5 worries it overwhelms the price knob. *Acceptance: `future_gate` is a constant in code; tune via calibration budget if evidence warrants.*
3. **Granovetter width / trust recovery half-life** — both are precedent-derived (recovery_days) or fixed (width 0.16). Researcher 6 wants them in the sensitivity box; researcher 7 notes they're already structural. *Acceptance: width fixed at 0.16, recovery from precedent; both reported in the cognitive block.*
4. **Price sensitivity direction** — observed noisy across seeds (0.413/0.384/0.428). Hypothesis: price enters both the addressable mask (gate) and affordability (surface), so at fixed ceiling the mask absorbs part of the effect. *Acceptance: logged as a known behaviour; held-out calibration can settle it; not claimed as a finding.*
5. **Sobol estimator at small N** — first-order Saltelli estimates are noisy below N≈64, so we report Jansen total-order + a stable linear response surface instead, explicitly labelled. *Acceptance: documented in `sensitivity.py` note and UI.*

---

## 5. Roadmap (priority order) with acceptance criteria

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| 1 | Fix broken scenarios | All 7 scenarios return HTTP 200; `scenario` appears in `provenance.params` and summary. |
| 2 | Wire ignored calibration params | `price_sensitivity`, `social_mult`, `trust_weight`, `atlas_strength`, `precedent` each move conversion; monotonicity test for social passes. |
| 3 | Validation battery | `GET /api/validation` returns 12/12 known-answer passes; backtest reports median MASE, vs-drift ratio, trend skill, and an honest verdict; `deep=1` runs held-out calibration. |
| 4 | Uncertainty & sensitivity | `POST /api/robustness` returns percentile intervals, P(SCALE), epistemic share; `POST /api/sensitivity` returns total-order indices with `inert` list; estimator recovers (0.9/0.1/0.0) on y=3x₀+x₁. |
| 5 | Model card & export | `GET /api/model-card` returns intended use, out-of-scope, limitations, systems status, validation results; `GET /api/runs/{id}/export` serves md/json/csv with content-disposition. |
| 6 | Research UI tab | Restrained Research/Validation view added to studio; no `theme.css`; renders battery, backtest table, ensemble fan, sensitivity bars, model card, export links. Zero new console errors in Playwright. |
| 7 | Tests & docs | `tests/` with known-answer identities, determinism, scenario coverage, param monotonicity, ensemble bounds, API contract; 33 tests pass; `pytest` added to dev requirements; `RESEARCH.md` written. |
| 8 | Ship & sync | Commit via REST API (blobs → tree → commit → PATCH ref); `git fetch origin && git reset --hard origin/main`. |

**Done**: items 1–7 (tests pass, endpoints smoke-tested, UI verified with Playwright). **Remaining**: item 8.

---

## 6. How to validate the build

```bash
# server
cd imprint-bharat && pkill -9 -f "uvicorn app.main"; sleep 2
nohup ../.venv/bin/python -m uvicorn app.main:app --port 7777 > /tmp/imprint-server.log 2>&1 &
sleep 14

# health
curl -s http://127.0.0.1:7777/api/health

# research endpoints
curl -s http://127.0.0.1:7777/api/model-card \| python3 -m json.tool \| head -40
curl -s "http://127.0.0.1:7777/api/validation" \| python3 -m json.tool | \
  python3 -c "import json,sys;d=json.load(sys.stdin);print(d['summary'])"

# robustness (15–25 s)
curl -s -X POST http://127.0.0.1:7777/api/robustness -H 'Content-Type: application/json' \
  -d '{"brief":"A ₹1.2 lakh electric scooter for tier-2 India","n_agents":150,"rounds":20,"seed":42}'

# sensitivity (20 s)
curl -s -X POST http://127.0.0.1:7777/api/sensitivity -H 'Content-Type: application/json' \
  -d '{"brief":"A ₹1.2 lakh electric scooter for tier-2 India","n_agents":140,"rounds":18,"seed":42}'

# run + export
RUN_ID=$(curl -s -X POST .../api/simulate ... \| python3 -c "import json,sys;print(json.load(sys.stdin)['run_id'])")
curl -s http://127.0.0.1:7777/api/runs/$RUN_ID/export?format=md

# tests
../.venv/bin/python -m pytest tests -q   # 33 passed
```

**UI**: open `http://127.0.0.1:7777/studio`, click **Validation**. The view shows the 12/12 known-answer battery, the backtest table (MASE vs TimesFM vs drift), the ensemble fan with P(SCALE), sensitivity bars, the model card, and run export.

---

## 7. What this is not

Not a representative survey, not a causal estimate, not a substitute for a pilot. Anchors are analyst ranges from public sources. The social graph is synthetic homophily. WhatsApp — India's largest social channel — is under-observed in public data. Outputs must travel with their uncertainty interval and the falsifier that would overturn them.
