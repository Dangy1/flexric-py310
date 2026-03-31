from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    return AgentCard(
        id='tc',
        name='TC Agent',
        role='Traffic control enforcer',
        service_model='TC',
        description='Applies shaping, CoDel, ECN, partitioning, and queue strategies using the TC service model.',
        page_path='/agents/tc',
        a2a_card_path='/.well-known/agents/tc.json',
        status='ready',
        activity='Idle; waiting for policy or transport optimization tasks.',
        skills=['tc.shape', 'tc.codel', 'tc.ecn', 'tc.partition', 'tc.validate'],
        measurements=['Queue policy state', 'RLC side effects', 'traffic class actions'],
        use_cases=['QoS enforcement', 'bufferbloat mitigation', 'traffic segregation'],
        peers=['orchestrator', 'mac', 'rlc', 'gtp'],
        providers=['ollama', 'openai'],
        actions=[
            suite_action('apply-codel', 'Apply CoDel', 'Run the TC suite with the CoDel profile.', python_bin, base_dir, 'xapp_tc_suite.py', '--profile', 'codel', '--duration-s', '30'),
            suite_action('apply-all', 'Run Full TC Flow', 'Run the TC suite with the full profile and RLC monitor.', python_bin, base_dir, 'xapp_tc_suite.py', '--profile', 'all', '--duration-s', '30', '--monitor-rlc'),
        ],
        notes=['Backed by xapp_tc_suite.py profiles segregate/partition/shaper/codel/ecn/osi_codel/all.'],
    )
