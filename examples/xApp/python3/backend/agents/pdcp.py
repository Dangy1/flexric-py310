from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    # Backed by xapp_l2_monitor.py --sm pdcp (FlexRIC PDCP_STATS_V0, RAN function 144). Read-only.
    observe = suite_action(
        'observe-pdcp', 'Observe PDCP Bearer Stats',
        'Subscribe to the FlexRIC PDCP stats service model for a short window and print per-bearer TX/RX volume, '
        'discarded and out-of-order PDUs; read-only.',
        python_bin, base_dir, 'xapp_l2_monitor.py', '--sm', 'pdcp', '--duration-s', '30',
    )
    observe.control_scopes = [ControlScope(target='ue', mode='read', resource='pdcp_subscription')]
    return AgentCard(
        id='pdcp',
        name='PDCP Agent',
        role='PDCP bearer monitor xApp',
        service_model='PDCP',
        description=('Reads per-radio-bearer PDCP statistics from the FlexRIC PDCP service model: TX/RX PDU and SDU volume, '
                     'sequence numbers, discarded and out-of-order PDUs. Read-only. Use when a workflow needs bearer-level '
                     'traffic volume or packet-loss/reordering evidence at PDCP before or after a decision. Do not use for '
                     'cell-level KPIs (KPM) or to change any RAN state.'),
        page_path='/agents/pdcp',
        a2a_card_path='/.well-known/agents/pdcp.json',
        status='ready',
        activity='Idle; ready to subscribe to PDCP indications.',
        skills=['pdcp.observe', 'pdcp.volume', 'pdcp.loss'],
        measurements=['PDCP.TxPduBytes', 'PDCP.RxPduBytes', 'PDCP.RxPduDiscarded', 'PDCP.RxPduOutOfOrder'],
        use_cases=['Bearer volume accounting', 'PDCP loss and reordering check'],
        peers=['orchestrator', 'rlc', 'gtp'],
        providers=['ollama', 'openai'],
        actions=[observe],
        notes=['Backed by xapp_l2_monitor.py --sm pdcp (PDCP_STATS_V0, RAN function 144).',
               'Ack marker: "PDCP ind tstamp="; no-data line: "PDCP monitor received no indications".'],
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-PDCP (FlexRIC custom)'],
        consumes=[],
        produces=['PDCP.bearer_stats'],
        control_scopes=[ControlScope(target='ue', mode='read', resource='pdcp_subscription')],
        timescale_s=1.0,
        capabilities=['pdcp_volume_monitoring', 'pdcp_loss_monitoring'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
        workflow_role='observe',
    )
