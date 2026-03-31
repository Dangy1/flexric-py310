from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    return AgentCard(
        id='slice',
        name='Slice Agent',
        role='Slice policy and assurance controller',
        service_model='SLICE',
        description='Applies and validates slice policies, then reports UE-to-slice associations and reserved capacity.',
        page_path='/agents/slice',
        a2a_card_path='/.well-known/agents/slice.json',
        status='ready',
        activity='Idle; ready to monitor or apply a slice profile.',
        skills=['slice.monitor', 'slice.apply', 'slice.verify', 'slice.associate-ue'],
        measurements=['Slice counts', 'reserved PRBs', 'UE associations', 'slice scheduler'],
        use_cases=['Slice rollout', 'capacity partitioning', 'policy validation'],
        peers=['orchestrator', 'kpm', 'mac', 'rc'],
        providers=['ollama', 'openai'],
        actions=[
            suite_action('monitor', 'Monitor Slice State', 'Run the slice suite in monitor mode.', python_bin, base_dir, 'xapp_slice_suite.py', '--profile', 'monitor', '--duration-s', '30', '--verbose'),
            suite_action('apply-static', 'Apply Static Slice', 'Apply the STATIC profile and monitor it.', python_bin, base_dir, 'xapp_slice_suite.py', '--profile', 'static', '--duration-s', '30', '--verbose'),
        ],
        notes=['Backed by xapp_slice_suite.py profiles monitor/static/nvs-rate/nvs-cap/edf/all.'],
    )
