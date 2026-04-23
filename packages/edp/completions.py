#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.completions - Click shell_complete 回调

为 CLI 选项提供动态补全。
"""

from pathlib import Path
from typing import Optional

import yaml

from dirkit import ProjectFinder


def _get_edp_center(ctx) -> Optional[Path]:
    return ctx.obj.get('edp_center') if ctx.obj else None


def _get_initialize_path(ctx) -> Optional[Path]:
    center = _get_edp_center(ctx)
    if not center:
        return None
    p = center / 'flow' / 'initialize'
    return p if p.exists() else None


def _complete_projects(ctx, param, incomplete):
    """补全可用项目名"""
    init_path = _get_initialize_path(ctx)
    if not init_path:
        return []
    finder = ProjectFinder(init_path)
    projects = [m['project_name'] for m in finder.list_projects()]
    return [p for p in projects if p.startswith(incomplete)]


def _complete_nodes(ctx, param, incomplete):
    """补全可用 node 名"""
    init_path = _get_initialize_path(ctx)
    if not init_path:
        return []
    nodes = set()
    if init_path.exists():
        for foundry_dir in init_path.iterdir():
            if not foundry_dir.is_dir() or foundry_dir.name.startswith('.'):
                continue
            for node_dir in foundry_dir.iterdir():
                if node_dir.is_dir() and not node_dir.name.startswith('.'):
                    nodes.add(node_dir.name)
    return sorted(n for n in nodes if n.startswith(incomplete))


def _complete_steps(ctx, param, incomplete):
    """补全 step 名"""
    init_path = _get_initialize_path(ctx)
    if not init_path:
        return []
    steps = set()
    for f in init_path.rglob('step_config.yaml'):
        data = yaml.safe_load(f.read_text(encoding='utf-8'))
        if data and 'steps' in data:
            for entry in data['steps']:
                name = str(entry).rsplit('.', 1)[-1] if '.' in str(entry) else str(entry)
                steps.add(name)
    return sorted(s for s in steps if s.startswith(incomplete))
