from __future__ import annotations

from pathlib import Path
from typing import Dict

from backend.common.models import AgentCard

from . import gtp, kpm, mac, orchestrator, pdcp, rc, rlc, slice, tc


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
    return {agent.id: agent for agent in agents}
