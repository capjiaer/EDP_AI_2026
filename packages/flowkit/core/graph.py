#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.core.graph - 依赖图构建模块

专注于图逻辑：步骤和依赖关系的管理，不关心执行细节。
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

from .step import Step, StepStatus


@dataclass
class Dependency:
    """依赖关系定义"""
    from_step: str           # 源步骤
    to_step: str             # 目标步骤
    weak: bool = False       # 是否为弱依赖


class Graph:
    """依赖图类

    管理步骤和依赖关系，提供图操作和查询功能。
    不关心执行逻辑，只关注图的结构。

    Attributes:
        steps: 步骤ID到Step对象的映射
        dependencies: 依赖关系列表
        adjacency_list: 邻接表，用于快速图查询
    """

    def __init__(self):
        self.steps: Dict[str, Step] = {}
        self.dependencies: List[Dependency] = []
        self._adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_step(self, step: Step) -> None:
        """添加步骤

        Args:
            step: Step对象

        Raises:
            ValueError: 如果步骤ID已存在
        """
        if step.id in self.steps:
            raise ValueError(f"步骤 {step.id} 已存在")

        self.steps[step.id] = step
        # 初始化邻接表条目
        if step.id not in self._adjacency_list:
            self._adjacency_list[step.id] = set()
        if step.id not in self._reverse_adjacency:
            self._reverse_adjacency[step.id] = set()

    def add_dependency(self, from_step: str, to_step: str, weak: bool = False) -> None:
        """添加依赖关系

        Args:
            from_step: 源步骤ID
            to_step: 目标步骤ID
            weak: 是否为弱依赖

        Raises:
            ValueError: 如果步骤不存在或形成环
        """
        # 验证步骤存在
        if from_step not in self.steps:
            raise ValueError(f"源步骤 {from_step} 不存在")
        if to_step not in self.steps:
            raise ValueError(f"目标步骤 {to_step} 不存在")

        # 检查是否会形成环
        if weak:
            # 弱依赖不检查环
            pass
        else:
            if self._would_create_cycle(from_step, to_step):
                raise ValueError(f"添加依赖 {from_step} -> {to_step} 会形成环")

        # 添加依赖关系
        dep = Dependency(from_step, to_step, weak)
        self.dependencies.append(dep)

        # 更新邻接表
        self._adjacency_list[from_step].add(to_step)
        self._reverse_adjacency[to_step].add(from_step)

    def get_dependencies(self, step_id: str, weak_only: bool = False) -> List[str]:
        """获取步骤的直接依赖

        Args:
            step_id: 步骤ID
            weak_only: 是否只返回弱依赖

        Returns:
            依赖步骤ID列表
        """
        deps = []
        for dep in self.dependencies:
            if dep.from_step == step_id:
                if not weak_only or (weak_only and dep.weak):
                    deps.append(dep.to_step)
        return deps

    def get_dependents(self, step_id: str) -> List[str]:
        """获取依赖于当前步骤的所有步骤

        Args:
            step_id: 步骤ID

        Returns:
            依赖当前步骤的步骤ID列表
        """
        return list(self._reverse_adjacency[step_id])

    def get_topological_order(self) -> List[str]:
        """获取拓扑排序顺序

        Returns:
            按拓扑排序的步骤ID列表

        Raises:
            ValueError: 如果图中存在环
        """
        # Kahn算法实现拓扑排序
        in_degree = defaultdict(int)

        # 计算入度
        for dep in self.dependencies:
            in_degree[dep.to_step] += 1

        # 找到所有入度为0的节点
        queue = deque([step_id for step_id in self.steps if in_degree[step_id] == 0])
        topological_order = []

        while queue:
            step_id = queue.popleft()
            topological_order.append(step_id)

            # 减少依赖当前节点的节点的入度
            for dependent in self._adjacency_list[step_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(topological_order) != len(self.steps):
            raise ValueError("图中存在环，无法进行拓扑排序")

        return topological_order

    def get_runnable_steps(self, current_state: Dict[str, StepStatus]) -> List[str]:
        """获取当前可执行的步骤

        Args:
            current_state: 当前所有步骤的状态

        Returns:
            可执行的步骤ID列表
        """
        runnable = []

        for step_id, step in self.steps.items():
            if step.can_execute():
                # 检查依赖是否满足
                if self._are_dependencies_satisfied(step_id, current_state):
                    runnable.append(step_id)

        return runnable

    def get_parallel_groups(self, current_state: Dict[str, StepStatus]) -> List[List[str]]:
        """获取可并行执行的步骤组

        Args:
            current_state: 当前所有步骤的状态

        Returns:
            步骤组列表，每个组内的步骤可以并行执行
        """
        # 获取可执行步骤
        runnable = set(self.get_runnable_steps(current_state))

        # 基于依赖关系分组
        groups = []
        processed = set()

        for step_id in runnable:
            if step_id in processed:
                continue

            # 找到可以与当前步骤并行的步骤
            parallel_group = {step_id}
            processed.add(step_id)

            for other_step in runnable:
                if other_step in processed:
                    continue

                # 检查是否可以并行
                if self._can_parallel_execute(step_id, other_step, current_state):
                    parallel_group.add(other_step)
                    processed.add(other_step)

            groups.append(list(parallel_group))

        return groups

    def _would_create_cycle(self, from_step: str, to_step: str) -> bool:
        """检查添加依赖是否会形成环"""
        # 临时添加边
        self._adjacency_list[from_step].add(to_step)
        self._reverse_adjacency[to_step].add(from_step)

        # 检测环
        has_cycle = self._has_cycle()

        # 移除临时边
        self._adjacency_list[from_step].discard(to_step)
        self._reverse_adjacency[to_step].discard(from_step)

        return has_cycle

    def _has_cycle(self) -> bool:
        """检测图中是否存在环（DFS）"""
        visited = set()
        rec_stack = set()

        def dfs(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            for neighbor in self._adjacency_list[step_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(step_id)
            return False

        for step_id in self.steps:
            if step_id not in visited:
                if dfs(step_id):
                    return True

        return False

    def _are_dependencies_satisfied(self, step_id: str, current_state: Dict[str, StepStatus]) -> bool:
        """检查步骤的依赖是否满足"""
        for dep in self.dependencies:
            if dep.to_step == step_id:
                # 检查源步骤状态
                source_status = current_state.get(dep.from_step, StepStatus.INIT)

                if dep.weak:
                    # 弱依赖：只检查是否完成，不阻塞执行
                    if source_status not in [StepStatus.FINISHED, StepStatus.SKIPPED]:
                        # 弱依赖未完成，但不阻塞
                        continue
                else:
                    # 强依赖：必须完成
                    if source_status not in [StepStatus.FINISHED, StepStatus.SKIPPED]:
                        return False

        return True

    def _can_parallel_execute(self, step1: str, step2: str, current_state: Dict[str, StepStatus]) -> bool:
        """检查两个步骤是否可以并行执行"""
        # 获取两个步骤的所有依赖
        deps1 = self._get_all_dependencies(step1, current_state)
        deps2 = self._get_all_dependencies(step2, current_state)

        # 如果两个步骤有依赖关系，不能并行
        if step1 in deps2 or step2 in deps1:
            return False

        # 如果它们共享某个依赖步骤，且该依赖还在进行中，不能并行
        common_deps = deps1 & deps2
        for dep_id in common_deps:
            if current_state.get(dep_id) == StepStatus.RUNNING:
                return False

        return True

    def _get_all_dependencies(self, step_id: str, current_state: Dict[str, StepStatus]) -> Set[str]:
        """获取步骤的所有依赖（包括传递依赖）"""
        all_deps = set()
        visited = set()

        def collect_deps(step_id: str):
            if step_id in visited:
                return

            visited.add(step_id)

            for dep in self.dependencies:
                if dep.to_step == step_id:
                    if not dep.weak:  # 只考虑强依赖
                        all_deps.add(dep.from_step)
                        collect_deps(dep.from_step)

        collect_deps(step_id)
        return all_deps

    def get_execution_levels(self) -> List[List[str]]:
        """获取执行层级（可用于并行优化）

        Returns:
            步骤组列表，每组内的步骤可以并行执行
        """
        levels = []
        processed = set()

        while len(processed) < len(self.steps):
            # 找出当前可执行的步骤
            current_level = []
            current_state = {step_id: StepStatus.FINISHED for step_id in processed}

            for step_id in self.steps:
                if step_id not in processed:
                    if self._are_dependencies_satisfied(step_id, current_state):
                        current_level.append(step_id)

            if not current_level:
                # 如果没有可执行步骤，说明存在环
                remaining = set(self.steps.keys()) - processed
                raise ValueError(f"无法构建执行层级，剩余步骤: {remaining}")

            levels.append(current_level)
            processed.update(current_level)

        return levels

    def validate(self) -> List[str]:
        """验证图的完整性

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 检查是否有步骤
        if not self.steps:
            errors.append("图中没有步骤")
            return errors

        # 检查是否有环
        if self._has_cycle():
            errors.append("图中存在环")

        # 检查是否存在孤立节点
        all_steps = set(self.steps.keys())
        connected = set()

        for dep in self.dependencies:
            connected.add(dep.from_step)
            connected.add(dep.to_step)

        isolated = all_steps - connected
        if isolated:
            errors.append(f"存在孤立步骤: {isolated}")

        return errors

    def get_statistics(self) -> Dict[str, Any]:
        """获取图的统计信息"""
        return {
            'total_steps': len(self.steps),
            'total_dependencies': len(self.dependencies),
            'weak_dependencies': sum(1 for dep in self.dependencies if dep.weak),
            'strong_dependencies': sum(1 for dep in self.dependencies if not dep.weak),
            'max_depth': self._calculate_max_depth(),
            'avg_parallelism': self._calculate_avg_parallelism()
        }

    # --- 子图提取 ---

    def get_downstream_steps(self, step_id: str) -> Set[str]:
        """获取 step_id 的所有下游步骤（包含自身）"""
        if step_id not in self.steps:
            raise ValueError(f"Step not found: {step_id}")
        visited = set()
        queue = deque([step_id])
        visited.add(step_id)
        while queue:
            current = queue.popleft()
            for neighbor in self._adjacency_list[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def get_upstream_steps(self, step_id: str) -> Set[str]:
        """获取 step_id 的所有上游步骤（不包含自身，只走强依赖）"""
        if step_id not in self.steps:
            raise ValueError(f"Step not found: {step_id}")
        visited = set()
        queue = deque()
        for dep in self.dependencies:
            if dep.to_step == step_id and not dep.weak:
                if dep.from_step not in visited:
                    visited.add(dep.from_step)
                    queue.append(dep.from_step)
        while queue:
            current = queue.popleft()
            for dep in self.dependencies:
                if dep.to_step == current and not dep.weak:
                    if dep.from_step not in visited:
                        visited.add(dep.from_step)
                        queue.append(dep.from_step)
        return visited

    def extract_subgraph(self, from_step: str, to_step: str) -> 'Graph':
        """提取 from_step 到 to_step 之间的子图

        包含 from_step、to_step、以及路径上的所有 step。
        """
        if from_step not in self.steps:
            raise ValueError(f"Step not found: {from_step}")
        if to_step not in self.steps:
            raise ValueError(f"Step not found: {to_step}")

        downstream = self.get_downstream_steps(from_step)
        upstream = self.get_upstream_steps(to_step)
        upstream.add(to_step)

        result = downstream & upstream

        if from_step not in result or to_step not in result:
            raise ValueError(f"No path from {from_step} to {to_step}")

        # 构建子图
        sub = Graph()
        for sid in result:
            sub.add_step(self.steps[sid])
        for dep in self.dependencies:
            if dep.from_step in result and dep.to_step in result:
                sub.add_dependency(dep.from_step, dep.to_step, dep.weak)

        return sub

    def _calculate_max_depth(self) -> int:
        """计算图的最大深度"""
        topological_order = self.get_topological_order()
        depth_map = {step_id: 0 for step_id in topological_order}

        for step_id in topological_order:
            for dep in self.dependencies:
                if dep.from_step == step_id:
                    if depth_map[dep.from_step] + 1 > depth_map.get(dep.to_step, 0):
                        depth_map[dep.to_step] = depth_map[dep.from_step] + 1

        return max(depth_map.values()) if depth_map else 0

    def _calculate_avg_parallelism(self) -> float:
        """计算平均并行度"""
        levels = self.get_execution_levels()

        if not levels:
            return 0.0

        total_parallelism = sum(len(level) for level in levels)
        return total_parallelism / len(levels)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"Graph(steps={len(self.steps)}, dependencies={len(self.dependencies)})"
