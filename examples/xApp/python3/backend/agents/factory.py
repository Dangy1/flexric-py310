from __future__ import annotations

from pathlib import Path

from backend.common.models import AgentAction


def suite_action(action_id: str, label: str, description: str, python_bin: str, base_dir: Path, *command: str) -> AgentAction:
    resolved = []
    for item in command:
        if item.endswith('.py') and not item.startswith('/'):
            resolved.append(str(base_dir / item))
        else:
            resolved.append(item)
    return AgentAction(
        id=action_id,
        label=label,
        description=description,
        kind='suite',
        command=[python_bin, '-u', *resolved],
    )
