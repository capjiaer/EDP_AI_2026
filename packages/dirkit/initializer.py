#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit.initializer - 项目环境初始化

从 edp_center 资源库中提取配置和流程，初始化项目工作环境。
"""

from pathlib import Path
from typing import Optional, List, Dict, Union

from .dirkit import DirKit


class ProjectInitializer:
    """项目环境初始化器"""

    def __init__(self, edp_center_path: Union[str, Path]):
        """
        初始化 ProjectInitializer

        Args:
            edp_center_path: edp_center 资源库的路径

        Raises:
            FileNotFoundError: 如果 edp_center 不存在
        """
        self.edp_center = Path(edp_center_path)
        if not self.edp_center.exists():
            raise FileNotFoundError(f"edp_center 不存在: {self.edp_center}")

        self.initialize_path = self.edp_center / "flow" / "initialize"
        self.flow_path = self.edp_center / "flow"

    def init_project(self, project_dir: Union[str, Path],
                     foundry: str, node: str, project: str,
                     link_mode: bool = False) -> Dict[str, Path]:
        """
        初始化项目环境

        Args:
            project_dir: 项目目录路径
            foundry: 代工厂名称（如 SAMSUNG）
            node: 工艺节点（如 S4）
            project: 项目名称（如 dongting）
            link_mode: 是否使用符号链接而不是复制（默认：False）

        Returns:
            包含创建的目录路径的字典
        """
        dirkit = DirKit(base_path=project_dir)
        created = {}

        # 1. 创建基础目录结构
        created['cmds'] = dirkit.ensure_dir("cmds")
        created['hooks'] = dirkit.ensure_dir("hooks")

        # 2. 复制/链接 common_prj 的 flow 文件（cmds + hooks）
        self._init_flow(dirkit, foundry, node, link_mode)

        # 3. 覆盖 project 级的 flow 文件
        self._init_project_overlay(dirkit, foundry, node, project, link_mode)

        return created

    def _init_flow(self, dirkit: DirKit, foundry: str, node: str,
                   link_mode: bool):
        """初始化 common_prj 的 flow 文件"""
        common_prj_path = self.initialize_path / foundry / node / "common_prj"

        if not common_prj_path.exists():
            raise FileNotFoundError(
                f"common_prj 不存在: {common_prj_path}\n"
                f"路径结构应为: initialize/{foundry}/{node}/common_prj/"
            )

        # 复制/链接 cmds 目录
        src_cmds = common_prj_path / "cmds"
        if src_cmds.exists():
            target_cmds = dirkit.base_path / "cmds"
            if link_mode:
                dirkit.link_dir(src_cmds, target_cmds, overwrite=True)
            else:
                dirkit.copy_dir(src_cmds, target_cmds, overwrite=True)

        # 复制/链接 step_config.yaml 和 graph_config*.yaml
        for name in ["step_config.yaml"] + sorted(
            f.name for f in common_prj_path.glob("graph_config*.yaml")
        ):
            src_file = common_prj_path / name
            target_file = dirkit.base_path / name
            if src_file.exists():
                if link_mode:
                    dirkit.link_file(src_file, target_file, overwrite=True)
                else:
                    dirkit.copy_file(src_file, target_file, overwrite=True)

    def _init_project_overlay(self, dirkit: DirKit, foundry: str,
                              node: str, project: str, link_mode: bool):
        """覆盖 project 级的 flow 文件"""
        project_path = self.initialize_path / foundry / node / project

        if not project_path.exists():
            return

        # 覆盖 cmds 目录下的工具
        src_cmds = project_path / "cmds"
        if src_cmds.exists():
            for tool_dir in src_cmds.iterdir():
                if not tool_dir.is_dir():
                    continue
                target_tool = dirkit.base_path / "cmds" / tool_dir.name
                if link_mode:
                    dirkit.link_dir(tool_dir, target_tool, overwrite=True)
                else:
                    dirkit.copy_dir(tool_dir, target_tool, overwrite=True)

        # 覆盖 step_config.yaml 和 graph_config*.yaml
        for name in ["step_config.yaml"] + sorted(
            f.name for f in project_path.glob("graph_config*.yaml")
        ):
            src_file = project_path / name
            target_file = dirkit.base_path / name
            if src_file.exists():
                if link_mode:
                    dirkit.link_file(src_file, target_file, overwrite=True)
                else:
                    dirkit.copy_file(src_file, target_file, overwrite=True)
