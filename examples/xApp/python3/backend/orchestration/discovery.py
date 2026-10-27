"""Agent-Card discovery: lexical retrieval over the registry.

With a handful of cards the planner prompt can carry the whole registry;
with a directory of 50+ rApps it cannot, and the Discover agent has to
retrieve candidates first. This module implements BM25 over the card text
(name, description, capabilities, skills, use cases, interfaces, data
models) with no external dependencies, so the retrieval step itself is
reproducible and cheap. An embedding backend can be added behind the same
`discover()` signature; the evaluation reports top-k recall of the
ground-truth cards so the two can be compared.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Sequence, Tuple

from backend.common.models import AgentCard

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SYNONYMS = {
    "energy": ["power", "sleep", "switch", "off", "saving", "consumption"],
    "qoe": ["experience", "mos", "quality"],
    "handover": ["mobility", "ho", "pingpong", "ping", "pong"],
    "slice": ["slicing", "sla", "tenant"],
    "latency": ["delay", "jitter", "rtt"],
    "throughput": ["capacity", "prb", "load"],
    "backhaul": ["transport", "tunnel", "queue", "bufferbloat"],
    "anomaly": ["outlier", "degradation", "fault", "root", "cause"],
    "tilt": ["antenna", "coverage", "ret"],
}


def tokenize(text: str) -> List[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(_SYNONYMS.get(token, []))
    return expanded


def card_text(card: AgentCard) -> str:
    parts: List[str] = [card.id.replace(".", " "), card.name, card.role, card.description]
    parts += list(card.capabilities) + list(card.skills) + list(card.use_cases) + list(card.interfaces)
    parts += list(card.consumes) + list(card.produces) + list(card.measurements)
    parts += [scope.target for scope in card.control_scopes]
    return " ".join(str(p).replace("_", " ").replace(".", " ") for p in parts)


class BM25Index:
    def __init__(self, cards: Iterable[AgentCard], k1: float = 1.5, b: float = 0.75):
        self.cards: List[AgentCard] = list(cards)
        self.k1 = k1
        self.b = b
        self.docs: List[Counter] = [Counter(tokenize(card_text(card))) for card in self.cards]
        self.doc_len = [sum(doc.values()) for doc in self.docs]
        self.avg_len = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 1.0
        df: Counter = Counter()
        for doc in self.docs:
            df.update(doc.keys())
        n = len(self.docs)
        self.idf: Dict[str, float] = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def score(self, query_tokens: Sequence[str], index: int) -> float:
        doc = self.docs[index]
        length = self.doc_len[index]
        total = 0.0
        for term in query_tokens:
            if term not in doc:
                continue
            tf = doc[term]
            idf = self.idf.get(term, 0.0)
            total += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
        return total

    def search(self, query: str, k: int) -> List[Tuple[AgentCard, float]]:
        tokens = tokenize(query)
        scored = [(card, self.score(tokens, i)) for i, card in enumerate(self.cards)]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k] if k > 0 else scored


def card_family(card: AgentCard) -> str:
    # rApp ids are rapp.<family>[.<vendor>|.v0]; xApps are their own family.
    parts = card.id.split(".")
    return ".".join(parts[:2]) if parts[0] == "rapp" and len(parts) >= 2 else card.id


def discover(
    registry: Dict[str, AgentCard],
    intent_text: str,
    k: int = 8,
    executable_only: bool = True,
    include_deprecated: bool = False,
    dedupe_families: bool = True,
) -> List[Tuple[AgentCard, float]]:
    """Rank registry cards for an intent.

    dedupe_families keeps only the best-scoring card of each capability
    family (vendor variants of the same function collapse to one slot) unless
    the intent text names that vendor, in which case the named variant is
    kept as well. This is part of the Discover agent's design; the
    evaluation can switch it off for the ablation.
    """
    cards = [
        card for card in registry.values()
        if (card.actions or not executable_only) and (include_deprecated or card.status != "deprecated")
    ]
    ranked = BM25Index(cards).search(intent_text, 0)
    if dedupe_families:
        lowered = intent_text.lower()
        seen: set = set()
        kept: List[Tuple[AgentCard, float]] = []
        for card, score in ranked:
            family = card_family(card)
            vendor_named = card.vendor.split()[0].lower() in lowered and card.id != family
            if vendor_named:
                # A named vendor variant rides along without taking the family's slot.
                kept.append((card, score))
                continue
            if family in seen:
                continue
            seen.add(family)
            kept.append((card, score))
        ranked = kept
    if k <= 0 or k >= len(ranked):
        # Small registry: return everything, ranked, so the prompt order is still informative.
        return ranked
    return ranked[:k]
