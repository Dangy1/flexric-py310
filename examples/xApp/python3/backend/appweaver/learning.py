"""AppWeaver learning variants: operator workflow-template cards and an experience memory.

Two retrievable knowledge sources that Discover adds to the Agent Cards (workstream F):

* **Workflow cards** (`appweaver_tpl`): the operator's predefined workflow templates
  (`backend/orchestration/config.py` WORKFLOW_TEMPLATES / WORKFLOW_ACTIONS) as cards with id,
  name, description and the ordered executable steps. This is exactly the platform information
  the rule router and the catalog-aware LLM baseline already have; no labels, notes or category.
* **Experience memory** (`appweaver_mem`): operator feedback on past (training) intents, one entry
  per intent: the intent sentence, the workflow(s) the operator accepted and up to two proposals
  the operator rejected with the reason. Built offline by `evaluation/build_experience_memory.py`
  from a training batch only. Retrieved by BM25 over the past intent sentences (top-k, score floor);
  an entry whose sentence is identical to the query is never returned (leakage guard, logged).

Both use the Discover tokenizer (`backend.orchestration.discovery.tokenize`) and the same BM25
parameters (k1 = 1.5, b = 0.75) as the Agent-Card retrieval.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from backend.orchestration.discovery import tokenize

# Templates: ranked by BM25, top-k (k = 3 is the operator's whole catalog, so every template is shown,
# best match first, as the catalog-aware baselines see it; k bounds a larger catalog). No similarity
# floor: on the training intents (intents_50) a score > 0 floor missed the operator's generic procedure
# (observe-diagnose-optimize, the rule router's default) for 5 of its 18 intents (no lexical overlap).
TEMPLATE_K = 3
TEMPLATE_MIN_SCORE: Optional[float] = None
MEMORY_K = 3
# BM25 floor, chosen leave-one-out on the training intents (intents_50) only: about the lower quartile
# of the 3rd-nearest past intent's score (drops weak lexical matches; 49/50 training intents keep >= 1).
MEMORY_MIN_SCORE = 4.0
MEMORY_ENTRY_KEYS = ("id", "intent", "accepted_workflows", "rejected", "provenance")
REJECTED_KEYS = ("workflow", "reasons", "count")


class TextBM25:
    """BM25 over plain-text documents with the Discover tokenizer (same formula as discovery.BM25Index)."""

    def __init__(self, texts: Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: List[Counter] = [Counter(tokenize(text)) for text in texts]
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
            total += self.idf.get(term, 0.0) * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
        return total

    def scores(self, query: str) -> List[float]:
        tokens = tokenize(query)
        return [self.score(tokens, i) for i in range(len(self.docs))]


def normalize_sentence(text: str) -> str:
    """Case/whitespace/trailing-punctuation-insensitive form used by the identical-sentence guard."""
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).rstrip(" .!?;:")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- workflow-template cards
def workflow_cards(
    templates: Mapping[str, Mapping[str, Any]],
    actions: Mapping[str, Mapping[str, str]],
    registry: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """The operator's workflow templates as cards (config order).

    Steps are the template's executable chain (WORKFLOW_ACTIONS order, the same chain the rule router
    deploys and the catalog-aware LLM is shown); an action id the registry card no longer has is
    dropped so Compose resolves the card's default action.
    """
    cards: List[Dict[str, Any]] = []
    for workflow_id, template in templates.items():
        steps: List[Dict[str, Any]] = []
        for agent_id, action_id in (actions.get(workflow_id) or {}).items():
            step: Dict[str, Any] = {"agent_id": str(agent_id).lower()}
            card = (registry or {}).get(str(agent_id).lower()) if registry is not None else None
            if registry is None or (card is not None and any(a.id == str(action_id) for a in card.actions)):
                step["action_id"] = str(action_id)
            steps.append(step)
        cards.append(
            {
                "workflow_id": str(workflow_id),
                "name": str(template.get("label") or workflow_id),
                "description": str(template.get("description") or ""),
                "generated_workflow": [s["agent_id"].upper() for s in steps],
                "steps": steps,
            }
        )
    return cards


def default_workflow_cards(registry: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    from backend.orchestration.config import WORKFLOW_ACTIONS, WORKFLOW_TEMPLATES

    return workflow_cards(WORKFLOW_TEMPLATES, WORKFLOW_ACTIONS, registry)


def workflow_card_text(card: Mapping[str, Any]) -> str:
    parts = [str(card.get("workflow_id", "")), str(card.get("name", "")), str(card.get("description", ""))]
    for step in card.get("steps") or []:
        parts += [str(step.get("agent_id", "")), str(step.get("action_id", ""))]
    return " ".join(p.replace("-", " ").replace("_", " ").replace(".", " ").replace("/", " ") for p in parts)


def retrieve_workflow_cards(
    cards: Sequence[Mapping[str, Any]], intent_text: str, k: int = TEMPLATE_K, min_score: Optional[float] = TEMPLATE_MIN_SCORE,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """BM25 over the workflow cards; top-k (score > min_score if a floor is set), best first (ties: catalog order)."""
    cards = [dict(card) for card in cards]
    scores = TextBM25([workflow_card_text(card) for card in cards]).scores(intent_text) if cards else []
    order = sorted(range(len(cards)), key=lambda i: (-scores[i], i))
    kept = [i for i in order if min_score is None or scores[i] > min_score]
    if k > 0:
        kept = kept[:k]
    report = {
        "k": k,
        "min_score": min_score,
        "catalog": [card["workflow_id"] for card in cards],
        "retrieved": [cards[i]["workflow_id"] for i in kept],
        "scores": {cards[i]["workflow_id"]: round(scores[i], 3) for i in order},
    }
    return [cards[i] for i in kept], report


# ---------------------------------------------------------------- experience memory
def validate_entry(entry: Mapping[str, Any]) -> None:
    """Memory entries carry only an id, the intent sentence, chains, rejection reasons and provenance."""
    extra = set(entry) - set(MEMORY_ENTRY_KEYS)
    if extra:
        raise ValueError(f"memory entry {entry.get('id')!r} has disallowed keys {sorted(extra)} (labels/notes/category must not enter memory)")
    if not str(entry.get("intent") or "").strip():
        raise ValueError(f"memory entry {entry.get('id')!r} has no intent sentence")
    for rejected in entry.get("rejected") or []:
        extra = set(rejected) - set(REJECTED_KEYS)
        if extra:
            raise ValueError(f"memory entry {entry.get('id')!r}: rejected proposal has disallowed keys {sorted(extra)}")


class ExperienceMemory:
    def __init__(self, entries: Iterable[Mapping[str, Any]], path: Optional[str] = None, sha256: Optional[str] = None,
                 k: int = MEMORY_K, min_score: float = MEMORY_MIN_SCORE):
        self.entries: List[Dict[str, Any]] = [dict(entry) for entry in entries]
        for entry in self.entries:
            validate_entry(entry)
        self.path = path
        self.sha256 = sha256
        self.k = k
        self.min_score = min_score
        self.index = TextBM25([str(entry["intent"]) for entry in self.entries])
        self._normalized = [normalize_sentence(entry["intent"]) for entry in self.entries]

    @classmethod
    def load(cls, path: str | Path, **kwargs: Any) -> "ExperienceMemory":
        p = Path(path).expanduser().resolve()
        entries = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(entries, path=str(p), sha256=_sha256(p), **kwargs)

    def describe(self) -> Dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "entry_count": len(self.entries), "k": self.k, "min_score": self.min_score}

    def retrieve(self, intent_text: str, k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        k = self.k if k is None else k
        floor = self.min_score if min_score is None else min_score
        query = normalize_sentence(intent_text)
        scores = self.index.scores(intent_text) if self.entries else []
        excluded = [i for i, sentence in enumerate(self._normalized) if sentence == query]
        order = sorted((i for i in range(len(self.entries)) if i not in excluded), key=lambda i: (-scores[i], i))
        above = [i for i in order if scores[i] >= floor and scores[i] > 0.0]
        kept = above[:k] if k > 0 else above
        retrieved = [{**self.entries[i], "score": round(scores[i], 3)} for i in kept]
        report = {
            **self.describe(),
            "k": k,
            "min_score": floor,
            "memory_retrieved": [{"id": self.entries[i]["id"], "score": round(scores[i], 3)} for i in kept],
            "excluded_identical": [self.entries[i]["id"] for i in excluded],
            "below_floor": len(order) - len(above),
            "best_score": round(scores[order[0]], 3) if order else None,
        }
        return retrieved, report
