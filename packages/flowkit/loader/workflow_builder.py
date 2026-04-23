#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.loader.workflow_builder - 工作流构建器

整合步骤定义、依赖关系和工具选择，创建可执行的工作流。
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

from ..core.graph import Graph
from ..core.step import Step, StepStatus
from .dependency_loader import DependencyLoader
from .step_loader import StepRegistry


class WorkflowBuilder:
    """工作流构建器

    整合步骤定义、依赖关系和工具选择，创建可执行的工作流。
    """

    def __init__(self, registry: Optional[StepRegistry] = None):
        self.step_registry = registry or StepRegistry()
        self.dependency_loader = DependencyLoader()
        self.flow_base_path: Optional[Path] = None
        self.flow_overlay_path: Optional[Path] = None

    def register_from_flow_path(self, base_path: Path,
                                 overlay_path: Optional[Path] = None) -> None:
        """从 flow 目录加载工具步骤（覆盖链）

        Args:
            base_path: base flow 路径（如 common_prj/）
            overlay_path: 可选 overlay 路径（如 dongting/）
        """
        self.flow_base_path = base_path
        self.flow_overlay_path = overlay_path
        self.step_registry.load_with_override(base_path, overlay_path)

    def load_dependencies(self, dep_files: Union[Path, List[Path]]) -> Graph:
        """加载步骤依赖关系

        Args:
            dep_files: 一个或多个依赖文件路径

        Returns:
            构建好的 Graph 对象
        """
        if isinstance(dep_files, Path):
            dep_files = [dep_files]

        return self.dependency_loader.load_from_multiple_files(dep_files)

    def check_step_readiness(self, graph: Graph,
                              tool_selection: Dict[str, str]) -> Dict[str, Dict]:
        """检查每个 step 的就绪状态

        按 overlay → base 链查找 tool/steps/{step}/ 下的 .tcl 文件。
        有 .tcl 文件 = ready，没有 = not ready。

        Returns:
            {
                step_id: {
                    'tool': tool_name,
                    'ready': True/False,
                    'source': 'overlay'|'base'|None,
                }
            }
        """
        result = {}
        for step_id in graph.steps:
            tool_name = tool_selection.get(step_id, '')
            if not tool_name:
                result[step_id] = {
                    'tool': '',
                    'ready': False,
                    'source': None,
                }
                continue

            # 查找路径：overlay 先，base 后
            source = None
            for label, path in [('overlay', self.flow_overlay_path),
                                ('base', self.flow_base_path)]:
                if not path:
                    continue
                step_dir = path / 'cmds' / tool_name / 'steps' / step_id
                if step_dir.is_dir() and any(step_dir.glob('*.tcl')):
                    source = label
                    break

            result[step_id] = {
                'tool': tool_name,
                'ready': source is not None,
                'source': source,
            }

        return result

    def create_workflow(self,
                       dependency_files: Union[Path, List[Path]],
                       tool_selection: Dict[str, str]) -> 'ExecutableWorkflow':
        """创建可执行的工作流

        Args:
            dependency_files: 依赖文件路径（graph_config*.yaml）
            tool_selection: 工具选择配置 {step_name: tool_name}

        Returns:
            可执行的工作流对象

        Raises:
            ValueError: 如果工具选择无效
        """
        # 1. 加载依赖关系
        graph = self.load_dependencies(dependency_files)

        # 2. 验证工具选择
        self._validate_tool_selection(graph, tool_selection)

        # 3. 加载步骤实现
        steps = self._load_step_implementations(graph, tool_selection)

        # 4. 创建可执行工作流
        workflow = ExecutableWorkflow(
            graph=graph,
            steps=steps,
            tool_selection=tool_selection
        )

        return workflow

    def create_workflow_from_dict(self,
                                   dependencies: Dict[str, Union[str, List[str]]],
                                   tool_selection: Dict[str, str]) -> 'ExecutableWorkflow':
        """从字典直接创建工作流（便捷方法，用于测试）

        Args:
            dependencies: 依赖关系字典
            tool_selection: 工具选择配置

        Returns:
            可执行的工作流对象
        """
        # 1. 构建图
        graph = self.dependency_loader.load_from_dict(dependencies)

        # 2. 创建步骤对象
        steps = {}
        for step_id, tool_name in tool_selection.items():
            sub_steps = []
            if self.step_registry.has_step(tool_name, step_id):
                sub_steps = self.step_registry.get_sub_steps(tool_name, step_id)

            steps[step_id] = Step(
                id=step_id,
                name=step_id,
                tool_name=tool_name,
                sub_steps=sub_steps
            )

        # 3. 创建工作流
        return ExecutableWorkflow(graph, steps, tool_selection)

    def _validate_tool_selection(self, graph: Graph, tool_selection: Dict[str, str]) -> None:
        """验证工具选择是否有效

        允许 graph 中有 step 没有配置工具（flow owner 尚未准备好）。
        执行时遇到未配置工具的 step 会失败并报错。

        Args:
            graph: 依赖图
            tool_selection: 工具选择配置

        Raises:
            ValueError: 如果工具选择无效
        """
        # 检查工具选择中的每个 step 都在 graph 中
        extra = [s for s in tool_selection if s not in graph.steps]
        if extra:
            raise ValueError(
                f"step_config.yaml 中的步骤不在依赖图中: {extra}"
            )

        # 检查已配置的工具已注册
        for step_id, tool_name in tool_selection.items():
            if not self.step_registry.has_tool(tool_name):
                raise ValueError(f"工具 {tool_name} 未注册")

    def _load_step_implementations(self, graph: Graph,
                                    tool_selection: Dict[str, str]) -> Dict[str, Step]:
        """加载步骤的具体实现

        Args:
            graph: 依赖图
            tool_selection: 工具选择配置

        Returns:
            步骤 ID 到 Step 对象的映射
        """
        steps = {}

        for step_id, tool_name in tool_selection.items():
            sub_steps = []
            if self.step_registry.has_step(tool_name, step_id):
                sub_steps = self.step_registry.get_sub_steps(tool_name, step_id)

            steps[step_id] = Step(
                id=step_id,
                name=step_id,
                tool_name=tool_name,
                sub_steps=sub_steps
            )

        return steps


