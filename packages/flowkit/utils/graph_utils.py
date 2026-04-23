#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.utils.graph_utils - 图算法工具模块

提供各种图算法和分析功能。
"""

from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque

from ..core.step import StepStatus


class GraphAnalyzer:
    """图分析器 - 提供图分析功能"""

    @staticmethod
    def find_critical_path(graph) -> List[str]:
        """查找关键路径（最长路径）

        Args:
            graph: Graph对象

        Returns:
            关键路径上的步骤ID列表
        """
        topological_order = graph.get_topological_order()
        distance = {step_id: 0 for step_id in topological_order}
        predecessor = {}

        for step_id in topological_order:
            for dep in graph.dependencies:
                if dep.to_step == step_id and not dep.weak:
                    if distance[dep.from_step] + 1 > distance[step_id]:
                        distance[step_id] = distance[dep.from_step] + 1
                        predecessor[step_id] = dep.from_step

        # 找到最远的节点
        if not distance:
            return []

        max_dist = max(distance.values())
        end_step = max(distance.keys(), key=lambda k: distance[k])

        # 回溯构建路径
        path = []
        current = end_step
        while current in predecessor:
            path.append(current)
            current = predecessor[current]

        path.reverse()
        return path

    @staticmethod
    def find_cycles(graph) -> List[List[str]]:
        """查找图中的所有环

        Args:
            graph: Graph对象

        Returns:
            环的列表，每个环是一个步骤ID列表
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph._adjacency_list[node]:
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # 找到环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for step_id in graph.steps:
            if step_id not in visited:
                dfs(step_id, [])

        return cycles

    @staticmethod
    def calculate_execution_time(graph, step_times: Dict[str, float]) -> Dict[str, float]:
        """计算执行时间

        Args:
            graph: Graph对象
            step_times: 每个步骤的执行时间

        Returns:
            每个步骤的最早开始时间和最晚完成时间
        """
        topological_order = graph.get_topological_order()

        earliest_start = {}
        latest_finish = {}

        # 正向计算最早开始时间
        for step_id in topological_order:
            max_prev_finish = 0
            for dep in graph.dependencies:
                if dep.to_step == step_id and not dep.weak:
                    prev_finish = earliest_start.get(dep.from_step, 0) + step_times.get(dep.from_step, 0)
                    if prev_finish > max_prev_finish:
                        max_prev_finish = prev_finish

            earliest_start[step_id] = max_prev_finish

        # 反向计算最晚完成时间
        for step_id in reversed(topological_order):
            min_next_start = float('inf')
            has_dependents = False

            for dep in graph.dependencies:
                if dep.from_step == step_id and not dep.weak:
                    next_start = earliest_start.get(dep.to_step, 0)
                    if next_start < min_next_start:
                        min_next_start = next_start
                    has_dependents = True

            if has_dependents:
                latest_finish[step_id] = min_next_start - step_times.get(step_id, 0)
            else:
                latest_finish[step_id] = earliest_start[step_id] + step_times.get(step_id, 0)

        return {
            'earliest_start': earliest_start,
            'latest_finish': latest_finish
        }

    @staticmethod
    def get_execution_levels(graph) -> List[List[str]]:
        """获取执行层级

        Args:
            graph: Graph对象

        Returns:
            步骤组列表，每组可以并行执行
        """
        return graph.get_execution_levels()


