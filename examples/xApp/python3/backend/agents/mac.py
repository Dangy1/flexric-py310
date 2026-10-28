from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    # Backed by xapp_l2_monitor.py --sm mac (FlexRIC MAC_STATS_V0, RAN function 142): subscribes, prints
    # one "MAC ind tstamp=" line per (rate-limited) indication, unsubscribes and exits. Sends no control.
    observe = suite_action(
        'observe-mac', 'Observe MAC Scheduler Stats',
        'Subscribe to the FlexRIC MAC stats service model for a short window and print per-UE scheduler '
        'statistics (scheduled RBs, wideband CQI, MCS, BLER, PUSCH SNR); read-only.',
        python_bin, base_dir, 'xapp_l2_monitor.py', '--sm', 'mac', '--duration-s', '30',
    )
    observe.control_scopes = [ControlScope(target='ue', mode='read', resource='mac_subscription')]
    return AgentCard(
        id='mac',
        name='MAC Agent',
        role='MAC scheduler monitor xApp',
        service_model='MAC',
        description=('Reads per-UE MAC scheduler statistics from the FlexRIC MAC service model: scheduled DL/UL resource '
                     'blocks, wideband CQI, MCS, BLER, HARQ, PUSCH/PUCCH SNR, buffer status and power headroom. Read-only. '
                     'Use when a workflow needs UE-level scheduling or link-adaptation evidence (radio link quality, MCS/BLER, '
                     'who gets the resource blocks) before or after a decision. Do not use for cell-level KPIs such as PRB '
                     'utilisation or throughput aggregates (KPM) or to change any RAN state.'),
        page_path='/agents/mac',
        a2a_card_path='/.well-known/agents/mac.json',
        status='ready',
        activity='Idle; ready to subscribe to MAC indications.',
        skills=['mac.observe', 'mac.link_quality', 'mac.scheduler_share'],
        measurements=['MAC.SchedRbDl', 'MAC.SchedRbUl', 'MAC.WbCqi', 'MAC.McsDl', 'MAC.BlerDl', 'MAC.PuschSnr'],
        use_cases=['Link adaptation review', 'per-UE scheduler share', 'radio link quality check'],
        peers=['orchestrator', 'kpm', 'slice', 'rlc'],
        providers=['ollama', 'openai'],
        actions=[observe],
        notes=['Backed by xapp_l2_monitor.py --sm mac (MAC_STATS_V0, RAN function 142).',
               'Ack marker: "MAC ind tstamp="; no-data line: "MAC monitor received no indications".'],
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-MAC (FlexRIC custom)'],
        consumes=[],
        produces=['MAC.ue_sched_stats', 'MAC.WbCqi', 'MAC.BlerDl'],
        control_scopes=[ControlScope(target='ue', mode='read', resource='mac_subscription')],
        timescale_s=1.0,
        capabilities=['mac_scheduler_monitoring', 'link_quality_monitoring'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
        workflow_role='observe',
    )