class ExecutableWorkflow:
    """可执行的工作流

    整合了图逻辑和具体实现，准备好执行。
    """

    def __init__(self, graph: Graph, steps: Dict[str, Step], tool_selection: Dict[str, str]):
        self.graph = graph
        self.steps = steps
        self.tool_selection = tool_selection
        self.name = "workflow"

    def get_execution_plan(self) -> List[List[str]]:
        """获取执行计划

        Returns:
            执行层级列表，每层可以并行执行
        """
        return self.graph.get_execution_levels()

    def get_initial_state(self) -> Dict[str, StepStatus]:
        """获取初始状态

        Returns:
            所有步骤的初始状态字典
        """
        return {step_id: StepStatus.INIT for step_id in self.steps}

    def get_step_sub_steps(self, step_id: str) -> List[str]:
        """获取步骤的 sub_step 列表

        Args:
            step_id: 步骤 ID

        Returns:
            sub_step 名称列表
        """
        step = self.steps.get(step_id)
        return step.sub_steps if step else []

    def get_step_tool(self, step_id: str) -> str:
        """获取步骤使用的工具

        Args:
            step_id: 步骤 ID

        Returns:
            工具名称
        """
        step = self.steps.get(step_id)
        return step.tool_name if step else ""

    def validate(self) -> Tuple[bool, List[str]]:
        """验证工作流的有效性

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 验证图
        graph_errors = self.graph.validate()
        errors.extend(graph_errors)

        # 验证步骤都有工具
        for step_id, step in self.steps.items():
            if not step.tool_name:
                errors.append(f"步骤 {step_id} 未指定工具")

        return (len(errors) == 0, errors)

    def get_summary(self) -> str:
        """获取工作流摘要

        Returns:
            摘要信息字符串
        """
        lines = [
            f"工作流: {self.name}",
            f"工具选择: {self.tool_selection}",
            f"步骤数量: {len(self.steps)}",
            f"依赖数量: {len(self.graph.dependencies)}",
            "",
            "步骤详情:",
        ]

        for step_id, step in self.steps.items():
            sub_info = f" ({len(step.sub_steps)} sub_steps)" if step.sub_steps else ""
            lines.append(f"  {step_id}: tool={step.tool_name}{sub_info}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ExecutableWorkflow(name={self.name}, steps={len(self.steps)}, tools={set(self.tool_selection.values())})"


# 便捷函数
def create_workflow_from_yaml(dep_files: Union[str, Path, List[str], List[Path]],
                               tool_selection: Dict[str, str],
                               flow_base_path: Optional[Path] = None,
                               flow_overlay_path: Optional[Path] = None) -> ExecutableWorkflow:
    """便捷函数：从 YAML 文件创建工作流

    Args:
        dep_files: 依赖文件路径
        tool_selection: 工具选择配置
        flow_base_path: 可选的 flow base 路径（自动加载工具步骤）
        flow_overlay_path: 可选的 flow overlay 路径

    Returns:
        可执行的工作流对象
    """
    builder = WorkflowBuilder()

    # 加载工具步骤
    if flow_base_path:
        builder.register_from_flow_path(flow_base_path, flow_overlay_path)

    # 创建工作流
    return builder.create_workflow(
        dependency_files=[Path(f) if isinstance(f, str) else f for f in dep_files],
        tool_selection=tool_selection
    )
