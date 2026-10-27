from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from backend.common.models import AgentAction, AgentCard, ControlScope


def catalog_path(base_dir: Path) -> Path:
    configured = os.getenv("FLEXRIC_RAPP_CATALOG", "").strip()
    if configured:
        return Path(configured)
    return base_dir / "rapps" / "catalog.json"


def rapps_enabled() -> bool:
    # Off by default so the 9-card portal behaves as before; the evaluation
    # harness and the stack script switch it on for registry-scale runs.
    return os.getenv("FLEXRIC_RAPP_DIRECTORY", "").strip().lower() in {"1", "true", "yes", "on"}


def build_agents(python_bin: str, base_dir: Path) -> Dict[str, AgentCard]:
    path = catalog_path(base_dir)
    if not path.exists():
        return {}
    entries = json.loads(path.read_text(encoding="utf-8"))
    runtime = base_dir / "rapps" / "runtime.py"
    cards: Dict[str, AgentCard] = {}
    for entry in entries:
        actions: List[AgentAction] = [
            AgentAction(
                id=tool["id"],
                label=tool["label"],
                description=tool["description"],
                kind="rapp",
                command=[python_bin, "-u", str(runtime), "--rapp", entry["id"], "--tool", tool["id"], "--duration-s", "10"],
            )
            for tool in entry.get("tools", [])
        ]
        card = AgentCard(
            id=entry["id"],
            name=entry["name"],
            role=f"{entry['solution_area']} rApp",
            service_model="Non-RT",
            description=entry["description"],
            page_path=f"/agents/{entry['id']}",
            a2a_card_path=f"/.well-known/agents/{entry['id']}.json",
            status="deprecated" if entry.get("status") == "deprecated" else "ready",
            activity="Idle; emulated rApp served by rapps/runtime.py.",
            skills=[f"{entry['family']}.{tool['id']}" for tool in entry.get("tools", [])],
            measurements=list(entry.get("consumes", [])),
            use_cases=[entry["use_case"]],
            peers=["orchestrator", "kpm", "rc"],
            providers=["ollama", "openai"],
            actions=actions,
            notes=list(entry.get("notes", [])) + ["Emulated rApp: decisions are simple estimators over live KPM, pushed as A1-style policies."],
            app_type="rapp",
            ric="non-rt",
            vendor=entry["vendor"],
            version=entry["version"],
            interfaces=list(entry.get("interfaces", [])),
            consumes=list(entry.get("consumes", [])),
            produces=list(entry.get("produces", [])),
            control_scopes=[ControlScope(**scope) for scope in entry.get("control_scopes", [])],
            timescale_s=float(entry.get("timescale_s", 60)),
            requires=list(entry.get("requires", [])),
            conflicts_with=list(entry.get("conflicts_with", [])),
            mcp_endpoint=os.getenv("FLEXRIC_RAPP_MCP_URL", "http://127.0.0.1:8010/mcp"),
            capabilities=list(entry.get("capabilities", [])),
        )
        cards[card.id] = card
    return cards
