"""Game Master, adapted from DeepMind Concordia — domain-agnostic version.

In Concordia, entities declare intended actions in natural language; the Game
Master (GM) adjudicates what actually happens — checking plausibility against
the world, and producing consequences. March & Olsen's three questions drive
agent reasoning:
  1. What kind of situation is this?
  2. What kind of person am I?
  3. What does a person such as I do in a situation such as this?

This version is fully domain-agnostic:
  - India market decisions → Hinglish dialogue, tier-based framing
  - Political simulations → civic context, ideology-aware framing
  - Organizational change → workplace context, authority framing
  - Social movements → identity and values framing
  - Any other domain → generic but psychologically realistic framing

The GM uses Claude Opus 4.7 when available; deterministic templates otherwise.
Every GM ruling is logged into both agents' memory streams.
"""
from __future__ import annotations

import random
from typing import Any


# ---------------------------------------------------------------------------
# March & Olsen three-question framework — domain-aware
# ---------------------------------------------------------------------------

def situation_type(agent: dict, topic: dict, day: int, domain: str = "market") -> str:
    """Q1: What kind of situation is this?"""
    label = topic.get("label", "this")
    category = topic.get("category", "General").lower()
    language = agent.get("language", "en")

    if domain == "market":
        if day <= 3:
            return f"an early-curiosity phase for a new {category} category"
        if float(agent.get("stance", 0.5)) > 0.6:
            return f"a decision window: someone I know might adopt {label}"
        return f"a routine {category} conversation — discovery, not purchase"

    if domain == "politics":
        if day <= 5:
            return "an early campaign period — most people are forming initial impressions"
        if float(agent.get("stance", 0.5)) > 0.65:
            return f"a solidifying conviction about {label} — now it's about whether to act"
        return f"an ongoing political discussion about {label} with uncertain personal stakes"

    if domain == "organizational":
        if day <= 3:
            return f"an announcement phase — {label} is new and people are assessing"
        if float(agent.get("stance", 0.5)) > 0.6:
            return f"a commitment moment: adopting {label} now has visible consequences"
        return f"a water-cooler conversation about {label} — cautious but curious"

    if domain == "social":
        if day <= 5:
            return f"an emergence phase — {label} is spreading through social networks"
        if float(agent.get("stance", 0.5)) > 0.7:
            return f"a normalization phase — {label} is becoming part of identity"
        return f"a contested social moment — {label} is visible but not yet settled"

    # Generic
    if day <= 3:
        return f"an early awareness phase for {label}"
    return f"an ongoing engagement with {label}"


def person_type(agent: dict, domain: str = "market") -> str:
    """Q2: What kind of person am I?"""
    t = agent.get("traits", {})
    lang = agent.get("language", "en")
    bits = []

    if domain == "market":
        risk = float(t.get("risk", 0.5))
        price = float(t.get("price", t.get("price_sensitivity", 0.5)))
        if risk > 0.6:
            bits.append("a cautious buyer who waits for proof")
        else:
            bits.append("an early adopter who tries things first")
        if price > 0.6:
            bits.append("very price-conscious")
        tier = agent.get("tier", 2)
        if tier >= 3:
            bits.append("from a community where word-of-mouth matters most")
        return " and ".join(bits)

    if domain == "politics":
        partisan = float(t.get("partisan_intensity", t.get("conformity", 0.5)))
        openness = float(t.get("openness", 0.5))
        if partisan > 0.65:
            bits.append("a strong partisan who votes on principle")
        else:
            bits.append("a pragmatic voter who weighs outcomes")
        if openness < 0.4:
            bits.append("skeptical of rapid change")
        return " and ".join(bits)

    if domain == "organizational":
        authority = float(t.get("authority_deference", t.get("conformity", 0.5)))
        if authority > 0.6:
            bits.append("someone who follows organizational direction")
        else:
            bits.append("someone who evaluates changes on their own merits")
        return " and ".join(bits)

    # Generic
    openness = float(t.get("openness", 0.5))
    risk = float(t.get("risk", 0.5))
    if openness > 0.6:
        bits.append("open to new ideas and willing to experiment")
    elif openness < 0.4:
        bits.append("cautious and preferring the familiar")
    else:
        bits.append("balanced between curiosity and caution")
    return " and ".join(bits)


