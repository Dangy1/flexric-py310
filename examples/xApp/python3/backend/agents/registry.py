from __future__ import annotations

from pathlib import Path
from typing import Dict

from backend.common.models import AgentCard

from . import gtp, kpm, mac, orchestrator, pdcp, rapps, rc, rlc, slice, tc


def build_agents(python_bin: str, base_dir: Path) -> Dict[str, AgentCard]:
    agents = [
        orchestrator.build_agent(),
        kpm.build_agent(python_bin, base_dir),
        mac.build_agent(),
        slice.build_agent(python_bin, base_dir),
        tc.build_agent(python_bin, base_dir),
        rc.build_agent(python_bin, base_dir),
        rlc.build_agent(),
        pdcp.build_agent(),
        gtp.build_agent(),
    ]
    registry = {agent.id: agent for agent in agents}
    # The rApp Directory (FLEXRIC_RAPP_DIRECTORY=1) adds the emulated rApp
    # cards from rapps/catalog.json so discovery runs over a realistic registry.
    if rapps.rapps_enabled():
        registry.update(rapps.build_agents(python_bin, base_dir))
    return registry
