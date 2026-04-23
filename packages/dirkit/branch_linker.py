#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit.branch_linker - 分支链接、步骤解析、来源记录

从源分支复制或链接步骤输出，并记录分支来源。
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

import yaml

from .dirkit import DirKit


def parse_branch_step(from_branch_step: str, current_user: str) -> Tuple[str, str, str]:
    """
    解析 from_branch_step 参数

    支持的格式：
    1. 'branch.tool.step'      -> 2个点号，当前用户
       例如: 'branch1.pnr_innovus.init'
    2. 'user.branch.tool.step' -> 3+个点号，指定用户
       例如: 'zhangsan.branch1.pnr_innovus.init'

    Returns:
        (source_user, source_branch, step_name) 元组
    """
    if not from_branch_step or '.' not in from_branch_step:
        raise ValueError(
            f"from_branch_step 格式不正确: {from_branch_step}\n"
            f"格式: 'branch.step' 或 'user.branch.step'"
        )

    parts = from_branch_step.split('.')
    dot_count = len(parts) - 1

    if dot_count == 1:
        raise ValueError(
            f"from_branch_step 格式不正确: {from_branch_step}\n"
            f"step_name 必须包含 tool.step 格式（如 pnr_innovus.init）"
        )

    if dot_count == 2:
        source_user = current_user
        source_branch = parts[0]
        step_name = parts[1] + '.' + parts[2]
    else:
        source_user = parts[0]
        source_branch = parts[1]
        step_name = '.'.join(parts[2:])

    return source_user, source_branch, step_name


def save_branch_source(branch_path: Path, from_branch_step: str,
                       copy_info: Dict, link_mode: bool) -> None:
    """保存分支来源信息到 .branch_source.yaml"""
    info = {
        'created_at': datetime.now().isoformat(),
        'source': {
            'from_branch_step': from_branch_step,
            'source_user': copy_info.get('source_user'),
            'source_branch': copy_info.get('source_branch'),
            'source_step': copy_info.get('source_step'),
            'step_name': copy_info.get('step_name'),
        },
        'target': {
            'branch_path': str(branch_path),
            'target_step': copy_info.get('target_step'),
        },
        'mode': 'link' if link_mode else 'copy',
    }

    source_file = branch_path / '.branch_source.yaml'
    with open(source_file, 'w', encoding='utf-8') as f:
        yaml.dump(info, f, allow_unicode=True,
                  default_flow_style=False, sort_keys=False)


def load_branch_source(branch_path: Path) -> Optional[Dict]:
    """获取分支来源信息，不存在则返回 None"""
    source_file = branch_path / '.branch_source.yaml'
    if not source_file.exists():
        return None
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


class BranchLinker:
    """分支链接器"""

    def copy_step_from_branch(self, work_path: Path, project_name: str,
                              project_node: str, block_name: str,
                              from_branch_step: str, target_branch_path: Path,
                              current_user: str, link_mode: bool = True) -> Dict[str, str]:
        """
        从源分支复制或链接指定步骤的输出到目标分支

        Args:
            work_path: WORK_PATH 根目录
            project_name: 项目名称
            project_node: 项目节点名称
            block_name: 块名称
            from_branch_step: 源分支步骤（如 'branch1.pnr_innovus.init'）
            target_branch_path: 目标分支路径
            current_user: 当前用户名
            link_mode: True=符号链接，False=复制

        Returns:
            操作详细信息
        """
        source_user, source_branch, step_name = parse_branch_step(
            from_branch_step, current_user
        )

        source_branch_path = (
            work_path / project_name / project_node / block_name /
            source_user / source_branch
        )

        if not source_branch_path.exists():
            raise FileNotFoundError(f"源分支不存在: {source_branch_path}")

        source_step_path = source_branch_path / "runs" / step_name
        if not source_step_path.exists():
            raise FileNotFoundError(f"源步骤输出不存在: {source_step_path}")

        target_step_path = target_branch_path / "runs" / step_name
        target_step_path.parent.mkdir(parents=True, exist_ok=True)

        dirkit = DirKit()
        if link_mode:
            if source_step_path.is_dir():
                dirkit.link_dir(source_step_path, target_step_path, overwrite=True)
            else:
                dirkit.link_file(source_step_path, target_step_path, overwrite=True)
        else:
            if source_step_path.is_dir():
                dirkit.copy_dir(source_step_path, target_step_path, overwrite=True)
            else:
                dirkit.copy_file(source_step_path, target_step_path, overwrite=True)

        return {
            'source_user': source_user,
            'source_branch': source_branch,
            'source_step': str(source_step_path),
            'target_step': str(target_step_path),
            'step_name': step_name,
        }

    def link_other_dirs(self, source_branch_path: Path,
                        target_branch_path: Path,
                        link_mode: bool = True) -> Dict[str, Dict]:
        """
        从源分支链接/复制其他目录（cmds, dbs, flow, hooks, logs, rpts）

        Args:
            source_branch_path: 源分支路径
            target_branch_path: 目标分支路径
            link_mode: True=符号链接，False=复制

        Returns:
            各目录的链接/复制结果
        """
        dirkit = DirKit()
        result = {}

        for dir_name in ['cmds', 'dbs', 'flow', 'hooks', 'logs', 'rpts']:
            src = source_branch_path / dir_name
            dst = target_branch_path / dir_name

            if src.exists() and src.is_dir():
                try:
                    if link_mode:
                        dirkit.link_dir(src, dst, overwrite=True)
                    else:
                        dirkit.copy_dir(src, dst, overwrite=True)
                    result[dir_name] = {'type': 'link' if link_mode else 'copy'}
                except Exception as e:
                    result[dir_name] = {'type': 'error', 'error': str(e)}
            else:
                result[dir_name] = {'type': 'skipped'}

        return result
