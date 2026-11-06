"""Universal Query Interpreter — powered by Claude Opus 4.7.

Takes any natural language query and returns a fully-structured SimulationSpec
that the engine can run directly. This is what makes the engine versatile:
instead of only handling pre-loaded Indian market topics, it can simulate any
human system — electoral politics, organizational behavior, global markets,
social movements, technology adoption, policy impact, historical counterfactuals.

The interpreter does five things:
  1. Domain classification (market, politics, social, finance, tech, org, historical, custom)
  2. Population inference (who the agents are, their demographics, traits, context)
  3. Dynamics mapping (what forces drive behavior in this domain)
  4. Hypothesis generation (what questions the simulation should answer)
  5. Scenario construction (what interventions / shocks to test)

Falls back to deterministic keyword-based inference when no LLM is available,
routing India-related queries to the existing rich India engine.
"""
from __future__ import annotations

import json
import re
from typing import Any

SYSTEM_PROMPT = """You are a simulation architect designing a multi-agent behavioral simulation.

Given a query, return a JSON object with this exact structure:

{
  "domain": "<market|politics|social|finance|technology|organizational|historical|science|custom>",
  "simulation_type": "<adoption|diffusion|conflict|negotiation|election|market_dynamics|policy_impact|social_movement|custom>",
  "is_india_context": <true|false>,
  "language": "<en|hi|hinglish|fr|de|es|ja|custom>",
  "brief": "<50-word simulation brief — the core hypothesis being tested>",
  "motion": "<declarative statement of what the simulation predicts, like a debate proposition>",
  "population_spec": {
    "size_recommended": <100-1600>,
    "context": "<who these agents are — geography, role, demographics>",
    "primary_dimension": "<the most important differentiating variable for this population>",
    "segments": [
      {"label": "<segment name>", "share": <0.0-1.0>, "description": "<who they are>", "traits": {"trait_key": <0.0-1.0>}}
    ],
    "universal_traits": {
      "<trait_name>": {"mean": <float>, "spread": <float>, "description": "<what this measures>"}
    }
  },
  "topic": {
    "id": "<snake_case_id>",
    "label": "<short label>",
    "category": "<category>",
    "price": <0 for non-market>,
    "price_note": "<note or empty>",
    "benefits": ["<benefit>"],
    "objections": ["<objection>"],
    "triggers": ["<adoption trigger>"],
    "pro_claims": ["<pro argument>"],
    "con_claims": ["<con argument>"],
    "ground_reality": ["<contextual fact>"]
  },
  "scenarios": [
    {"id": "<id>", "label": "<label>", "description": "<what changes>", "direction": "<positive|negative|neutral>"}
  ],
  "hypotheses": [
    {
      "id": "<id>",
      "label": "<hypothesis label>",
      "binding_factor": "<what drives behavior>",
      "keys": ["<keyword>"],
      "falsifier": "<what would disprove this>"
    }
  ],
  "forecast_variables": ["<variable to track over time>"],
  "metrics": ["adoption_rate", "sentiment_mean", "polarization_index", "coalition_density"],
  "rounds_recommended": <24-96>,
  "reasoning_note": "<one sentence on why this simulation design fits the query>"
}

Rules:
- is_india_context: true only when the query is specifically about India or Indian context
- segments shares must sum to 1.0
- scenarios: provide exactly 5 (base + 4 interventions relevant to this domain)
- hypotheses: provide exactly 4-5 competing explanations
- Traits use 0.0-1.0 scales (0=low, 1=high)
- Be specific: a query about "US voters and UBI" needs American political segments, not generic ones
- For historical counterfactuals, model the actual historical population
- Never hallucinate data; use "unknown" rather than inventing statistics
"""


def interpret(query: str) -> dict[str, Any]:
    """Main entry point. Returns a SimulationSpec dict."""
    from . import llm

    raw = llm.generate_structured(
        prompt=f"Query to simulate: {query}",
        system=SYSTEM_PROMPT,
        max_tokens=3000,
        temperature=0.2,
    )

    if raw:
        spec = _parse_llm_response(raw)
        if spec:
            spec["query"] = query
            spec["interpreter_mode"] = "claude"
            return spec

    # Fallback: deterministic keyword inference
    return _deterministic_interpret(query)


def _parse_llm_response(raw: str) -> dict[str, Any] | None:
    """Extract JSON from Claude's response, tolerating markdown fences."""
    text = raw.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    # Find the first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        obj = json.loads(text[start : end + 1])
        if "domain" in obj and "population_spec" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    return None


# ---------------------------------------------------------------------------
# Deterministic fallback interpreter
# ---------------------------------------------------------------------------

