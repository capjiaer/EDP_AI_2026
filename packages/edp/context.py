#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.context - CLI 共享上下文解析

薄包装层：调 dirkit → 转 ClickException。
"""

from pathlib import Path
from typing import Dict, List, Optional

import click
import yaml

from dirkit import ProjectFinder


def _find_graph_configs(flow_base: Path, flow_overlay: Optional[Path]) -> List[Path]:
    """查找所有 graph_config*.yaml 文件（overlay 覆盖同名 base，互斥）"""
    files = {}
    if flow_base.exists():
        for f in sorted(flow_base.glob('graph_config*.yaml')):
            files[f.name] = f
    if flow_overlay and flow_overlay.exists():
        for f in sorted(flow_overlay.glob('graph_config*.yaml')):
            files[f.name] = f
    return sorted(files.values())


def _load_step_config(flow_base: Path, flow_overlay: Optional[Path]) -> Dict[str, str]:
    """加载 step_config.yaml 为 {step: tool} 字典"""
    config_path = None
    if flow_overlay and flow_overlay.exists():
        p = flow_overlay / 'step_config.yaml'
        if p.exists():
            config_path = p
    if not config_path:
        p = flow_base / 'step_config.yaml'
        if p.exists():
            config_path = p
    if not config_path:
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or 'steps' not in data:
        return {}

    tool_selection = {}
    for entry in data['steps']:
        if '.' in str(entry):
            tool, step = str(entry).rsplit('.', 1)
            tool_selection[step] = tool
        else:
            tool_selection[str(entry)] = str(entry)
    return tool_selection


def _resolve_context(ctx) -> dict:
    """自动检测项目上下文

    Returns:
        {
            branch_path, flow_base_path, flow_overlay_path,
            graph_configs, tool_selection, project_info,
        }
    """
    edp_center = ctx.obj['edp_center']
    cwd = Path.cwd().resolve()

    # 1. dirkit 检测项目上下文（含 user/branch）
    init_path = edp_center / 'flow' / 'initialize'
    finder = ProjectFinder(init_path)
    info = finder.resolve_context(cwd)

    if not info:
        raise click.ClickException(
            "Cannot detect project context from current directory.\n"
            f"  Current: {cwd}\n"
            "  Make sure you're in a branch directory under WORK_PATH.\n"
            "  Or set EDP_CENTER / --edp-center to the correct path."
        )

    # branch_path 只在 block/user/branch 三级路径下才存在
    if 'branch_path' not in info:
        hint = ""
        if 'block_name' in info:
            hint = f"\n  Detected block: '{info['block_name']}'\n  Please navigate to: block/user/branch"
        raise click.ClickException(
            f"Not in a valid branch directory.\n"
            f"  Current: {cwd}\n"
            f"  Expected path structure: work_path/project/version/block/user/branch\n"
            f"{hint}"
        )

    # 2. Flow 路径
    flow_base = init_path / info['foundry'] / info['node'] / 'common_prj'
    flow_overlay = init_path / info['foundry'] / info['node'] / info['project_name']

    # 3. 查找配置文件
    graph_configs = _find_graph_configs(flow_base, flow_overlay)
    if not graph_configs:
        raise click.ClickException(
            f"No graph_config*.yaml found in:\n"
            f"  {flow_base}\n"
            f"  {flow_overlay}"
        )

    tool_selection = _load_step_config(flow_base, flow_overlay)
    if not tool_selection:
        raise click.ClickException(
            f"No step_config.yaml found or empty in:\n"
            f"  {flow_base}\n"
            f"  {flow_overlay}"
        )

    return {
        'branch_path': info['branch_path'],
        'flow_base_path': flow_base,
        'flow_overlay_path': flow_overlay,
        'graph_configs': graph_configs,
        'tool_selection': tool_selection,
        'project_info': info,
    }


def _pick_graph_config(graph_configs: List[Path], branch_path: Path,
                       force_select: bool = False) -> Path:
    """选择 graph config。优先读取已保存的选择，否则提示用户选并保存。"""
    # 只有一张图直接返回
    if len(graph_configs) == 1:
        selected = graph_configs[0]
        _save_graph_config_choice(branch_path, selected)
        return selected

    # 尝试读取已保存的选择
    if not force_select:
        saved = _load_graph_config_choice(branch_path, graph_configs)
        if saved:
            return saved

    # 提示用户选择
    click.echo("Multiple graph configs found, please select one:")
    for i, f in enumerate(graph_configs, 1):
        click.echo(f"  [{i}] {f.name}  ({f.resolve()})")

    while True:
        choice = click.prompt("Enter number", type=int)
        if 1 <= choice <= len(graph_configs):
            selected = graph_configs[choice - 1]
            _save_graph_config_choice(branch_path, selected)
            return selected
        click.echo(f"Invalid choice. Please enter 1-{len(graph_configs)}.")


_GRAPH_CONFIG_FILE = '.graph_config'


def _load_graph_config_choice(branch_path: Path, graph_configs: List[Path]) -> Optional[Path]:
    """读取已保存的 graph config 选择"""
    choice_file = branch_path / _GRAPH_CONFIG_FILE
    if not choice_file.exists():
        return None
    saved_name = choice_file.read_text(encoding='utf-8').strip()
    for f in graph_configs:
        if f.name == saved_name:
            return f
    return None


def _save_graph_config_choice(branch_path: Path, graph_config: Path) -> None:
    """保存 graph config 选择"""
    branch_path.mkdir(parents=True, exist_ok=True)
    choice_file = branch_path / _GRAPH_CONFIG_FILE
    choice_file.write_text(graph_config.name, encoding='utf-8')
