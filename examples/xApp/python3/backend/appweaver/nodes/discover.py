"""Discover: BM25 retrieval over Agent Cards (backend/orchestration/discovery.py, wrapped by the harness)."""
from __future__ import annotations

from typing import Any, Callable, Dict

from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import event


def build_discover_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    def discover_node(state: AppWeaverState) -> Dict[str, Any]:
        excluded = list(state.get("excluded_agents") or [])
        cards, report = deps.discover(state["intent_text"], excluded)
        ids = [card.id for card in cards]
        return {
            "retrieval": report,
            "card_ids": ids,
            "events": [event(deps, state, "discover", "retrieved", count=len(ids), pinned=report.get("pinned"), excluded=excluded)],
        }

    return discover_node
