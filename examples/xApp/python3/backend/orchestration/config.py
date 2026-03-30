WORKFLOW_TEMPLATES = {
    'observe-diagnose-optimize': {
        'label': 'Observe, Diagnose, Optimize',
        'steps': ['orchestrator', 'kpm', 'mac', 'slice', 'tc', 'rc'],
        'description': 'Collect KPIs, correlate MAC/slice pressure, enforce policy, then validate with RC.',
    },
    'slice-assurance': {
        'label': 'Slice Assurance Loop',
        'steps': ['orchestrator', 'slice', 'kpm', 'rc'],
        'description': 'Apply or monitor slice policy, measure impact, then review control readiness.',
    },
    'transport-qos': {
        'label': 'Transport QoS Chain',
        'steps': ['orchestrator', 'tc', 'rlc', 'pdcp', 'gtp'],
        'description': 'Use TC actions and downstream bearer/tunnel observers for transport-aware feedback.',
    },
}

WORKFLOW_ACTIONS = {
    'observe-diagnose-optimize': {
        'kpm': 'observe-rru',
        'slice': 'monitor',
        'tc': 'apply-codel',
        'rc': 'rc-scaffold',
    },
    'slice-assurance': {
        'slice': 'monitor',
        'kpm': 'observe-rru',
        'rc': 'rc-scaffold',
    },
    'transport-qos': {
        'tc': 'apply-codel',
    },
}

WORKFLOW_RESOURCE_REQUIREMENTS = {
    'observe-diagnose-optimize': [
        {'id': 'kpm_subscription', 'mode': 'shared', 'scope': 'read'},
        {'id': 'slice_control', 'mode': 'exclusive', 'scope': 'write'},
        {'id': 'tc_control', 'mode': 'exclusive', 'scope': 'write'},
        {'id': 'rc_control', 'mode': 'exclusive', 'scope': 'write'},
    ],
    'slice-assurance': [
        {'id': 'kpm_subscription', 'mode': 'shared', 'scope': 'read'},
        {'id': 'slice_control', 'mode': 'exclusive', 'scope': 'write'},
        {'id': 'rc_control', 'mode': 'exclusive', 'scope': 'write'},
    ],
    'transport-qos': [
        {'id': 'tc_control', 'mode': 'exclusive', 'scope': 'write'},
    ],
}

GRAPH_STAGE_LABELS = {
    'observe': 'Observe',
    'diagnose': 'Diagnose',
    'approve': 'Approve',
    'act': 'Act',
    'verify': 'Verify',
    'summarize': 'Summarize',
}

GRAPH_STAGE_AGENTS = {
    'observe': 'orchestrator',
    'diagnose': 'orchestrator',
    'approve': 'rc',
    'act': 'orchestrator',
    'verify': 'orchestrator',
    'summarize': 'orchestrator',
}
