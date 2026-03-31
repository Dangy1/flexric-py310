from __future__ import annotations

from backend.common.models import AgentCard


def build_agent() -> AgentCard:
    return AgentCard(
        id='mac',
        name='MAC Agent',
        role='Scheduler and PRB analyst',
        service_model='MAC',
        description='Interprets MAC-level scheduling pressure and links PRB utilization to slice or TC actions.',
        page_path='/agents/mac',
        a2a_card_path='/.well-known/agents/mac.json',
        status='ready',
        activity='Idle; waiting for MAC telemetry handoff.',
        skills=['mac.observe', 'mac.correlate', 'mac.recommend'],
        measurements=['DL/UL PRB usage', 'scheduler pressure', 'UE contention'],
        use_cases=['Scheduler tuning', 'congestion triage', 'slice fairness review'],
        peers=['orchestrator', 'kpm', 'slice', 'tc'],
        providers=['ollama', 'openai'],
        actions=[],
        notes=['Uses shared monitor flows today; a dedicated MAC suite can be plugged in later.'],
    )