_INDIA_KEYWORDS = {
    "india", "bharat", "indian", "hindi", "rupee", "₹", "crore", "lakh",
    "tier-1", "tier-2", "tier-3", "tier-4", "metro", "nse", "bse", "sebi",
    "rbi", "gst", "upi", "paytm", "reliance", "tata", "jio", "flipkart",
    "amazon india", "swiggy", "zomato", "byju", "ola", "delhi", "mumbai",
    "bangalore", "bengaluru", "chennai", "kolkata", "hyderabad", "pune",
    "ahmedabad", "surat", "jaipur", "lucknow", "kanpur", "nagpur", "patna",
    "indore", "thane", "bhopal", "visakhapatnam", "pimpri", "vadodara",
    "hinglish",
}

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "politics": ["election", "vote", "voter", "policy", "government", "party", "senator", "president",
                 "parliament", "democracy", "legislation", "campaign", "ballot", "referendum"],
    "social": ["movement", "protest", "community", "social", "cultural", "norm", "behavior", "attitude",
               "belief", "religion", "identity", "gender", "race", "ethnicity"],
    "finance": ["stock", "market", "invest", "portfolio", "fund", "hedge", "trade", "crypto",
                "bitcoin", "equity", "bond", "rate", "gdp", "inflation", "recession"],
    "technology": ["ai", "tech", "software", "app", "platform", "startup", "digital", "automation",
                   "robot", "saas", "cloud", "blockchain", "innovation"],
    "organizational": ["employee", "workplace", "hr", "team", "company", "firm", "manager", "worker",
                       "remote", "office", "salary", "burnout", "productivity"],
    "historical": ["historical", "history", "1900", "1950", "century", "war", "revolution",
                   "empire", "colonial", "ancient"],
    "science": ["climate", "vaccine", "health", "medical", "drug", "science", "research", "study"],
    "market": ["buy", "purchase", "product", "brand", "consumer", "customer", "price", "launch",
               "adoption", "category", "market"],
}


def _detect_domain(query: str) -> str:
    q = query.lower()
    scores: dict[str, int] = {}
    for domain, kws in _DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for k in kws if k in q)
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "custom"


def _deterministic_interpret(query: str) -> dict[str, Any]:
    q = query.lower()
    is_india = any(kw in q for kw in _INDIA_KEYWORDS)
    domain = _detect_domain(query)
    if is_india:
        domain = "market"

    segments = _default_segments(domain, is_india)
    scenarios = _default_scenarios(domain)
    hypotheses = _default_hypotheses(domain)

    return {
        "query": query,
        "domain": domain,
        "simulation_type": _simulation_type(domain),
        "is_india_context": is_india,
        "language": "hinglish" if is_india else "en",
        "brief": query[:200],
        "motion": f"The described scenario — {query[:100]} — will produce significant behavioral change in the target population.",
        "population_spec": {
            "size_recommended": 240,
            "context": "India (all tiers and states)" if is_india else "General population relevant to the query",
            "primary_dimension": "tier" if is_india else "segment",
            "segments": segments,
            "universal_traits": _default_traits(domain),
        },
        "topic": {
            "id": "custom",
            "label": query[:80],
            "category": domain.capitalize(),
            "price": 0,
            "price_note": "",
            "benefits": ["Potential positive outcome"],
            "objections": ["Uncertainty and risk", "Cost or disruption"],
            "triggers": ["Strong evidence of benefit", "Peer adoption"],
            "pro_claims": ["The proposed change could improve outcomes significantly."],
            "con_claims": ["Adoption barriers and uncertainty may limit uptake."],
            "ground_reality": ["No specific data loaded; using domain priors."],
        },
        "scenarios": scenarios,
        "hypotheses": hypotheses,
        "forecast_variables": ["adoption_rate", "sentiment", "polarization"],
        "metrics": ["adoption_rate", "sentiment_mean", "polarization_index", "coalition_density"],
        "rounds_recommended": 36,
        "reasoning_note": "Deterministic fallback: set ANTHROPIC_API_KEY for Claude-powered interpretation.",
        "interpreter_mode": "deterministic",
    }


def _simulation_type(domain: str) -> str:
    return {
        "politics": "election",
        "social": "diffusion",
        "finance": "market_dynamics",
        "technology": "adoption",
        "organizational": "policy_impact",
        "historical": "diffusion",
        "science": "diffusion",
        "market": "adoption",
    }.get(domain, "custom")


