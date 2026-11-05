"""Generative Agents memory system, adapted for Imprint (cognitive neuroscience for Indian markets).

Implements the Stanford Generative Agents architecture (Park et al., UIST 2023):
  * Memory Stream — append-only record of observations and actions, each with
    timestamp, importance, and embedding (bag-of-terms as a cheap, honest stand-in
    for a sentence embedder; noted explicitly).
  * Retrieval — recency × importance × relevance score, top-k.
  * Reflection — an LLM (or deterministic fallback) derives belief insights from
    clusters of memories, appended back to the stream as "reflection" memories.
  * Planning — each agent forms a daily intention before acting.

No LLM is required: with no model, memories and reflections are produced by
deterministic templates seeded on the agent's traits. With a model, the same
functions produce open-ended natural language.
"""
from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field


@dataclass
class Memory:
    text: str
    kind: str  # "observation" | "action" | "reflection"
    importance: float
    day: int
    hour: float = 9.0
    embedding: list[float] = field(default_factory=list)
    id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "kind": self.kind,
            "importance": round(self.importance, 2),
            "day": self.day,
            "hour": round(self.hour, 2),
        }


def _embed(text: str) -> list[float]:
    """Cheap bag-of-terms embedding (32 dims). Deterministic and transparent."""
    vec = [0.0] * 32
    for tok in re.findall(r"[a-z]+", text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % 32] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


class MemoryStream:
    """Append-only memory for one agent."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memories: list[Memory] = []
        self._seq = 0

    def add(self, text: str, kind: str, importance: float, day: int, hour: float = 9.0) -> Memory:
        self._seq += 1
        mem = Memory(
            text=text,
            kind=kind,
            importance=max(0.0, min(1.0, importance)),
            day=day,
            hour=hour,
            embedding=_embed(text),
            id=f"{self.agent_id}-m{self._seq}",
        )
        self.memories.append(mem)
        return mem

    def retrieve(self, query: str, day: int, k: int = 3, decay: float = 0.5) -> list[Memory]:
        """Score memories by recency^α · importance^β · relevance^γ (Park et al. 2023)."""
        if not self.memories:
            return []
        q = _embed(query)
        scored = []
        for m in self.memories:
            # recency: exponential decay with half-life of 30 days
            age_days = max(0, day - m.day) + max(0, hour_delay(day, m))
            recency = 0.5 ** (age_days / 30.0)
            importance = 0.4 + 0.6 * m.importance
            relevance = max(0.0, _cosine(q, m.embedding))
            score = recency * importance * relevance
            scored.append((score, m))
        scored.sort(key=lambda x: -x[0])
        return [m for s, m in scored if s > 0][:k]

    def context_block(self, query: str, day: int, k: int = 3) -> str:
        """Render retrieved memories as a prompt block for LLM calls."""
        picked = self.retrieve(query, day, k=k)
        if not picked:
            return "(no memories yet)"
        lines = ["What I remember:"]
        for m in picked:
            lines.append(f"- [day {m.day}] {m.text}")
        return "\n".join(lines)

    def reflect(self, agent: dict, topic_label: str, day: int, llm_fn) -> list[str]:
        """Derive higher-level beliefs from recent memories. Appends reflections."""
        recent = self.memories[-6:]
        if len(recent) < 2:
            return []
        texts = "; ".join(m.text for m in recent)
        prompt = (
            f"Agent {agent.get('name')} ({agent.get('occupation')}, tier {agent.get('tier')}) "
            f"observed about {topic_label}: {texts}\n"
            f"Summarize 1-2 firm beliefs the agent would form from these. "
            f"One sentence each, in the agent's voice."
        )
        raw = llm_fn(prompt, max_tokens=80, temperature=0.6) if llm_fn else None
        if raw:
            lines = [ln.strip("-•1234567890. ").strip() for ln in raw.split("\n") if ln.strip()]
            lines = [ln for ln in lines if len(ln) > 12][:2]
        else:
            # deterministic fallback: synthesize from traits
            stance = float(agent.get("stance", 0.5))
            if stance >= 0.6:
                lines = [f"I want to try {topic_label.lower()} if the local setup is trustworthy."]
            elif stance <= 0.4:
                lines = [f"I still doubt {topic_label.lower()} at this price."]
            else:
                lines = [f"I am curious but waiting for someone I trust to vouch for it."]
        for line in dict.fromkeys(lines):  # dedupe preserving order
            if any(line == m.text for m in self.memories if m.kind == "reflection"):
                continue
            self.add(line, "reflection", importance=0.85, day=day)
        return lines

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "count": len(self.memories),
            "memories": [m.to_dict() for m in self.memories[-20:]],
            "reflections": [m.text for m in self.memories if m.kind == "reflection"],
        }


def hour_delay(day: int, m: Memory) -> float:
    return 0.0  # same-day memories are equally recent; kept simple and explicit


def seed_memories(agent: dict, topic_label: str, day: int) -> list[tuple[str, str, float]]:
    """Initial memories every agent starts with (from Generative Agents init)."""
    traits = agent.get("traits", {})
    out = [
        (f"I live in {agent.get('city')} and work as {agent.get('occupation')}.", "observation", 0.3),
        (f"I have {agent.get('household_income', 0) and 'enough' or 'limited'} money for household expenses.", "observation", 0.5),
        (f"I know about {topic_label.lower()} — saw it on my phone / heard from neighbours.", "observation", 0.4),
    ]
    if traits.get("risk", 0.5) > 0.6:
        out.append(("I am generally cautious. One bad experience and I write it off.", "disposition", 0.6))
    else:
        out.append(("I like trying new things before others do.", "disposition", 0.6))
    return out


def encounter_note(a: dict, b: dict, day: int, topic_label: str) -> str:
    """What both agents observe at an encounter (before conversation)."""
    return (
        f"Day {day}: {a.get('name')} ({a.get('occupation')}) and {b.get('name')} ({b.get('occupation')}) "
        f"met near {a.get('city')} market and talked about {topic_label.lower()}."
    )

__all__ = ["Memory", "MemoryStream", "seed_memories", "encounter_note"]
