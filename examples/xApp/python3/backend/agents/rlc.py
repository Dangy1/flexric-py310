from __future__ import annotations

from backend.common.models import AgentCard


def build_agent() -> AgentCard:
    return AgentCard(
        id='rlc',
        name='RLC Agent',
        role='Bearer health analyst',
        service_model='RLC',
        description='Correlates queue and bearer behavior with TC and slice actions.',
        page_path='/agents/rlc',
        a2a_card_path='/.well-known/agents/rlc.json',
        status='ready',
        activity='Idle; waiting for TC or MAC handoff.',
        skills=['rlc.observe', 'rlc.compare', 'rlc.validate'],
        measurements=['Radio bearer stats', 'latency shifts', 'queue depth clues'],
        use_cases=['QoS troubleshooting', 'post-control validation'],
        peers=['orchestrator', 'tc', 'mac', 'pdcp'],
        providers=['ollama', 'openai'],
        actions=[],
        notes=['Often paired with the TC agent for feedback verification.'],
    )
