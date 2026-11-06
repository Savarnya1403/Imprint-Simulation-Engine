"""Game Master, adapted from DeepMind Concordia.

In Concordia, entities declare intended actions in natural language; the Game
Master (GM) adjudicates what actually happens — checking plausibility against
the world, and producing consequences. March & Olsen's three questions drive
agent reasoning:
  1. What kind of situation is this?
  2. What kind of person am I?
  3. What does a person such as I do in a situation such as this?

Here the GM resolves one sampled social encounter per simulation day between
two agents (chosen from the social graph), producing a natural-language
exchange and the outcome the world observes (e.g., "B convinced A to try it"
or "A dismissed it"). Uses the configured LLM (local or hosted) if available;
falls back to a deterministic template otherwise. Every GM ruling is logged
into both agents' memory streams.
"""
from __future__ import annotations

import random
from typing import Any


def situation_type(agent: dict, topic: dict, day: int) -> str:
    """March & Olsen Q1: what kind of situation is this?"""
    t = topic.get("category", "General")
    if day <= 3:
        return "an early-curiosity phase for a new category"
    if agent.get("stance", 0.5) > 0.6:
        return f"a decision window: someone I know might buy {topic.get('label','')}"
    return f"a routine {t.lower()} conversation — discovery, not purchase"


def person_type(agent: dict) -> str:
    """March & Olsen Q2: what kind of person am I?"""
    t = agent.get("traits", {})
    bits = []
    if t.get("risk", 0.5) > 0.6:
        bits.append("a cautious buyer")
    else:
        bits.append("an early adopter")
    if t.get("price", 0.5) > 0.6:
        bits.append("very price-conscious")
    if agent.get("tier") in (3, 4):
        bits.append("from a small town where word travels fast")
    return " and ".join(bits)


def action_rule(agent: dict, other: dict) -> str:
    """March & Olsen Q3: what does a person such as I do here?"""
    t = agent.get("traits", {})
    if t.get("conformity", 0.5) > 0.6:
        return f"I mostly follow what {other.get('name','they')} and neighbours do"
    if t.get("independence", 0.5) > 0.6:  # trait may be absent -> default
        return "I decide on evidence I can verify myself"
    return "I ask what it costs and who has tried it locally"


def llm_available(llm) -> bool:
    try:
        return bool(llm and getattr(llm, "available", False))
    except Exception:
        return False


def resolve_encounter(
    a: dict,
    b: dict,
    topic: dict,
    day: int,
    topic_label: str,
    llm_generate,
    rng: random.Random,
) -> dict[str, Any]:
    """GM adjudicates one encounter. Returns the outcome transcript."""
    sit = situation_type(a, topic, day)
    person = person_type(a)
    rule = action_rule(a, b)

    prompt = (
        "You are an impartial Game Master adjudicating a slice-of-life encounter in India.\n"
        f"Situation: {sit}.\n"
        f"A = {a.get('name')}, {a.get('occupation')}, tier {a.get('tier')}, {person}. Rule of thumb: {rule}.\n"
        f"B = {b.get('name')}, {b.get('occupation')}, tier {b.get('tier')}, stance {b.get('stance', .5):.2f}.\n"
        f"They talk about {topic_label}.\n"
        "Write ONLY 3-4 short lines of natural Hinglish dialogue between A and B. "
        "Do NOT narrate the situation, do NOT restate the setup, do NOT add any preamble. Start directly with A speaking.\n"
        "Then one final line exactly: OUTCOME: <convinced|sceptical|indifferent> — <very short reason>."
    )
    raw = llm_generate(prompt, max_tokens=220, temperature=0.8) if llm_generate else None

    if raw:
        lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
        outcome_line = next((l for l in lines if l.upper().startswith("OUTCOME")), "")
        preamble_prefixes = ("situation:", "a =", "b =", "person a", "person b", "they talk", "rule of thumb:", "a: rule of thumb", "a routine", "a rule")
        dialogue_lines = []
        for ln in lines:
            low = ln.lower()
            if low.startswith("outcome"):
                continue
            if any(low.startswith(p) for p in preamble_prefixes):
                continue
            dialogue_lines.append(ln)
        outcome_text = outcome_line.replace("OUTCOME:", "").strip() if outcome_line else ""
        verdict = next((v for v in ("convinced", "sceptical", "indifferent") if v in outcome_text.lower()), "indifferent")
        dialogue = "\n".join(dialogue_lines[:6]).strip()
    else:
        dialogue = make_dialogue(a, b, topic_label, rng)
        verdict = pick_verdict(a, b, rng)

    stance_delta = {"convinced": +0.22, "sceptical": -0.22, "indifferent": +0.02}[verdict]
    return {
        "day": day,
        "a": {"id": a.get("id"), "name": a.get("name")},
        "b": {"id": b.get("id"), "name": b.get("name")},
        "setting": f"{a.get('city')} · day {day}",
        "dialogue": dialogue,
        "outcome": verdict,
        "reason": outcome_text if raw else f"{b.get('name')} {'made it relatable' if verdict == 'convinced' else 'could not convince them' if verdict == 'sceptical' else 'did not have a strong opinion either way'}",
        "stance_delta": stance_delta,
        "topic": topic_label,
        "gm_mode": "llm" if raw else "template",
    }


