from __future__ import annotations

from pathlib import Path

from backend.agents.factory import suite_action
from backend.common.models import AgentCard, ControlScope


def build_agent(python_bin: str, base_dir: Path) -> AgentCard:
    # Backed by xapp_rc_ctrl.py (real E2SM-RC over E2; messages built by the C++ SWIG helpers
    # control_rc_sm_qos_flow_map / report_rc_sm_auto from the node-advertised RC RAN function).
    # Per-action scope: `rc-control` sends an E2 RIC CONTROL (write, UE-level radio bearer
    # configuration); `rc-report` only subscribes to RC REPORT style 4 (read).
    rc_control = suite_action(
        'rc-control', 'Send RC Control',
        'Send one E2SM-RC CONTROL (style 1 Radio Bearer Control, action 2 QoS flow mapping configuration: '
        'DRB 5, QFI 10, DL, UE amf_ue_ngap_id 1) and wait for the E2 CONTROL-ACK.',
        python_bin, base_dir, 'xapp_rc_ctrl.py', '--profile', 'control', '--duration-s', '10',
    )
    rc_control.control_scopes = [ControlScope(target='ue', mode='write', resource='rc_control')]
    rc_report = suite_action(
        'rc-report', 'Subscribe RC Report',
        'Subscribe to E2SM-RC REPORT style 4 (UE Information, RRC state changes) and print the RC indications '
        '(read-only, sends no control).',
        python_bin, base_dir, 'xapp_rc_ctrl.py', '--profile', 'report', '--duration-s', '10',
    )
    rc_report.control_scopes = [ControlScope(target='ue', mode='read', resource='rc_control')]
    return AgentCard(
        id='rc',
        name='RC Agent',
        role='E2SM-RC radio bearer control xApp',
        service_model='RC',
        description=('Sends O-RAN E2SM-RC CONTROL messages (Radio Bearer Control: QoS flow to DRB mapping for a UE) '
                     'and confirms that the E2 node acknowledged them (E2 CONTROL-ACK); can also subscribe to E2SM-RC '
                     'REPORT style 4 to read UE information (RRC state) changes. Use as the final actuation/confirmation '
                     'step of a chain that must push a per-UE radio bearer configuration through E2SM-RC. Do not use for '
                     'slice PRB reservation (SLICE), queue management (TC) or KPI collection (KPM). On the FlexRIC '
                     'emulator the control is acknowledged but has no effect on later KPIs.'),
        page_path='/agents/rc',
        a2a_card_path='/.well-known/agents/rc.json',
        status='ready',
        activity='Idle; ready to send an E2SM-RC control or subscribe to RC reports.',
        skills=['rc.control.radio_bearer', 'rc.control.ack', 'rc.report.ue_info'],
        measurements=['E2 CONTROL-ACK and its latency', 'RC indications (UE ID, RRC state)'],
        use_cases=['Per-UE QoS flow to DRB mapping', 'confirming that an E2 node accepts RC control', 'UE RRC-state reporting'],
        peers=['orchestrator', 'kpm', 'slice', 'tc'],
        providers=['ollama', 'openai'],
        actions=[rc_control, rc_report],
        notes=[
            'Backed by xapp_rc_ctrl.py --profile control|report (E2SM-RC v1.03; helpers in src/xApp/swig/swig_wrapper.cpp).',
            'Ack markers: "RC CONTROL-ACK received" (control), "RC indication received" (report); '
            'failure markers: "RC CONTROL-FAILED", "RC REPORT-FAILED".',
            'The control is only sent when the E2 node advertises RC control style 1 / action 2; the report only when it '
            'advertises report style 4 with event trigger format 4.',
        ],
        app_type='xapp',
        ric='near-rt',
        interfaces=['E2SM-RC v1.03'],
        consumes=[],
        produces=['rc.control_ack', 'rc.ue_info'],
        control_scopes=[ControlScope(target='ue', mode='write', resource='rc_control')],
        timescale_s=1.0,
        # `control_validation`: the control step reports whether the E2 node acknowledged the RC control
        # (CONTROL-ACK), which is what the end-of-chain "validate" role in the labels relies on.
        capabilities=['radio_bearer_control', 'qos_flow_mapping', 'control_validation', 'ue_info_report'],
        conflicts_with=[],
        mcp_endpoint='http://127.0.0.1:8000/mcp',
    )
