#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp_flowkit - 现代化的工作流执行库

这是原版 edp_flowkit 的重写版本，保持核心功能的同时引入现代化改进。

核心功能：
- 步骤依赖管理
- 工作流图构建和验证
- 灵活的依赖加载
- 工具步骤注册

现代化改进：
- 简化的依赖语法
- 灵活的工具选择机制
- 分离关注点：图逻辑与执行逻辑分离
- 完整的类型提示
"""

__version__ = '2.0.0'

# 核心类导入
from .core.graph import Graph, Dependency
from .core.step import Step, StepStatus, StepResult
from .core.runner import Runner, LocalRunner, LSFRunner
from .core.executor import Executor, ExecutionReport, default_judge
from .core.state_store import StateStore

# 加载器导入
from .loader.workflow_builder import WorkflowBuilder, ExecutableWorkflow
from .loader.step_loader import StepRegistry, load_tools_from_flow_path
from .loader.dependency_loader import DependencyLoader, DependencyParser

# 工具函数导入
from .utils.graph_utils import (
    GraphAnalyzer,
    GraphValidator,
    GraphOptimizer,
    GraphVisualizer,
    find_shortest_path,
    get_graph_summary,
)

__all__ = [
    # 核心类
    'Graph',
    'Dependency',
    'Step',
    'StepStatus',
    'StepResult',
    'Runner',
    'LocalRunner',
    'LSFRunner',
    'Executor',
    'ExecutionReport',
    'default_judge',
    'StateStore',

    # 加载器
    'WorkflowBuilder',
    'ExecutableWorkflow',
    'StepRegistry',
    'load_tools_from_flow_path',
    'DependencyLoader',
    'DependencyParser',

    # 工具类
    'GraphAnalyzer',
    'GraphValidator',
    'GraphOptimizer',
    'GraphVisualizer',
    'find_shortest_path',
    'get_graph_summary',
]
