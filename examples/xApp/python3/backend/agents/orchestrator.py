from __future__ import annotations

from backend.common.models import AgentCard


def build_agent() -> AgentCard:
    return AgentCard(
        id='orchestrator',
        name='RIC Orchestrator',
        role='Chain planner and agent router',
        service_model='Cross-SM',
        description='Coordinates domain agents, builds multi-agent chains, and exposes A2A-style discovery and handoff.',
        page_path='/agents/orchestrator',
        a2a_card_path='/.well-known/agents/orchestrator.json',
        status='ready',
        activity='Waiting for a network automation goal.',
        skills=['plan.chain', 'route.handoff', 'summarize.state', 'track.workflow'],
        measurements=['Workflow latency', 'handoff count', 'run success rate'],
        use_cases=['Cross-agent automation', 'incident triage', 'closed-loop coordination'],
        peers=['kpm', 'mac', 'slice', 'tc', 'rc', 'rlc', 'pdcp', 'gtp'],
        providers=['ollama', 'openai'],
        actions=[],
        notes=[
            'A2A-ready card and JSON-RPC handoff endpoints are exposed by this portal.',
            'Use this agent as the entry point for chained workflows.',
        ],
    )
