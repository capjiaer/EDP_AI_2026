#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.loader.dependency_loader - 依赖关系加载器

支持多种依赖关系格式的加载，提供简洁的语法。
"""

import yaml
from pathlib import Path
from typing import Dict, List, Union, Tuple

from ..core.graph import Graph, Dependency


class DependencyLoader:
    """依赖关系加载器"""

    def __init__(self):
        self.graph = Graph()

    def load_from_file(self, dep_file: Path) -> Graph:
        """从文件加载依赖关系

        支持多种格式：
        1. 简单格式：A: B          (强依赖，默认)
        2. 并行格式：A: [B, C, D]
        3. 弱依赖：  A: B?         (弱依赖，不阻塞执行)
        4. 详细格式：A: {next: B, type: weak}

        Args:
            dep_file: 依赖文件路径

        Returns:
            构建好的Graph对象
        """
        if not dep_file.exists():
            raise FileNotFoundError(f"依赖文件不存在: {dep_file}")

        with open(dep_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return self.load_from_dict(data)

    def load_from_dict(self, data: dict) -> Graph:
        """从字典加载依赖关系

        Args:
            data: 包含依赖关系的字典

        Returns:
            构建好的Graph对象
        """
        graph = Graph()

        # 解析所有依赖关系
        for from_step, to_step in data.items():
            if isinstance(to_step, str):
                # 单个依赖：A: B
                self._add_single_dependency(graph, from_step, to_step)
            elif isinstance(to_step, list):
                # 并行依赖：A: [B, C, D]
                for dep in to_step:
                    self._add_single_dependency(graph, from_step, dep)
            elif isinstance(to_step, dict):
                # 详细格式：A: {next: B, type: weak}
                if 'next' in to_step:
                    next_step = to_step['next']
                    dep_type = to_step.get('type', 'strong')
                    weak = (dep_type == 'weak')
                    self._add_single_dependency(graph, from_step, next_step, weak)

        return graph

    def load_from_multiple_files(self, dep_files: List[Path]) -> Graph:
        """从多个文件加载依赖关系

        Args:
            dep_files: 依赖文件路径列表

        Returns:
            合并后的Graph对象
        """
        graph = Graph()

        for dep_file in dep_files:
            temp_graph = self.load_from_file(dep_file)

            # 合并步骤和依赖
            for step_id, step in temp_graph.steps.items():
                if step_id not in graph.steps:
                    graph.add_step(step)

            for dep in temp_graph.dependencies:
                graph.add_dependency(
                    dep.from_step,
                    dep.to_step,
                    dep.weak
                )

        return graph

    def _add_single_dependency(self, graph: Graph, from_step: str,
                              to_step: str, weak: bool = False) -> None:
        """添加单个依赖关系（解析弱依赖标记）

        语法：
        - A: B     -> 强依赖（默认）
        - A: B?    -> 弱依赖
        """
        from ..core.step import Step

        # 解析弱依赖标记（只有 ? 标记弱依赖，强依赖是默认行为）
        if to_step.endswith('?'):
            step_name = to_step[:-1].strip()
            is_weak = True
        else:
            step_name = to_step.strip()
            is_weak = weak  # 默认强依赖

        # 确保步骤存在（如果不存在则创建空步骤）
        if from_step not in graph.steps:
            graph.add_step(Step(id=from_step, name=from_step, cmd=""))
        if step_name not in graph.steps:
            graph.add_step(Step(id=step_name, name=step_name, cmd=""))

        # 添加依赖
        graph.add_dependency(from_step, step_name, is_weak)


class DependencyParser:
    """依赖关系解析器"""

    @staticmethod
    def parse_dependency_string(dep_string: str) -> Tuple[str, str, bool]:
        """解析依赖字符串

        支持的格式：
        - "A: B"  -> ("A", "B", False)  强依赖（默认）
        - "A: B?" -> ("A", "B", True)   弱依赖

        Args:
            dep_string: 依赖字符串

        Returns:
            (from_step, to_step, is_weak) 元组
        """
        dep_string = dep_string.strip()

        if ':' not in dep_string:
            raise ValueError(f"无效的依赖格式: {dep_string}")

        parts = dep_string.split(':', 1)
        if len(parts) != 2:
            raise ValueError(f"无效的依赖格式: {dep_string}")

        from_step = parts[0].strip()
        to_step = parts[1].strip()

        # 解析弱依赖标记
        is_weak = to_step.endswith('?')
        if is_weak:
            to_step = to_step[:-1].strip()

        return from_step, to_step, is_weak


class DependencyValidator:
    """依赖关系验证器"""

    @staticmethod
    def validate_dependency_format(data: dict) -> Tuple[bool, List[str]]:
        """验证依赖关系数据格式

        Args:
            data: 依赖关系字典

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        if not isinstance(data, dict):
            errors.append("依赖关系必须是字典格式")
            return False, errors

        for from_step, to_step in data.items():
            if not isinstance(from_step, str):
                errors.append(f"源步骤必须是字符串: {from_step}")

            if isinstance(to_step, str):
                # 验证单个依赖
                if not DependencyValidator._validate_step_name(to_step):
                    errors.append(f"无效的目标步骤名称: {to_step}")
            elif isinstance(to_step, list):
                # 验证并行依赖
                for step in to_step:
                    if not DependencyValidator._validate_step_name(step):
                        errors.append(f"无效的目标步骤名称: {step}")
            elif isinstance(to_step, dict):
                # 验证详细格式
                if 'next' not in to_step:
                    errors.append(f"详细格式必须包含 'next' 字段: {from_step}")
                else:
                    next_step = to_step['next']
                    if not DependencyValidator._validate_step_name(next_step):
                        errors.append(f"无效的目标步骤名称: {next_step}")
            else:
                errors.append(f"无效的依赖格式: {type(to_step)}")

        return len(errors) == 0, errors

    @staticmethod
    def _validate_step_name(step_name: str) -> bool:
        """验证步骤名称是否有效"""
        if not isinstance(step_name, str):
            return False

        step_name = step_name.strip()

        # 不能为空
        if not step_name:
            return False

        # 不能包含特殊字符
        invalid_chars = ['!', '@', '#', '$', '%', '^', '&', '*']
        if any(char in step_name for char in invalid_chars):
            return False

        return True


def create_dependency_graph(dependencies: Dict[str, Union[str, List[str]]]) -> Graph:
    """便捷函数：从依赖字典创建图

    Args:
        dependencies: 依赖关系字典
            - 单个依赖：{"ipmerge": "dummy"}       (强依赖)
            - 并行依赖：{"dummy": ["drc", "lvs", "perc"]}
            - 弱依赖：  {"lvs": "drc?"}           (弱依赖)

    Returns:
        构建好的Graph对象

    Examples:
        >>> deps = {
        ...     "ipmerge": "dummy",       # 强依赖（默认）
        ...     "dummy": ["drc", "lvs"],  # 并行依赖
        ...     "lvs": "final?"           # 弱依赖
        ... }
        >>> graph = create_dependency_graph(deps)
    """
    loader = DependencyLoader()
    return loader.load_from_dict(dependencies)


def load_dependencies_from_yaml(yaml_files: Union[str, Path, List[Union[str, Path]]]) -> Graph:
    """便捷函数：从YAML文件加载依赖关系

    Args:
        yaml_files: 一个或多个YAML文件路径

    Returns:
        构建好的Graph对象
    """
    if isinstance(yaml_files, (str, Path)):
        yaml_files = [yaml_files]

    yaml_paths = [Path(f) for f in yaml_files]
    loader = DependencyLoader()
    return loader.load_from_multiple_files(yaml_paths)
