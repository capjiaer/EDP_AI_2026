#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit 核心功能测试

测试纯图逻辑功能，不涉及执行细节。
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flowkit.core import Graph, Step, StepStatus
from flowkit.loader import WorkflowBuilder, StepRegistry, create_workflow_from_yaml
from flowkit.utils import find_shortest_path, get_graph_summary


class TestGraph(unittest.TestCase):
    """测试图构建功能"""

    def test_simple_graph(self):
        """测试简单图构建"""
        graph = Graph()

        # 添加步骤
        graph.add_step(Step(id="a", name="Step A", cmd="echo A"))
        graph.add_step(Step(id="b", name="Step B", cmd="echo B"))
        graph.add_step(Step(id="c", name="Step C", cmd="echo C"))

        # 添加依赖
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")

        # 测试拓扑排序
        order = graph.get_topological_order()
        self.assertEqual(order, ["a", "b", "c"])

    def test_parallel_dependencies(self):
        """测试并行依赖"""
        graph = Graph()

        # 创建并行结构
        graph.add_step(Step(id="a", name="Step A", cmd="echo A"))
        graph.add_step(Step(id="b", name="Step B", cmd="echo B"))
        graph.add_step(Step(id="c", name="Step C", cmd="echo C"))
        graph.add_step(Step(id="d", name="Step D", cmd="echo D"))

        # a -> [b, c] 并行依赖
        graph.add_dependency("a", "b")
        graph.add_dependency("a", "c")

        # [b, c] -> d
        graph.add_dependency("b", "d")
        graph.add_dependency("c", "d")

        # 测试执行层级
        levels = graph.get_execution_levels()
        self.assertEqual(len(levels), 3)
        self.assertEqual(levels[0], ["a"])
        self.assertEqual(set(levels[1]), {"b", "c"})

    def test_weak_dependencies(self):
        """测试弱依赖"""
        graph = Graph()

        graph.add_step(Step("a", "Step A", "echo A"))
        graph.add_step(Step("b", "Step B", "echo B"))
        graph.add_step(Step("c", "Step C", "echo C"))

        # 强依赖
        graph.add_dependency("a", "b", weak=False)

        # 弱依赖
        graph.add_dependency("b", "c", weak=True)

        # 测试可执行性
        state = {
            "a": StepStatus.FINISHED,
            "b": StepStatus.FINISHED,
            "c": StepStatus.INIT
        }

        # b -> c 是弱依赖，c 应该可执行
        runnable = graph.get_runnable_steps(state)
        self.assertIn("c", runnable)

    def test_graph_validation(self):
        """测试图验证"""
        graph = Graph()

        graph.add_step(Step("a", "Step A", cmd="echo A"))
        graph.add_step(Step("b", "Step B", cmd="echo B"))

        # 正常依赖
        graph.add_dependency("a", "b")

        # 验证应该通过
        errors = graph.validate()
        self.assertEqual(len(errors), 0)

    def test_cycle_detection(self):
        """测试环检测"""
        graph = Graph()

        graph.add_step(Step("a", "Step A", cmd="echo A"))
        graph.add_step(Step("b", "Step B", cmd="echo B"))
        graph.add_step(Step("c", "Step C", cmd="echo C"))

        # 添加正常依赖
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")

        # 添加 c -> a 会形成环，应该抛出异常
        with self.assertRaises(ValueError):
            graph.add_dependency("c", "a")


class TestDependencyLoader(unittest.TestCase):
    """测试依赖加载器"""

    def test_load_simple_dependencies(self):
        """测试加载简单依赖"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""ipmerge: dummy
dummy: [drc, lvs, perc]
drc: final_signoff
lvs: final_signoff
perc: final_signoff
""")
            dep_file = f.name

        try:
            from flowkit.loader import DependencyLoader
            loader = DependencyLoader()
            graph = loader.load_from_file(Path(dep_file))

            # 验证步骤和依赖
            self.assertEqual(len(graph.steps), 6)
            self.assertEqual(len(graph.dependencies), 7)  # ipmerge->dummy, dummy->drc, dummy->lvs, dummy->perc, drc->final, lvs->final, perc->final

        finally:
            os.unlink(dep_file)

    def test_load_weak_dependencies(self):
        """测试加载弱依赖"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""ipmerge: dummy?
dummy: drc
dummy: lvs?
""")
            dep_file = f.name

        try:
            from flowkit.loader import DependencyLoader
            loader = DependencyLoader()
            graph = loader.load_from_file(Path(dep_file))

            # 验证弱依赖：只有 ipmerge->dummy 和 dummy->lvs 是弱依赖
            weak_deps = [dep for dep in graph.dependencies if dep.weak]
            self.assertEqual(len(weak_deps), 2)

        finally:
            os.unlink(dep_file)


