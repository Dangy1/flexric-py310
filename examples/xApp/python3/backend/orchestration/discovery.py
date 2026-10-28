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
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

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


def pinned_xapp_ids(registry: Dict[str, AgentCard]) -> List[str]:
    """Executable near-RT xApps of the platform (kpm, slice, tc, rc).

    They are the control/observation primitives every chain is built from, so the
    Discover step always hands them to the planner; top-k only bounds the rApp
    directory (review P0-6: at k=8 KPM/RC/SLICE were outranked by rApp families).
    """
    return sorted(
        card.id for card in registry.values()
        if card.actions and getattr(card, "app_type", "xapp") == "xapp" and card.status != "deprecated"
    )


def discover_with_report(
    registry: Dict[str, AgentCard],
    intent_text: str,
    k: int = 8,
    executable_only: bool = True,
    include_deprecated: bool = True,
    dedupe_families: bool = True,
    pin: Optional[Sequence[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> Tuple[List[Tuple[AgentCard, float]], Dict[str, object]]:
    """Rank registry cards for an intent and explain the selection.

    * ``pin``: card ids that are always returned (ahead of the ranked rApps) and
      never consume one of the ``k`` slots.
    * ``k`` bounds the number of *families* among the non-pinned cards
      (``k <= 0`` returns every family).
    * ``dedupe_families`` keeps the best-scoring active card of each family; a
      vendor variant named in the intent text and the family's deprecated
      releases ride along with the family's slot instead of taking one.
    * ``include_deprecated`` keeps deprecated cards visible (marked by their
      ``status``) so the planner can be caught selecting them; Compose/Validate
      reject them (``compat.lifecycle_findings``).
    * ``exclude``: ids removed before ranking (Recover re-plans around busy apps).
    """
    excluded = {str(item).strip().lower() for item in (exclude or []) if str(item).strip()}
    pinned_ids = [pid for pid in (pin or []) if pid in registry and pid not in excluded]
    cards = [
        card for card in registry.values()
        if (card.actions or not executable_only)
        and (include_deprecated or card.status != "deprecated")
        and card.id not in excluded
    ]
    ranked = BM25Index(cards).search(intent_text, 0)
    by_id = {card.id: (card, score) for card, score in ranked}
    pinned = [by_id[pid] for pid in pinned_ids if pid in by_id]
    pinned.sort(key=lambda item: item[1], reverse=True)
    pinned_set = {card.id for card, _ in pinned}
    rest = [(card, score) for card, score in ranked if card.id not in pinned_set]

    lowered = intent_text.lower()
    slots: List[List[Tuple[AgentCard, float]]] = []
    if dedupe_families:
        family_slot: Dict[str, int] = {}
        riders: Dict[str, List[Tuple[AgentCard, float]]] = {}
        for card, score in rest:
            family = card_family(card)
            vendor_named = card.id != family and bool(card.vendor) and card.vendor.split()[0].lower() in lowered
            rider = card.status == "deprecated" or vendor_named
            if rider:
                riders.setdefault(family, []).append((card, score))
                continue
            if family in family_slot:
                continue
            family_slot[family] = len(slots)
            slots.append([(card, score)])
        for family, items in riders.items():
            if family in family_slot:
                slots[family_slot[family]].extend(items)
            else:
                # A family with only deprecated/vendor cards still gets one slot.
                family_slot[family] = len(slots)
                slots.append(list(items))
        slots.sort(key=lambda slot: slot[0][1], reverse=True)
    else:
        slots = [[item] for item in rest]
    kept_slots = slots if k <= 0 else slots[:k]
    selected = list(pinned) + [item for slot in kept_slots for item in slot]
    report: Dict[str, object] = {
        "k": k,
        "pinned": [card.id for card, _ in pinned],
        "family_slots": [slot[0][0].id for slot in kept_slots],
        "riders": [item[0].id for slot in kept_slots for item in slot[1:]],
        "deprecated_visible": [card.id for card, _ in selected if card.status == "deprecated"],
        "excluded": sorted(excluded),
        "candidate_count": len(cards),
    }
    return selected, report


def discover(
    registry: Dict[str, AgentCard],
    intent_text: str,
    k: int = 8,
    executable_only: bool = True,
    include_deprecated: bool = False,
    dedupe_families: bool = True,
    pin: Optional[Sequence[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> List[Tuple[AgentCard, float]]:
    """Backward-compatible wrapper around :func:`discover_with_report`."""
    selected, _ = discover_with_report(
        registry, intent_text, k=k, executable_only=executable_only,
        include_deprecated=include_deprecated, dedupe_families=dedupe_families, pin=pin, exclude=exclude,
    )
    return selected