class GraphValidator:
    """图验证器 - 验证图的完整性"""

    @staticmethod
    def validate_graph(graph) -> Tuple[bool, List[str]]:
        """验证图的完整性

        Args:
            graph: Graph对象

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = graph.validate()

        if not errors:
            return True, []
        else:
            return False, errors


class GraphOptimizer:
    """图优化器 - 提供图优化功能"""

    @staticmethod
    def optimize_dependencies(graph, optimization_strategy: str = "none") -> dict:
        """优化依赖关系

        Args:
            graph: Graph对象
            optimization_strategy: 优化策略
                - "none": 不优化
                - "transitive_reduction": 传递依赖简化
                - "parallelization": 并行化优化

        Returns:
            优化统计信息
        """
        stats = {
            'original_dependencies': len(graph.dependencies),
            'optimized_dependencies': len(graph.dependencies),
            'reduction_count': 0
        }

        if optimization_strategy == "transitive_reduction":
            # 移除传递依赖
            GraphOptimizer._remove_transitive_dependencies(graph)
            stats['optimized_dependencies'] = len(graph.dependencies)
            stats['reduction_count'] = stats['original_dependencies'] - stats['optimized_dependencies']

        return stats

    @staticmethod
    def _remove_transitive_dependencies(graph):
        """移除传递依赖

        如果 A->B, B->C，则 A->C 是传递依赖，可以移除
        """
        to_remove = []

        for dep1 in graph.dependencies:
            for dep2 in graph.dependencies:
                # 检查是否是传递依赖
                if dep1.to_step == dep2.from_step:
                    to_remove.append(dep1)

        # 移除传递依赖
        for dep in to_remove:
            if dep in graph.dependencies:
                graph.dependencies.remove(dep)
                # 更新邻接表
                graph._adjacency_list[dep.from_step].discard(dep.to_step)
                graph._reverse_adjacency[dep.to_step].discard(dep.from_step)


class GraphVisualizer:
    """图可视化器 - 生成图的可视化表示"""

    @staticmethod
    def to_dot_format(graph) -> str:
        """转换为 DOT 格式（Graphviz）

        Args:
            graph: Graph对象

        Returns:
            DOT 格式字符串
        """
        lines = [
            "digraph workflow {",
            "    rankdir=TB;",
            "    node [shape=box];",
            ""
        ]

        # 添加节点
        for step_id, step in graph.steps.items():
            label = f"{step_id}\\n[{step.status.value}]"
            lines.append(f"    \"{step_id}\" [label=\"{label}\"];")

        lines.append("")

        # 添加边
        for dep in graph.dependencies:
            style = "dashed" if dep.weak else "solid"
            lines.append(f"    \"{dep.from_step}\" -> \"{dep.to_step}\" [style={style}];")

        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def to_ascii_format(graph) -> str:
        """转换为 ASCII 艺术图（执行顺序：从上到下）

        Args:
            graph: Graph对象

        Returns:
            ASCII 艺术图字符串
        """
        lines = []
        lines.append("工作流执行顺序：")
        lines.append("")

        topological_order = graph.get_topological_order()

        for step_id in topological_order:
            # 找出依赖当前 step 的后续步骤
            dependents = []
            for dep in graph.dependencies:
                if dep.from_step == step_id:
                    if dep.to_step not in dependents:
                        dependents.append(dep.to_step)
            for d in dependents:
                # 检查下游是否是叶子节点
                d_has_dependents = any(
                    dep.from_step == d for dep in graph.dependencies
                )
                suffix = "" if d_has_dependents else " (end)"
                lines.append(f"{step_id} -> {d}{suffix}")

        return "\n".join(lines)

    @staticmethod
    def to_table_format(graph) -> str:
        """转换为表格格式

        Args:
            graph: Graph对象

        Returns:
            表格格式的字符串
        """
        lines = []
        lines.append("步骤依赖表：")
        lines.append("")
        lines.append(f"{'步骤':<20} {'依赖':<30} {'类型':<10}")
        lines.append("-" * 60)

        for step_id in graph.steps:
            deps = graph.get_dependencies(step_id)
            if deps:
                for dep in deps:
                    dep_type = "弱" if any(
                        d.to_step == step_id and d.weak
                        for d in graph.dependencies
                    ) else "强"
                    lines.append(f"{step_id:<20} {dep:<30} {dep_type:<10}")
            else:
                lines.append(f"{step_id:<20} {'(无依赖)':<30} {'-':<10}")

        return "\n".join(lines)


def find_shortest_path(graph, start_step: str, end_step: str) -> Optional[List[str]]:
    """查找两个步骤之间的最短路径

    Args:
        graph: Graph对象
        start_step: 起始步骤ID
        end_step: 目标步骤ID

    Returns:
        最短路径的步骤ID列表，如果不存在路径则返回None
    """
    if start_step not in graph.steps or end_step not in graph.steps:
        return None

    # BFS 找最短路径
    queue = deque([[start_step]])
    visited = {start_step: True}
    parent = {}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == end_step:
            return path

        for neighbor in graph._adjacency_list[current]:
            if neighbor not in visited:
                visited[neighbor] = True
                parent[neighbor] = current
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)

    return None


def get_graph_summary(graph) -> str:
    """获取图的摘要信息

    Args:
        graph: Graph对象

    Returns:
        摘要信息字符串
    """
    stats = graph.get_statistics()

    summary_parts = [
        f"工作流图摘要",
        f"=" * 30,
        f"总步骤数: {stats['total_steps']}",
        f"总依赖数: {stats['total_dependencies']}",
        f"强依赖: {stats['strong_dependencies']}",
        f"弱依赖: {stats['weak_dependencies']}",
        f"最大深度: {stats['max_depth']}",
        f"平均并行度: {stats['avg_parallelism']:.2f}"
    ]

    return "\n".join(summary_parts)
