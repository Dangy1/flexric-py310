from __future__ import annotations

from backend.common.models import AgentCard


def build_agent() -> AgentCard:
    return AgentCard(
        id='pdcp',
        name='PDCP Agent',
        role='Session continuity analyst',
        service_model='PDCP',
        description='Tracks PDCP-level behavior to explain downstream transport or user-plane issues.',
        page_path='/agents/pdcp',
        a2a_card_path='/.well-known/agents/pdcp.json',
        status='ready',
        activity='Idle; waiting for transport or UE quality review.',
        skills=['pdcp.observe', 'pdcp.trace', 'pdcp.compare'],
        measurements=['PDCP bearer stats', 'delivery patterns', 'control side effects'],
        use_cases=['Session diagnostics', 'handover-effect review'],
        peers=['orchestrator', 'rlc', 'gtp'],
        providers=['ollama', 'openai'],
        actions=[],
        notes=['Works best as a secondary explanation agent after MAC/RLC anomalies.'],
    )
