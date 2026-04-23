#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cmdkit - 脚本生成模块

根据 flow 目录结构和覆盖链，为每个 step 生成可执行的 Tcl 脚本。
"""

__version__ = '2.0.0'

from .script_builder import ScriptBuilder

__all__ = [
    'ScriptBuilder',
]