def _default_segments(domain: str, is_india: bool) -> list[dict]:
    if is_india:
        return [
            {"label": "Metro tier-1", "share": 0.10, "description": "Urban metros", "traits": {"risk": 0.3, "price": 0.4, "digital": 0.9}},
            {"label": "Tier-2 urban", "share": 0.15, "description": "Mid-sized cities", "traits": {"risk": 0.45, "price": 0.55, "digital": 0.7}},
            {"label": "Tier-3 small town", "share": 0.28, "description": "Small towns", "traits": {"risk": 0.6, "price": 0.7, "digital": 0.5}},
            {"label": "Tier-4 rural", "share": 0.47, "description": "Rural India", "traits": {"risk": 0.75, "price": 0.85, "digital": 0.3}},
        ]
    segs = {
        "politics": [
            {"label": "Progressive", "share": 0.35, "description": "Left-leaning, urban, educated", "traits": {"openness": 0.8, "risk": 0.4}},
            {"label": "Conservative", "share": 0.35, "description": "Right-leaning, rural/suburban", "traits": {"openness": 0.3, "risk": 0.6}},
            {"label": "Moderate/Independent", "share": 0.30, "description": "Swing voters", "traits": {"openness": 0.55, "risk": 0.5}},
        ],
        "organizational": [
            {"label": "Senior leadership", "share": 0.10, "description": "Executives and VPs", "traits": {"authority": 0.9, "risk": 0.4}},
            {"label": "Middle management", "share": 0.25, "description": "Managers and leads", "traits": {"authority": 0.5, "risk": 0.5}},
            {"label": "Individual contributors", "share": 0.65, "description": "ICs and analysts", "traits": {"authority": 0.2, "risk": 0.55}},
        ],
        "finance": [
            {"label": "Institutional", "share": 0.20, "description": "Funds, banks, large investors", "traits": {"sophistication": 0.9, "risk": 0.5}},
            {"label": "Retail — active", "share": 0.30, "description": "Active retail traders", "traits": {"sophistication": 0.5, "risk": 0.6}},
            {"label": "Retail — passive", "share": 0.50, "description": "Long-term savers", "traits": {"sophistication": 0.3, "risk": 0.3}},
        ],
    }
    return segs.get(domain, [
        {"label": "Early adopters", "share": 0.15, "description": "Innovators and early adopters", "traits": {"openness": 0.8, "risk": 0.3}},
        {"label": "Mainstream", "share": 0.65, "description": "Early and late majority", "traits": {"openness": 0.5, "risk": 0.5}},
        {"label": "Laggards", "share": 0.20, "description": "Skeptics and late adopters", "traits": {"openness": 0.2, "risk": 0.8}},
    ])


def _default_scenarios(domain: str) -> list[dict]:
    base = [{"id": "base", "label": "Base case", "description": "No external intervention.", "direction": "neutral"}]
    domain_scenarios: dict[str, list[dict]] = {
        "politics": [
            {"id": "media_amplify", "label": "Media amplification", "description": "Major media campaign pushes the narrative.", "direction": "positive"},
            {"id": "scandal", "label": "Scandal / crisis", "description": "A trust-damaging event surfaces.", "direction": "negative"},
            {"id": "economic_shock", "label": "Economic shock", "description": "GDP or jobs number shifts voter mood sharply.", "direction": "negative"},
            {"id": "grassroots", "label": "Grassroots surge", "description": "Ground-level organizing drives turnout.", "direction": "positive"},
        ],
        "market": [
            {"id": "price_cut", "label": "Price reduction", "description": "20% price drop + heavy ads.", "direction": "positive"},
            {"id": "trust_shock", "label": "Trust shock", "description": "Viral quality failure on day 12.", "direction": "negative"},
            {"id": "viral", "label": "Viral moment", "description": "Creator-led social proof surge.", "direction": "positive"},
            {"id": "competitor", "label": "Competitor counter", "description": "Incumbent cuts price and seeds doubt.", "direction": "negative"},
        ],
        "organizational": [
            {"id": "mandate", "label": "Top-down mandate", "description": "Leadership mandates adoption with KPI.", "direction": "positive"},
            {"id": "resistance", "label": "Active resistance", "description": "Vocal minority organizes against change.", "direction": "negative"},
            {"id": "incentive", "label": "Incentive program", "description": "Financial/recognition incentives roll out.", "direction": "positive"},
            {"id": "attrition", "label": "Attrition spike", "description": "Key adopters leave the organization.", "direction": "negative"},
        ],
        "social": [
            {"id": "influencer", "label": "Influencer adoption", "description": "High-status nodes visibly adopt.", "direction": "positive"},
            {"id": "backlash", "label": "Cultural backlash", "description": "Opposition frames it as a threat to identity.", "direction": "negative"},
            {"id": "institutional", "label": "Institutional endorsement", "description": "Respected institution endorses the change.", "direction": "positive"},
            {"id": "polarization", "label": "Polarization event", "description": "Divisive media event splits the population.", "direction": "negative"},
        ],
    }
    extras = domain_scenarios.get(domain, domain_scenarios["market"])
    return base + extras


