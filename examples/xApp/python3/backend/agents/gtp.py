from __future__ import annotations

from backend.common.models import AgentCard


def build_agent() -> AgentCard:
    return AgentCard(
        id='gtp',
        name='GTP Agent',
        role='Transport tunnel analyst',
        service_model='GTP',
        description='Monitors user-plane tunnel behavior and supports end-to-end performance diagnosis.',
        page_path='/agents/gtp',
        a2a_card_path='/.well-known/agents/gtp.json',
        status='ready',
        activity='Idle; waiting for transport diagnostics tasks.',
        skills=['gtp.observe', 'gtp.trace', 'gtp.explain'],
        measurements=['NG-U tunnel stats', 'transport throughput', 'packet path behavior'],
        use_cases=['Backhaul diagnosis', 'end-to-end throughput review'],
        peers=['orchestrator', 'tc', 'pdcp'],
        providers=['ollama', 'openai'],
        actions=[],
        notes=['Pairs with TC and PDCP for transport-aware automation loops.'],
    )
