#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit graph_utils 测试
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flowkit.core import Graph, Step
from flowkit.utils.graph_utils import GraphOptimizer


class TestGraphOptimizer(unittest.TestCase):
    """测试传递依赖简化正确性"""

    def _build_graph(self) -> Graph:
        graph = Graph()
        for sid in ("a", "b", "c", "d"):
            graph.add_step(Step(id=sid, name=sid, tool_name="mock"))
        return graph

    def test_transitive_reduction_removes_only_redundant_edge(self):
        """A->B->C 且 A->C 时，只删除 A->C。"""
        graph = self._build_graph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")
        graph.add_dependency("a", "c")

        stats = GraphOptimizer.optimize_dependencies(graph, "transitive_reduction")

        deps = {(d.from_step, d.to_step) for d in graph.dependencies}
        self.assertIn(("a", "b"), deps)
        self.assertIn(("b", "c"), deps)
        self.assertNotIn(("a", "c"), deps)
        self.assertEqual(stats["reduction_count"], 1)

    def test_transitive_reduction_keeps_non_redundant_chain_edges(self):
        """A->B->C 没有 A->C 时，不应删除任何边。"""
        graph = self._build_graph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")

        stats = GraphOptimizer.optimize_dependencies(graph, "transitive_reduction")

        deps = {(d.from_step, d.to_step) for d in graph.dependencies}
        self.assertEqual(deps, {("a", "b"), ("b", "c")})
        self.assertEqual(stats["reduction_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
