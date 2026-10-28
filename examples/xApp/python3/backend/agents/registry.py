from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from backend.common.models import AgentCard

from . import gtp, kpm, mac, orchestrator, pdcp, rapps, rc, rlc, slice, tc


L2_MONITOR_IDS = ("mac", "rlc", "pdcp", "gtp")


def l2_monitors_enabled() -> bool:
    return os.getenv("FLEXRIC_L2_MONITORS", "1").strip().lower() not in {"0", "false", "no", "off"}


def build_agents(python_bin: str, base_dir: Path) -> Dict[str, AgentCard]:
    agents = [
        orchestrator.build_agent(),
        kpm.build_agent(python_bin, base_dir),
        mac.build_agent(python_bin, base_dir),
        slice.build_agent(python_bin, base_dir),
        tc.build_agent(python_bin, base_dir),
        rc.build_agent(python_bin, base_dir),
        rlc.build_agent(python_bin, base_dir),
        pdcp.build_agent(python_bin, base_dir),
        gtp.build_agent(python_bin, base_dir),
    ]
    registry = {agent.id: agent for agent in agents}
    # The FlexRIC L2 monitor cards (mac, rlc, pdcp, gtp) are executable read-only xApps backed by
    # xapp_l2_monitor.py. FLEXRIC_L2_MONITORS=0 turns them back into descriptive cards (no actions),
    # e.g. to reproduce the registry of runs made before 2026-10-28.
    if not l2_monitors_enabled():
        for agent_id in L2_MONITOR_IDS:
            registry[agent_id].actions = []
    # The rApp Directory (FLEXRIC_RAPP_DIRECTORY=1) adds the emulated rApp
    # cards from rapps/catalog.json so discovery runs over a realistic registry.
    if rapps.rapps_enabled():
        registry.update(rapps.build_agents(python_bin, base_dir))
    return registry
