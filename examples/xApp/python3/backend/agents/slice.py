from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    # Per-action scope: `monitor` only subscribes to SLICE indications (read); `apply-static`
    # sends an E2 SLICE CONTROL (write). The card-level scope is the union (write).
    monitor = suite_action('monitor', 'Monitor Slice State', 'Run the slice suite in monitor mode (read-only: subscribes to slice indications, sends no control).', python_bin, base_dir, 'xapp_slice_suite.py', '--profile', 'monitor', '--duration-s', '30', '--verbose')
    monitor.control_scopes = [ControlScope(target='slice', mode='read', resource='slice_control')]
    apply_static = suite_action('apply-static', 'Apply Static Slice', 'Apply the STATIC profile (E2 SLICE CONTROL) and monitor it.', python_bin, base_dir, 'xapp_slice_suite.py', '--profile', 'static', '--duration-s', '30', '--verbose')
    apply_static.control_scopes = [ControlScope(target='slice', mode='write', resource='slice_control')]
    return AgentCard(
        id='slice',
        name='Slice Agent',
        role='Slice policy and assurance controller',
        service_model='SLICE',
        description=('Applies and validates RAN slice policies (PRB reservation per slice, STATIC profile) over E2SM-SLICE, then reports '
                     'UE-to-slice associations and reserved capacity. Use when the goal needs per-slice resource partitioning, slice '
                     'isolation or a slice reconfiguration, or a read of the current slice state (monitor action). Do not use for '
                     'transport/queue policies (TC) or for per-UE scheduling priority.'),
        page_path='/agents/slice',
        a2a_card_path='/.well-known/agents/slice.json',
        status='ready',
        activity='Idle; ready to monitor or apply a slice profile.',
        skills=['slice.monitor', 'slice.apply', 'slice.verify', 'slice.associate-ue'],
        measurements=['Slice counts', 'reserved PRBs', 'UE associations', 'slice scheduler'],
        use_cases=['Slice rollout', 'capacity partitioning', 'policy validation'],
        peers=['orchestrator', 'kpm', 'mac', 'rc'],
        providers=['ollama', 'openai'],
        actions=[monitor, apply_static],
        notes=['Backed by xapp_slice_suite.py profiles monitor/static/nvs-rate/nvs-cap/edf/all.'],
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-SLICE (FlexRIC custom)'],
        consumes=['RRU.PrbTotDl'],
        produces=['slice.policy', 'slice.ue_association'],
        control_scopes=[ControlScope(target='slice', mode='write', resource='slice_control')],
        timescale_s=1.0,
        capabilities=['slice_control', 'slice_assurance', 'capacity_partitioning'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
        workflow_role='control',
    )