def _default_hypotheses(domain: str) -> list[dict]:
    domain_hyps: dict[str, list[dict]] = {
        "market": [
            {"id": "price", "label": "Price is binding", "binding_factor": "affordability", "keys": ["cost", "price", "afford", "expensive"], "falsifier": "Price reduction >20% doesn't move conversion by >5pp."},
            {"id": "trust", "label": "Trust is binding", "binding_factor": "credibility", "keys": ["trust", "quality", "safety", "warranty"], "falsifier": "Third-party guarantee doesn't shift conversion."},
            {"id": "social", "label": "Social proof is binding", "binding_factor": "peer_influence", "keys": ["neighbour", "peer", "family", "everyone"], "falsifier": "Seeded community trial doesn't lift adoption vs control."},
            {"id": "awareness", "label": "Awareness is binding", "binding_factor": "comprehension", "keys": ["aware", "heard", "know", "understand"], "falsifier": "Doubled reach doesn't lift conversion in low-awareness districts."},
        ],
        "politics": [
            {"id": "economic", "label": "Economic anxiety is binding", "binding_factor": "material_interest", "keys": ["job", "economy", "income", "cost", "inflation"], "falsifier": "Economic optimism index doesn't predict vote share."},
            {"id": "identity", "label": "Identity and values are binding", "binding_factor": "tribal_alignment", "keys": ["identity", "value", "culture", "tradition", "threat"], "falsifier": "Same-party voters split evenly across economic vs identity messages."},
            {"id": "trust", "label": "Candidate trust is binding", "binding_factor": "credibility", "keys": ["trust", "honest", "credible", "authentic"], "falsifier": "Favorability gap doesn't predict vote margin."},
            {"id": "turnout", "label": "Differential turnout is binding", "binding_factor": "mobilization", "keys": ["turnout", "vote", "register", "mobilize"], "falsifier": "GOTV effort in low-turnout precincts doesn't shift result."},
        ],
        "organizational": [
            {"id": "incentive", "label": "Incentive alignment is binding", "binding_factor": "reward_structure", "keys": ["bonus", "kpi", "review", "reward", "promotion"], "falsifier": "Incentive program doesn't increase adoption rate vs control group."},
            {"id": "inertia", "label": "Process inertia is binding", "binding_factor": "habit_formation", "keys": ["habit", "process", "workflow", "familiar", "easy"], "falsifier": "Workflow redesign doesn't reduce friction score."},
            {"id": "trust_leadership", "label": "Leadership trust is binding", "binding_factor": "authority", "keys": ["trust", "manager", "leader", "vision", "direction"], "falsifier": "Endorsed mandate shows same adoption curve as self-directed."},
            {"id": "social_proof_work", "label": "Peer adoption is binding", "binding_factor": "social_proof", "keys": ["colleague", "team", "peer", "everyone", "department"], "falsifier": "Adoption rate doesn't correlate with peer adoption density."},
        ],
    }
    return domain_hyps.get(domain, domain_hyps["market"])


def _default_traits(domain: str) -> dict[str, dict]:
    base = {
        "openness": {"mean": 0.5, "spread": 0.25, "description": "openness to new ideas"},
        "risk": {"mean": 0.5, "spread": 0.2, "description": "risk aversion (1=very risk-averse)"},
        "social_influence": {"mean": 0.5, "spread": 0.2, "description": "susceptibility to peer pressure"},
        "information_seeking": {"mean": 0.5, "spread": 0.2, "description": "tendency to research before deciding"},
    }
    domain_extras: dict[str, dict] = {
        "market": {"price_sensitivity": {"mean": 0.6, "spread": 0.25, "description": "price sensitivity"}},
        "politics": {"partisan_intensity": {"mean": 0.55, "spread": 0.3, "description": "strength of party affiliation"}},
        "organizational": {"authority_deference": {"mean": 0.5, "spread": 0.25, "description": "deference to authority"}},
        "finance": {"loss_aversion": {"mean": 0.65, "spread": 0.2, "description": "prospect theory loss weight"}},
    }
    base.update(domain_extras.get(domain, {}))
    return base


def spec_to_simulate_kwargs(spec: dict[str, Any]) -> dict[str, Any]:
    """Convert a SimulationSpec to kwargs accepted by engine.run_simulation."""
    pop = spec.get("population_spec", {})
    topic = spec.get("topic", {})
    return {
        "brief": spec.get("brief", spec.get("query", "")),
        "n_agents": min(1600, max(40, pop.get("size_recommended", 240))),
        "rounds": min(120, max(12, spec.get("rounds_recommended", 36))),
        "seed": 42,
        "scenario": "base",
        "_simulation_spec": spec,
    }
