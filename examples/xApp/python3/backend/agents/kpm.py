from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    return AgentCard(
        id='kpm',
        name='KPM Agent',
        role='Measurement and KPI analyst',
        service_model='KPM',
        description='Consumes shared KPM telemetry from the single-owner KPM bus and surfaces radio/resource measurements for downstream agents.',
        page_path='/agents/kpm',
        a2a_card_path='/.well-known/agents/kpm.json',
        status='ready',
        activity='Idle; ready to read shared RRU or UE-oriented KPM records from the KPM bus.',
        skills=['kpm.observe', 'kpm.filter', 'kpm.explain', 'kpm.report'],
        measurements=['RRU.PrbTotDl', 'RRU.PrbTotUl', 'DRB.* UE metrics'],
        use_cases=['Congestion detection', 'capacity reporting', 'SLA evidence'],
        peers=['orchestrator', 'mac', 'slice', 'rc'],
        providers=['ollama', 'openai'],
        actions=[
            suite_action('observe-rru', 'Observe RRU KPIs', 'Read shared RRU-oriented KPM records from the KPM bus for a short window.', python_bin, base_dir, 'xapp_kpm_bus_reader.py', '--mode', 'rru', '--duration-s', '30'),
            suite_action('observe-ue', 'Observe UE KPIs', 'Read shared UE/DRB-oriented KPM records from the KPM bus for a short window.', python_bin, base_dir, 'xapp_kpm_bus_reader.py', '--mode', 'ue', '--duration-s', '30'),
        ],
        notes=['Backed by the shared kpm_bus_service.py collector and xapp_kpm_bus_reader.py readers.'],
    )
