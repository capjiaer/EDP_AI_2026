#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit.project_finder - 项目查找和路径检测

在 initialize/{foundry}/{node}/ 下查找项目，或从当前路径推断项目信息。
"""

from pathlib import Path
from typing import List, Dict, Optional

import yaml


class ProjectFinder:
    """项目查找器"""

    def __init__(self, initialize_path: Path):
        """
        初始化 ProjectFinder

        Args:
            initialize_path: initialize 目录路径（如 edp_center/flow/initialize/）
        """
        self.initialize_path = Path(initialize_path)

    def find_project(self, project_name: str) -> List[Dict[str, str]]:
        """
        根据项目名称查找所有匹配的 foundry/node 组合

        Returns:
            例如: [{'foundry': 'SAMSUNG', 'node': 'S8'}, ...]
        """
        matches = []
        if not self.initialize_path.exists():
            return matches

        for foundry_dir in self.initialize_path.iterdir():
            if not foundry_dir.is_dir() or foundry_dir.name.startswith('.'):
                continue
            for node_dir in foundry_dir.iterdir():
                if not node_dir.is_dir() or node_dir.name.startswith('.'):
                    continue
                if (node_dir / project_name).is_dir():
                    matches.append({
                        'foundry': foundry_dir.name,
                        'node': node_dir.name,
                        'project': project_name
                    })

        return matches

    def get_project_info(self, project_name: str,
                         foundry: Optional[str] = None,
                         node: Optional[str] = None) -> Dict[str, str]:
        """
        获取项目信息（foundry 和 node）

        Raises:
            ValueError: 如果找不到项目或找到多个匹配
        """
        matches = self.find_project(project_name)
        if foundry:
            matches = [m for m in matches if m['foundry'] == foundry]
        if node:
            matches = [m for m in matches if m['node'] == node]

        if not matches:
            available = [p['project'] for p in self.list_projects()]
            raise ValueError(
                f"找不到项目 '{project_name}'\n可用项目: {available}"
            )
        if len(matches) == 1:
            return matches[0]

        match_info = "\n".join(f"  - {m['foundry']}/{m['node']}" for m in matches)
        raise ValueError(
            f"找到多个匹配的项目 '{project_name}'，请指定 foundry 和/或 node:\n{match_info}"
        )

    def list_projects(self, foundry: Optional[str] = None,
                      node: Optional[str] = None) -> List[Dict[str, str]]:
        """列出所有可用的项目（排除 common）"""
        projects = []
        if not self.initialize_path.exists():
            return projects

        for foundry_dir in self.initialize_path.iterdir():
            if not foundry_dir.is_dir() or foundry_dir.name.startswith('.'):
                continue
            if foundry and foundry_dir.name != foundry:
                continue
            for node_dir in foundry_dir.iterdir():
                if not node_dir.is_dir() or node_dir.name.startswith('.'):
                    continue
                if node and node_dir.name != node:
                    continue
                for item in node_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.') and item.name != 'common_prj':
                        projects.append({
                            'foundry': foundry_dir.name,
                            'node': node_dir.name,
                            'project': item.name
                        })

        return sorted(projects, key=lambda x: (x['foundry'], x['node'], x['project']))

    def resolve_context(self, path: Path) -> Optional[Dict[str, str]]:
        """从 cwd 向上查找 .edp_version，推断项目上下文。

        遍历当前目录及其父目录，找到最近的 .edp_version 即停止。
        .edp_version 所在目录即为 {work_path}/{project}/{version}/，
        然后根据 cwd 相对于此目录的深度，提取 block / user / branch。

        Returns:
            上下文字典，至少包含 work_path / project_name / project_node /
            foundry / node，可能包含 block_name / user / branch / branch_path。
            检测失败返回 None。
        """
        current = Path(path).resolve()

        for candidate in [current] + list(current.parents):
            vf = candidate / '.edp_version'
            if not vf.exists():
                continue

            # 读取版本信息
            try:
                with open(vf, 'r', encoding='utf-8') as f:
                    info = yaml.safe_load(f) or {}
            except Exception:
                continue

            if 'project' not in info:
                continue

            # candidate = {work_path}/{project}/{version}
            # work_path 需要再往上两层
            result = {
                'work_path': str(candidate.parent.parent.resolve()),
                'project_name': info['project'],
                'project_node': info.get('version', candidate.name),
                'foundry': info.get('foundry'),
                'node': info.get('node'),
            }

            # 根据 cwd 相对于 project_path 的深度提取更多上下文
            try:
                rel = current.relative_to(candidate)
                parts = rel.parts
            except ValueError:
                return result  # cwd 就是 project_path 本身

            if len(parts) >= 1:
                result['block_name'] = parts[0]
            if len(parts) >= 2:
                result['user'] = parts[1]
            if len(parts) >= 3:
                result['branch'] = parts[2]
                result['branch_path'] = candidate / parts[0] / parts[1] / parts[2]

            return result

        return None
