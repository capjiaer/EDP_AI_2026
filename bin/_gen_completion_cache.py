#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate completion cache files for both bash and tcsh/tab completion.
Runs once during `source edp.sh` or `source edp.csh`.

Generates two cache files:
1. .edp_completion_cache     - bash format (key=value)
2. .edp_completion_cache.csh  - tcsh format (set variables)
"""

import os
import sys
from pathlib import Path

def collect_data(edp_root):
    """Collect projects, nodes, and steps from the file system."""
    resources = Path(edp_root) / 'resources'
    init_dir = resources / 'flow' / 'initialize'

    projects = set()
    nodes = set()
    steps = set()

    # Collect projects and nodes from directory structure
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

    # Collect steps from step_config.yaml files
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

    return sorted(projects), sorted(nodes), sorted(steps)

def generate_bash_cache(projects, nodes, steps, cache_file):
    """Generate bash format cache (key=value)."""
    lines = [
        f"PROJECTS={' '.join(projects)}",
        f"NODES={' '.join(nodes)}",
        f"STEPS={' '.join(steps)}"
    ]
    cache_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def generate_tcsh_cache(projects, nodes, steps, cache_file):
    """Generate tcsh format cache (set variables)."""
    lines = [
        "# tcsh completion cache - generated automatically",
        "# Source this file in tcsh completion scripts",
        "",
        f"set _edp_projects = ({' '.join(projects)})",
        f"set _edp_nodes = ({' '.join(nodes)})",
        f"set _edp_steps = ({' '.join(steps)})",
    ]
    cache_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def main():
    edp_root = os.environ.get('EDP_ROOT', '')
    if not edp_root:
        return

    projects, nodes, steps = collect_data(edp_root)

    # Generate bash cache
    bash_cache = Path(edp_root) / '.edp_completion_cache'
    generate_bash_cache(projects, nodes, steps, bash_cache)

    # Generate tcsh cache
    tcsh_cache = Path(edp_root) / '.edp_completion_cache.csh'
    generate_tcsh_cache(projects, nodes, steps, tcsh_cache)

    print(f"Generated completion caches for bash and tcsh", file=sys.stderr)


if __name__ == '__main__':
    main()
