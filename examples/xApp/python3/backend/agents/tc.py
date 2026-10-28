from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    return AgentCard(
        id='tc',
        name='TC Agent',
        role='Traffic control enforcer',
        service_model='TC',
        description=('Applies transport/queue control over the TC service model: CoDel or ECN active queue management, shaping, '
                     'partitioning and traffic classification on the bearer path. Use when the goal is queueing delay, jitter, '
                     'bufferbloat or per-class transport treatment. Do not use for slice PRB reservation (SLICE) or radio '
                     'parameters such as handover, tilt or cell power.'),
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
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-TC (FlexRIC custom)', 'E2SM-RLC (FlexRIC custom)'],
        consumes=['DRB.RlcSduDelayDl'],
        produces=['tc.policy', 'RLC.queue_stats'],
        control_scopes=[ControlScope(target='transport', mode='write', resource='tc_control')],
        timescale_s=1.0,
        capabilities=['transport_qos', 'bufferbloat_mitigation', 'traffic_shaping'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
        workflow_role='control',
    )
