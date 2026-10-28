from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    # Backed by xapp_l2_monitor.py --sm gtp (FlexRIC GTP_STATS_V0, RAN function 148). Read-only.
    observe = suite_action(
        'observe-gtp', 'Observe GTP-U Tunnels',
        'Subscribe to the FlexRIC GTP stats service model for a short window and print the NG-U (N3) tunnels per UE '
        '(gNB and UPF TEIDs, QoS flow id); read-only.',
        python_bin, base_dir, 'xapp_l2_monitor.py', '--sm', 'gtp', '--duration-s', '30',
    )
    observe.control_scopes = [ControlScope(target='transport', mode='read', resource='gtp_subscription')]
    return AgentCard(
        id='gtp',
        name='GTP Agent',
        role='GTP-U tunnel monitor xApp',
        service_model='GTP',
        description=('Reads the NG-U (N3) GTP-U tunnel table from the FlexRIC GTP service model: per UE the gNB and UPF '
                     'tunnel endpoint ids (TEIDs) and the QoS flow id carried. Read-only. Use when a workflow needs '
                     'user-plane tunnel evidence (which UEs have an active N3 tunnel, QoS-flow-to-tunnel mapping) before or '
                     'after a decision. Do not use for radio KPIs (KPM), for queue policies (TC) or to change any RAN state.'),
        page_path='/agents/gtp',
        a2a_card_path='/.well-known/agents/gtp.json',
        status='ready',
        activity='Idle; ready to subscribe to GTP indications.',
        skills=['gtp.observe', 'gtp.tunnel_inventory', 'gtp.qfi_mapping'],
        measurements=['GTP.NguTunnels', 'GTP.Qfi', 'GTP.TeidGnb', 'GTP.TeidUpf'],
        use_cases=['N3 tunnel inventory', 'QoS flow to tunnel mapping check', 'end-to-end user-plane diagnosis'],
        peers=['orchestrator', 'tc', 'pdcp'],
        providers=['ollama', 'openai'],
        actions=[observe],
        notes=['Backed by xapp_l2_monitor.py --sm gtp (GTP_STATS_V0, RAN function 148).',
               'Ack marker: "GTP ind tstamp="; no-data line: "GTP monitor received no indications".'],
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-GTP (FlexRIC custom)'],
        consumes=[],
        produces=['GTP.ngu_tunnel_stats'],
        control_scopes=[ControlScope(target='transport', mode='read', resource='gtp_subscription')],
        timescale_s=1.0,
        capabilities=['gtp_tunnel_monitoring', 'n3_tunnel_inventory'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
        workflow_role='observe',
    )
