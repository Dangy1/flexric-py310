from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    return AgentCard(
        id='rc',
        name='RC Agent',
        role='RAN control reasoning agent',
        service_model='RC',
        description='Tracks control opportunities, validates actions, and acts as the policy gate for automation loops.',
        page_path='/agents/rc',
        a2a_card_path='/.well-known/agents/rc.json',
        status='ready',
        activity='Idle; RC auto-builder is still scaffolded in Python.',
        skills=['rc.review', 'rc.gate', 'rc.validate'],
        measurements=['Procedure IDs', 'control outcomes', 'policy checkpoints'],
        use_cases=['Control approval', 'policy simulation', 'closed-loop validation'],
        peers=['orchestrator', 'kpm', 'slice', 'tc'],
        providers=['ollama', 'openai'],
        actions=[
            suite_action('rc-scaffold', 'Run RC Scaffold', 'Run the KPM/RC suite in RC scaffold mode.', python_bin, base_dir, 'xapp_kpm_rc_suite.py', '--profile', 'rc', '--duration-s', '30'),
        ],
        notes=['RC is exposed as a workflow/scaffold today; Python auto-subscription builder is still a next step.'],
    )