def action_rule(agent: dict, other: dict, domain: str = "market") -> str:
    """Q3: What does a person such as I do in a situation such as this?"""
    t = agent.get("traits", {})
    conformity = float(t.get("conformity", 0.5))
    independence = float(t.get("independence", t.get("information_seeking", 0.5)))

    if conformity > 0.65:
        return f"I look to what {other.get('name', 'others like me')} and my community are doing"
    if independence > 0.6:
        return "I gather evidence I can verify myself before deciding"
    if domain == "politics":
        return "I think about how this affects my family and community concretely"
    if domain == "organizational":
        return "I watch what respected colleagues do and assess the signals carefully"
    return "I ask who has tried this and what their actual experience was"


# ---------------------------------------------------------------------------
# GM encounter resolution
# ---------------------------------------------------------------------------

def resolve_encounter(
    a: dict,
    b: dict,
    topic: dict,
    day: int,
    topic_label: str,
    llm_generate,
    rng: random.Random,
    domain: str = "market",
) -> dict[str, Any]:
    """GM adjudicates one encounter. Returns the outcome transcript."""
    sit = situation_type(a, topic, day, domain)
    person = person_type(a, domain)
    rule = action_rule(a, b, domain)
    language = a.get("language", "en")

    # Build domain-aware GM prompt
    if domain == "market" and language in ("hi", "hinglish"):
        lang_instruction = "Write 3-4 short lines of natural Hinglish dialogue between A and B."
        setting_note = f"A = {a.get('name')}, {a.get('occupation')}, tier {a.get('tier')}"
    else:
        lang_instruction = "Write 3-4 short, realistic lines of dialogue between A and B in the voice of their context."
        location = a.get("city", a.get("state", "their location"))
        setting_note = f"A = {a.get('name')}, {a.get('occupation')}, in {location}"

    prompt = (
        f"You are an impartial Game Master adjudicating a realistic social encounter.\n"
        f"Domain: {domain}. Topic: {topic_label}.\n"
        f"Situation: {sit}.\n"
        f"{setting_note}, {person}. Rule of thumb: {rule}.\n"
        f"B = {b.get('name')}, {b.get('occupation')}, stance {float(b.get('stance', 0.5)):.2f}.\n"
        f"{lang_instruction} "
        f"Do NOT narrate setup or add preamble. Start directly with A speaking.\n"
        f"End with exactly one line: OUTCOME: <convinced|sceptical|indifferent> — <very short reason>."
    )

    raw = llm_generate(prompt, max_tokens=280, temperature=0.8) if llm_generate else None

    if raw:
        lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
        outcome_line = next((l for l in lines if l.upper().startswith("OUTCOME")), "")
        skip_prefixes = (
            "domain:", "situation:", "a =", "b =", "topic:", "setting:",
            "you are", "game master", "note:", "rule of thumb:",
        )
        dialogue_lines = [
            ln for ln in lines
            if not ln.lower().startswith(skip_prefixes) and not ln.upper().startswith("OUTCOME")
        ]
        outcome_text = outcome_line.replace("OUTCOME:", "").strip() if outcome_line else ""
        verdict = next((v for v in ("convinced", "sceptical", "indifferent") if v in outcome_text.lower()), "indifferent")
        dialogue = "\n".join(dialogue_lines[:6]).strip()
    else:
        dialogue = make_dialogue(a, b, topic_label, rng, domain)
        verdict = pick_verdict(a, b, rng)
        outcome_text = ""

    stance_delta = {"convinced": +0.22, "sceptical": -0.22, "indifferent": +0.02}[verdict]
    return {
        "day": day,
        "a": {"id": a.get("id"), "name": a.get("name")},
        "b": {"id": b.get("id"), "name": b.get("name")},
        "setting": f"{a.get('city', a.get('state', 'Unknown'))} · day {day}",
        "dialogue": dialogue,
        "outcome": verdict,
        "reason": outcome_text if raw else _default_reason(verdict, b),
        "stance_delta": stance_delta,
        "topic": topic_label,
        "domain": domain,
        "gm_mode": "claude" if raw else "template",
    }


def _default_reason(verdict: str, b: dict) -> str:
    name = b.get("name", "them")
    return {
        "convinced": f"{name} made a compelling case",
        "sceptical": f"{name} raised concerns that weren't resolved",
        "indifferent": f"Neither felt strongly enough to change the other's mind",
    }[verdict]


# ---------------------------------------------------------------------------
# Dialogue templates — domain-aware deterministic fallback
# ---------------------------------------------------------------------------