def make_dialogue(a: dict, b: dict, topic_label: str, rng: random.Random) -> str:
    """Deterministic Hinglish dialogue when no LLM is configured."""
    name_b = b.get("name", "friend")
    templates = [
        f"{a.get('name')}: Bhai, {topic_label} — ab itna show ho raha hai.\n{name_b}: Suno toh, price pehle dekho.\n{a.get('name')}: Neighbour ka cousin le liya, bolta hai service theek hai.\n{name_b}: Hmm… main dekhta hoon, abhi rush mat karo.",
        f"{a.get('name')}: Yeh {topic_label} ka kya scene hai?\n{name_b}: Mera beta bol raha tha, ads toh sabke hain.\n{a.get('name')}: Farji mat samjho yaar, apne gaon mein pehle dekha hai.\n{name_b}: Chalo, trial toh kar sakte hain.",
        f"{a.get('name')}: {name_b}, {topic_label} lena chahta hoon kya?\n{name_b}: Paisa ka kya plan hai? EMI chalega?\n{a.get('name')}: EMI pe hi soch raha hoon.\n{name_b}: Toh pehle ek neighbour se baat karo.",
    ]
    return rng.choice(templates)


def pick_verdict(a: dict, b: dict, rng: random.Random) -> str:
    """Deterministic outcome: higher stance b and lower a stance -> more likely convinced."""
    p = 0.5 + (float(b.get("stance", 0.5)) - float(a.get("stance", 0.5))) * 0.7 + rng.gauss(0, 0.15)
    p = max(0.05, min(0.95, p))
    r = rng.random()
    if r < p:
        return "convinced"
    if r < p + (1 - p) * 0.6:
        return "sceptical"
    return "indifferent"


def sample_encounters(agents: list[dict], adopted_mask, day: int, topic: dict, rng: random.Random, n: int = 3) -> list[tuple[dict, dict]]:
    """Pick pairs of agents to talk — prefer one adopted/higher-stance with one undecided."""
    if len(agents) < 2:
        return []
    pairs = []
    for _ in range(n):
        i = rng.randrange(len(agents))
        j = rng.randrange(len(agents))
        if i == j:
            continue
        a_idx, b_idx = agents[i], agents[j]
        if float(a_idx["traits"].get("voice", 0.5)) < float(b_idx["traits"].get("voice", 0.5)):
            a_idx, b_idx = b_idx, a_idx
        pairs.append((a_idx, b_idx))
    return pairs


__all__ = ["resolve_encounter", "sample_encounters", "situation_type", "person_type", "action_rule"]
