#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate completion cache file for bash tab completion.
Runs once during `source edp.sh`, outputs a simple key=value file.

Cache format (one per line):
    PROJECTS=project1 project2 ...
    NODES=node1 node2 ...
    STEPS=step1 step2 ...
"""

import os
import sys
from pathlib import Path

def main():
    edp_root = os.environ.get('EDP_ROOT', '')
    if not edp_root:
        return

    resources = Path(edp_root) / 'resources'
    init_dir = resources / 'flow' / 'initialize'
    cache_file = Path(edp_root) / '.edp_completion_cache'

    lines = []

    # Collect projects and nodes
    projects = set()
    nodes = set()
    if init_dir.exists():
        for foundry_dir in init_dir.iterdir():
            if not foundry_dir.is_dir() or foundry_dir.name.startswith('.'):
                continue
            for node_dir in foundry_dir.iterdir():
                if not node_dir.is_dir() or node_dir.name.startswith('.'):
                    continue
                nodes.add(node_dir.name)
                for proj_dir in node_dir.iterdir():
                    if (proj_dir.is_dir()
                            and not proj_dir.name.startswith('.')
                            and proj_dir.name != 'common_prj'):
                        projects.add(proj_dir.name)

    lines.append(f"PROJECTS={' '.join(sorted(projects))}")
    lines.append(f"NODES={' '.join(sorted(nodes))}")

    # Collect steps from step_config.yaml
    steps = set()
    try:
        import yaml
        for f in init_dir.rglob('step_config.yaml'):
            data = yaml.safe_load(f.read_text(encoding='utf-8'))
            if data and 'steps' in data:
                for entry in data['steps']:
                    name = str(entry).rsplit('.', 1)[-1] if '.' in str(entry) else str(entry)
                    steps.add(name)
    except Exception:
        pass

    lines.append(f"STEPS={' '.join(sorted(steps))}")

    cache_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