def make_dialogue(a: dict, b: dict, topic_label: str, rng: random.Random, domain: str = "market") -> str:
    name_a = a.get("name", "A")
    name_b = b.get("name", "B")

    if domain == "market" and a.get("language", "en") in ("hi", "hinglish"):
        templates = [
            f"{name_a}: Bhai, {topic_label} — ab itna show ho raha hai.\n{name_b}: Suno toh, pehle price dekho.\n{name_a}: Neighbour ka cousin le liya, bolta hai service theek hai.\n{name_b}: Hmm… main dekhta hoon, abhi rush mat karo.",
            f"{name_a}: Yeh {topic_label} ka kya scene hai?\n{name_b}: Mera beta bol raha tha, ads toh sabke hain.\n{name_a}: Farji mat samjho yaar, apne gaon mein pehle dekha hai.\n{name_b}: Chalo, trial toh kar sakte hain.",
            f"{name_a}: {name_b}, {topic_label} lena chahta hoon.\n{name_b}: Paisa ka kya plan hai?\n{name_a}: EMI pe soch raha hoon.\n{name_b}: Pehle ek neighbour se baat karo.",
        ]
        return rng.choice(templates)

    if domain == "politics":
        templates = [
            f"{name_a}: I've been reading about {topic_label}. It's more complicated than the coverage suggests.\n{name_b}: I hear you, but I'm not sure the leadership can actually deliver.\n{name_a}: That's fair — but what's the alternative?\n{name_b}: Voting for real change, even if it's slow.",
            f"{name_a}: {topic_label} is going to define this election, I think.\n{name_b}: Only if people actually turn out.\n{name_a}: That's what I'm worried about — enthusiasm is there but organization isn't.\n{name_b}: We'll see — I've seen surprises before.",
        ]
        return rng.choice(templates)

    if domain == "organizational":
        templates = [
            f"{name_a}: Did you see the update about {topic_label}?\n{name_b}: Yeah, I'm still figuring out what it actually means for our team.\n{name_a}: I think leadership is serious about it this time — the KPIs changed.\n{name_b}: That's what will make the difference. Show me the incentive.",
            f"{name_a}: I tried {topic_label} this week. The learning curve is real.\n{name_b}: How long did it take you to get comfortable?\n{name_a}: A few days, but once it clicked it's actually faster.\n{name_b}: Okay, that's more reassuring than the training video.",
        ]
        return rng.choice(templates)

    # Generic
    templates = [
        f"{name_a}: What do you make of {topic_label}?\n{name_b}: Honestly I'm still skeptical. There's a lot of noise out there.\n{name_a}: Fair, but the data I've seen is fairly convincing.\n{name_b}: Data is only as good as the question it answers.",
        f"{name_a}: I've been thinking about {topic_label} a lot lately.\n{name_b}: Me too — it's hard to know what to believe.\n{name_a}: I think at some point you have to just try and see.\n{name_b}: Maybe. I'd want to know who else has tried first.",
    ]
    return rng.choice(templates)


def pick_verdict(a: dict, b: dict, rng: random.Random) -> str:
    """Deterministic outcome: higher stance b and lower a stance → more likely convinced."""
    p = 0.5 + (float(b.get("stance", 0.5)) - float(a.get("stance", 0.5))) * 0.7 + rng.gauss(0, 0.15)
    p = max(0.05, min(0.95, p))
    r = rng.random()
    if r < p:
        return "convinced"
    if r < p + (1 - p) * 0.6:
        return "sceptical"
    return "indifferent"


def sample_encounters(agents: list[dict], adopted_mask, day: int, topic: dict, rng: random.Random, n: int = 3) -> list[tuple[dict, dict]]:
    """Pick pairs of agents — prefer one higher-stance with one undecided."""
    if len(agents) < 2:
        return []
    pairs = []
    for _ in range(n):
        i = rng.randrange(len(agents))
        j = rng.randrange(len(agents))
        if i == j:
            continue
        a_idx, b_idx = agents[i], agents[j]
        # Higher-voice agent initiates
        voice_a = float(a_idx.get("traits", {}).get("voice", a_idx.get("traits", {}).get("information_seeking", 0.5)))
        voice_b = float(b_idx.get("traits", {}).get("voice", b_idx.get("traits", {}).get("information_seeking", 0.5)))
        if voice_a < voice_b:
            a_idx, b_idx = b_idx, a_idx
        pairs.append((a_idx, b_idx))
    return pairs


__all__ = ["resolve_encounter", "sample_encounters", "situation_type", "person_type", "action_rule"]
