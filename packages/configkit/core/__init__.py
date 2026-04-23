#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 核心模块

提供配置管理的核心功能：字典操作、值转换和 Tcl 桥接。
"""

from .dict_ops import DictOperations, merge_dict, yamlfiles2dict, files2dict
from .value_converter import ValueConverter
from .tcl_bridge import TclBridge

__all__ = [
    # 字典操作
    'DictOperations',
    'merge_dict',
    'yamlfiles2dict',
    'files2dict',

    # 值转换器
    'ValueConverter',

    # Tcl 桥接器
    'TclBridge',
]
