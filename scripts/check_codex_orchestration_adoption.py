#!/usr/bin/env python3
"""Validate Codex parallel orchestration adoption configuration."""

from __future__ import annotations

import json
from pathlib import Path
import sys

CONFIG_PATH = Path('.codex/orchestration/codex-parallel-adoption.json')
REQUIRED_IDS = {
    'review-comments',
    'multi-terminal',
    'remote-devbox-ssh',
    'rich-preview',
    'summary-pane-tracking',
    'thread-reuse',
    'scheduled-automations',
    'persistent-memory',
}
REQUIRED_FIELDS = {
    'id',
    'name',
    'status',
    'execution_mode',
    'entrypoint',
    'verification_command',
    'notes',
}


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f'Missing configuration: {CONFIG_PATH}')
        return 1

    with CONFIG_PATH.open('r', encoding='utf-8') as handle:
        data = json.load(handle)

    workstreams = data.get('workstreams', [])
    ids = {item.get('id') for item in workstreams}

    missing = REQUIRED_IDS - ids
    extra = ids - REQUIRED_IDS

    if missing:
        print(f'Missing required workstreams: {sorted(missing)}')
        return 1

    if extra:
        print(f'Unexpected workstreams: {sorted(extra)}')
        return 1

    for item in workstreams:
        missing_fields = REQUIRED_FIELDS - set(item)
        if missing_fields:
            print(f"Workstream '{item.get('id', 'unknown')}' missing fields: {sorted(missing_fields)}")
            return 1

        if item['status'] != 'active':
            print(f"Workstream '{item['id']}' must be active")
            return 1

        if item['execution_mode'] != 'parallel':
            print(f"Workstream '{item['id']}' must use parallel execution_mode")
            return 1

    print('Codex orchestration adoption config is valid.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
