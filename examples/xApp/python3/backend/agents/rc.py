from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


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
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-RC v1.03', 'E2SM-KPM v2.03'],
        consumes=[],
        produces=['rc.validation', 'rc.control_ack'],
        control_scopes=[ControlScope(target='cell', mode='write', resource='rc_control')],
        timescale_s=1.0,
        capabilities=['control_validation', 'policy_gate'],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
    )
