"""Discover: BM25 retrieval over Agent Cards (backend/orchestration/discovery.py, wrapped by the harness).

Learning variants (backend/appweaver/learning.py): with `cfg.workflow_templates` Discover also
retrieves the operator's workflow-template cards; with `cfg.memory_path` it recalls similar past
intents from the experience memory (identical sentences excluded). AppWeaver itself does neither.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..learning import ExperienceMemory, default_workflow_cards, retrieve_workflow_cards
from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import event

_MEMORY_CACHE: Dict[tuple, ExperienceMemory] = {}


def load_memory(cfg: AppWeaverConfig) -> ExperienceMemory:
    """Experience memory for `cfg.memory_path` (cached per path, k and floor; reloaded if the file changes)."""
    from pathlib import Path

    path = Path(str(cfg.memory_path)).expanduser().resolve()
    key = (str(path), path.stat().st_mtime_ns, int(cfg.memory_k), float(cfg.memory_min_score))
    if key not in _MEMORY_CACHE:
        _MEMORY_CACHE[key] = ExperienceMemory.load(path, k=int(cfg.memory_k), min_score=float(cfg.memory_min_score))
    return _MEMORY_CACHE[key]


def build_discover_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    retrieve_templates: Optional[Callable] = None
    if cfg.workflow_templates:
        if deps.retrieve_templates is not None:
            retrieve_templates = deps.retrieve_templates
        else:
            catalog = default_workflow_cards(deps.registry)
            retrieve_templates = lambda text: retrieve_workflow_cards(catalog, text, k=int(cfg.template_k))  # noqa: E731
    recall: Optional[Callable] = None
    if cfg.memory_path:
        recall = deps.recall_memory or load_memory(cfg).retrieve

    def discover_node(state: AppWeaverState) -> Dict[str, Any]:
        excluded = list(state.get("excluded_agents") or [])
        cards, report = deps.discover(state["intent_text"], excluded)
        ids = [card.id for card in cards]
        out: Dict[str, Any] = {"retrieval": report, "card_ids": ids}
        detail: Dict[str, Any] = {}
        if retrieve_templates is not None:
            workflow_cards, template_report = retrieve_templates(state["intent_text"])
            out.update({"workflow_cards": list(workflow_cards), "template_retrieval": template_report})
            detail["templates"] = [c.get("workflow_id") for c in workflow_cards]
        if recall is not None:
            entries, memory_report = recall(state["intent_text"])
            out.update({"memory_entries": list(entries), "memory_retrieval": memory_report})
            detail["memory"] = [e.get("id") for e in entries]
            if memory_report.get("excluded_identical"):
                detail["memory_excluded_identical"] = list(memory_report["excluded_identical"])
        out["events"] = [event(deps, state, "discover", "retrieved", count=len(ids), pinned=report.get("pinned"), excluded=excluded, **detail)]
        return out

    return discover_node