class TestWorkflowBuilder(unittest.TestCase):
    """测试工作流构建器"""

    def test_create_simple_workflow(self):
        """测试创建简单工作流"""
        from flowkit.loader import WorkflowBuilder

        builder = WorkflowBuilder()

        # 模拟工具步骤（新格式）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""pv_calibre:
  supported_steps:
    ipmerge:
      sub_steps: [merge_sub1]
      invoke: []
    dummy:
      sub_steps: [dummy_sub1]
      invoke: []
    drc:
      sub_steps: [drc_sub1]
      invoke: []
""")
            tool_file = f.name

        # 模拟依赖关系
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""ipmerge: dummy
dummy: drc
""")
            dep_file = f.name

        try:
            # 注册工具步骤
            builder.step_registry.register_tool_steps(Path(tool_file))

            # 创建工作流
            workflow = builder.create_workflow(
                dependency_files=[Path(dep_file)],
                tool_selection={
                    'ipmerge': 'pv_calibre',
                    'dummy': 'pv_calibre',
                    'drc': 'pv_calibre'
                }
            )

            # 验证工作流
            self.assertEqual(len(workflow.steps), 3)
            self.assertTrue(workflow.validate()[0])
            # 验证 sub_steps
            self.assertEqual(workflow.get_step_sub_steps('ipmerge'), ['merge_sub1'])
            self.assertEqual(workflow.get_step_tool('drc'), 'pv_calibre')

        finally:
            os.unlink(tool_file)
            os.unlink(dep_file)

    def test_cross_domain_workflow(self):
        """测试跨域工作流"""
        from flowkit.loader import WorkflowBuilder

        builder = WorkflowBuilder()

        # 注册工具步骤（新格式）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""pv_calibre:
  supported_steps:
    ipmerge:
      sub_steps: [merge_sub1]
      invoke: []
    dummy:
      sub_steps: [dummy_sub1]
      invoke: []
    drc:
      sub_steps: [drc_sub1]
      invoke: []
    lvs:
      sub_steps: [lvs_sub1]
      invoke: []
    perc:
      sub_steps: [perc_sub1]
      invoke: []
""")
            tool_file = f.name

        # PR 领域依赖
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""place: cts
cts: route
route: postroute
postroute: ipmerge
""")
            pr_dep_file = f.name

        # PV 领域依赖
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""ipmerge: dummy
dummy: [drc, lvs, perc]
drc: final_signoff
lvs: final_signoff
perc: final_signoff
""")
            pv_dep_file = f.name

        try:
            # 注册工具步骤
            builder.step_registry.register_tool_steps(Path(tool_file))

            # 加载跨域依赖
            workflow = builder.create_workflow(
                dependency_files=[Path(pr_dep_file), Path(pv_dep_file)],
                tool_selection={'ipmerge': 'pv_calibre', 'dummy': 'pv_calibre', 'drc': 'pv_calibre',
                               'lvs': 'pv_calibre', 'perc': 'pv_calibre'}
            )

            # 验证跨域连接 - 检查依赖图中的所有步骤
            self.assertIn('ipmerge', workflow.graph.steps)
            self.assertIn('postroute', workflow.graph.steps)

            # 验证工作流包含选中的工具步骤
            self.assertIn('ipmerge', workflow.steps)
            self.assertIn('dummy', workflow.steps)

        finally:
            os.unlink(tool_file)
            os.unlink(pr_dep_file)
            os.unlink(pv_dep_file)


class TestGraphUtils(unittest.TestCase):
    """测试图工具函数"""

    def test_find_shortest_path(self):
        """测试最短路径查找"""
        from flowkit.core import Graph, Step, StepStatus

        graph = Graph()

        # 创建路径
        graph.add_step(Step("a", "A", "echo A"))
        graph.add_step(Step("b", "B", "echo B"))
        graph.add_step(Step("c", "C", "echo C"))
        graph.add_step(Step("d", "D", "echo D"))

        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")
        graph.add_dependency("a", "d")

        # 测试最短路径
        path = find_shortest_path(graph, "a", "c")
        self.assertEqual(path, ["a", "b", "c"])

    def test_graph_summary(self):
        """测试图摘要"""
        from flowkit.core import Graph, Step

        graph = Graph()

        # 添加一些步骤
        graph.add_step(Step("a", "A", "echo A"))
        graph.add_step(Step("b", "B", "echo B"))
        graph.add_step(Step("c", "C", "echo C"))

        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")

        # 获取摘要
        summary = get_graph_summary(graph)
        self.assertIn("工作流图摘要", summary)
        self.assertIn("总步骤数: 3", summary)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
