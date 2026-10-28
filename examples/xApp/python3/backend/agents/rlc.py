from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    # Backed by xapp_l2_monitor.py --sm rlc (FlexRIC RLC_STATS_V0, RAN function 143). Read-only.
    observe = suite_action(
        'observe-rlc', 'Observe RLC Bearer Stats',
        'Subscribe to the FlexRIC RLC stats service model for a short window and print per-bearer buffer '
        'occupancy, retransmissions and SDU waiting time; read-only.',
        python_bin, base_dir, 'xapp_l2_monitor.py', '--sm', 'rlc', '--duration-s', '30',
    )
    observe.control_scopes = [ControlScope(target='ue', mode='read', resource='rlc_subscription')]
    return AgentCard(
        id='rlc',
        name='RLC Agent',
        role='RLC bearer monitor xApp',
        service_model='RLC',
        description=('Reads per-radio-bearer RLC statistics from the FlexRIC RLC service model: TX/RX buffer occupancy, '
                     'PDU retransmissions, dropped PDUs and SDU waiting time. Read-only. Use when a workflow needs '
                     'bearer-level queue or retransmission evidence (buffer build-up, ARQ retransmissions) before or after '
                     'a decision. Do not use for cell-level KPIs (KPM), for transport queue policies (TC) or to change any '
                     'RAN state.'),
        page_path='/agents/rlc',
        a2a_card_path='/.well-known/agents/rlc.json',
        status='ready',
        activity='Idle; ready to subscribe to RLC indications.',
        skills=['rlc.observe', 'rlc.buffer', 'rlc.retx'],
        measurements=['RLC.TxBufOccBytes', 'RLC.TxPduRetxPkts', 'RLC.TxSduWaitUs'],
        use_cases=['Bearer buffer build-up check', 'retransmission review', 'post-control bearer check'],
        peers=['orchestrator', 'tc', 'mac', 'pdcp'],
        providers=['ollama', 'openai'],
        actions=[observe],
        notes=['Backed by xapp_l2_monitor.py --sm rlc (RLC_STATS_V0, RAN function 143).',
               'Ack marker: "RLC ind tstamp="; no-data line: "RLC monitor received no indications".'],
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-RLC (FlexRIC custom)'],
        consumes=[],
        produces=['RLC.bearer_stats', 'RLC.queue_stats'],
        control_scopes=[ControlScope(target='ue', mode='read', resource='rlc_subscription')],
        timescale_s=1.0,
        capabilities=['rlc_buffer_monitoring', 'retransmission_monitoring'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
        workflow_role='observe',
    )
