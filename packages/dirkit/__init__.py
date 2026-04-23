#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit - 目录管理模块

负责项目环境初始化和工作路径管理。
"""

__version__ = '2.0.0'

from .dirkit import DirKit
from .initializer import ProjectInitializer
from .project_finder import ProjectFinder
from .branch_linker import BranchLinker, parse_branch_step, save_branch_source, load_branch_source
from .work_path import WorkPathInitializer, get_current_user

__all__ = [
    # 基础操作
    'DirKit',

    # 初始化器
    'ProjectInitializer',
    'WorkPathInitializer',

    # 项目查找
    'ProjectFinder',

    # 分支操作
    'BranchLinker',
    'parse_branch_step',
    'save_branch_source',
    'load_branch_source',

    # 工具
    'get_current_user',
]
