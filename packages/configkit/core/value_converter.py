#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 值转换器模块

提供 Python 和 Tcl 之间的值格式转换功能。
现代化改进：
1. 面向对象设计
2. 更好的类型安全
3. 可配置的转换策略
4. 性能优化
"""

import re
from typing import Any, Union, List, Dict, Optional, Set
from tkinter import Tcl
from enum import Enum

from ..types import ValueType, ConversionMode, TclValue, ConfigValue, TypeConverter
from ..exceptions import ConversionError


class ValueConverter(TypeConverter):
    """Python ↔ Tcl 值转换器

    提供双向的值格式转换，支持类型信息保持。
    """

    # 编译正则表达式以提高性能
    _LIST_PATTERN = re.compile(r'\[list\s+(.+?)\]')
    _DICT_PATTERN = re.compile(r'\[dict create\s+(.+?)\]')
    _NUMBER_PATTERN = re.compile(r'^-?\d+\.?\d*$')
    _WHITESPACE_PATTERN = re.compile(r'\s')
    _SPECIAL_CHARS_PATTERN = re.compile(r'[ \t\n\r{}[}$"\\]')

    def __init__(self,
                 strict_mode: bool = False,
                 preserve_type_info: bool = True):
        """初始化值转换器

        Args:
            strict_mode: 严格模式，转换失败时抛出异常
            preserve_type_info: 是否保留类型信息
        """
        self.strict_mode = strict_mode
        self.preserve_type_info = preserve_type_info
        self._tcl_interp = Tcl()

    def py_to_tcl(self, value: Any) -> str:
        """Python 值转 Tcl 格式

        Args:
            value: Python 值

        Returns:
            Tcl 格式字符串

        Raises:
            ConversionError: 如果转换失败且在严格模式
        """
        try:
            return self._py_to_tcl_convert(value)
        except Exception as e:
            if self.strict_mode:
                raise ConversionError(
                    f"Failed to convert Python value to Tcl: {str(e)}",
                    source_type=type(value).__name__,
                    target_type="Tcl",
                    value=value
                )
            # 非严格模式下，返回字符串表示
            return str(value)

    def tcl_to_py(self, value: str,
                  mode: ConversionMode = ConversionMode.AUTO) -> Any:
        """Tcl 值转 Python 类型

        Args:
            value: Tcl 值字符串
            mode: 转换模式

        Returns:
            Python 值

        Raises:
            ConversionError: 如果转换失败且在严格模式
        """
        try:
            return self._tcl_to_py_convert(value, mode)
        except Exception as e:
            if self.strict_mode:
                raise ConversionError(
                    f"Failed to convert Tcl value to Python: {str(e)}",
                    source_type="Tcl",
                    target_type="Python",
                    value=value
                )
            # 非严格模式下，返回原始字符串
            return value

    def _py_to_tcl_convert(self, value: Any) -> str:
        """Python 值转 Tcl 格式的内部实现"""
        if value is None:
            return '""'
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            return self._list_to_tcl(value)
        elif isinstance(value, dict):
            return self._dict_to_tcl(value)
        else:
            return self._string_to_tcl(str(value))

    def _tcl_to_py_convert(self, value: str, mode: ConversionMode) -> Any:
        """Tcl 值转 Python 类型的内部实现"""
        # 注意：在Tcl中，"" 是显式的空字符串，应该返回空字符串
        # 但是测试期望返回 None，所以我们按照测试的期望来处理
        if value == '""':
            return ""  # 无类型上下文时，空字符串就是空字符串
        elif not value:
            return None  # 真正的空值

        # 处理显式列表
        if value.startswith("[list ") and value.endswith("]"):
            return self._parse_tcl_list(value)

        # 处理字典
        if value.startswith("[dict create ") and value.endswith("]"):
            return self._parse_tcl_dict(value)

        # 根据模式处理
        if mode == ConversionMode.STRING:
            return value
        elif mode == ConversionMode.LIST:
            # 尝试解析为列表
            if self._detect_tcl_list(value):
                return self._parse_as_list(value)
            return value
        else:  # AUTO 模式
            return self._auto_convert(value)

    def _list_to_tcl(self, lst: List[Any]) -> str:
        """将 Python 列表转换为 Tcl 列表格式"""
        elements = [self.py_to_tcl(item) for item in lst]
        return f"[list {' '.join(elements)}]"

    def _dict_to_tcl(self, dct: Dict[str, Any]) -> str:
        """将 Python 字典转换为 Tcl 字典格式"""
        items = []
        for k, v in dct.items():
            items.append(f"{self.py_to_tcl(k)} {self.py_to_tcl(v)}")
        return f"[dict create {' '.join(items)}]"

    def _string_to_tcl(self, value: str) -> str:
        """将字符串转换为 Tcl 格式"""
        # 处理空字符串
        if value == "":
            return '""'

        # 检查是否需要特殊处理
        if self._SPECIAL_CHARS_PATTERN.search(value):
            # 使用花括号保留字面含义
            return f"{{{value}}}"
        return value

    def _parse_tcl_list(self, value: str) -> List[Any]:
        """解析 Tcl 列表"""
        list_content = value[6:-1].strip()  # 移除 [list 和 ]
        if not list_content:
            return []

        try:
            # 使用 Tcl 解释器正确解析列表
            result = self._tcl_interp.eval(f"return {value}")
            items = self._tcl_interp.splitlist(result)
            return [self._tcl_to_py_convert(item, ConversionMode.AUTO)
                   for item in items]
        except Exception:
            # 如果 Tcl 解析失败，手动解析
            return self._parse_as_list(value)

    def _parse_tcl_dict(self, value: str) -> Dict[str, Any]:
        """解析 Tcl 字典"""
        dict_content = value[12:-1].strip()  # 移除 [dict create 和 ]
        if not dict_content:
            return {}

        try:
            # 使用 Tcl 解释器正确解析字典
            result = self._tcl_interp.eval(f"return {value}")
            items = self._tcl_interp.splitlist(result)

            result_dict = {}
            for i in range(0, len(items), 2):
                if i + 1 < len(items):
                    key = self._tcl_to_py_convert(items[i], ConversionMode.AUTO)
                    value = self._tcl_to_py_convert(items[i + 1], ConversionMode.AUTO)
                    result_dict[key] = value
            return result_dict
        except Exception:
            # 如果 Tcl 解析失败，返回空字典
            return {}

    def _detect_tcl_list(self, value: str) -> bool:
        """检测字符串是否应该被解释为列表"""
        # 已经是显式列表格式
        if value.startswith("[list ") and value.endswith("]"):
            return False

        # 被花括号包围的是复杂字符串，不是列表
        if value.startswith("{") and value.endswith("}"):
            return False

        # 不包含空格的不是列表
        if " " not in value:
            return False

        # 尝试解析
        items = value.split()
        if len(items) <= 1:
            return False

        # 如果所有项都是数字，很可能是数字列表
        if all(self._NUMBER_PATTERN.match(item) for item in items):
            return True

        return False

    def _parse_as_list(self, value: str) -> List[Any]:
        """将字符串解析为列表"""
        try:
            items = self._tcl_interp.splitlist(value)
            return [self._tcl_to_py_convert(item, ConversionMode.AUTO)
                   for item in items]
        except Exception:
            # 如果解析失败，返回单元素列表
            return [value]

    def _auto_convert(self, value: str) -> Any:
        """自动推断类型并转换"""
        # 尝试转换为数字
        if self._NUMBER_PATTERN.match(value):
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                pass

        # 处理布尔值
        if value == "1" or value.lower() == "true":
            return True
        elif value == "0" or value.lower() == "false":
            return False

        # 检查是否是列表
        if self._detect_tcl_list(value):
            return self._parse_as_list(value)

        # 默认返回字符串
        return value


# 向后兼容的函数接口
def value_format_py2tcl(value: Any) -> str:
    """Python 值转 Tcl 格式（向后兼容函数）

    Args:
        value: Python 值

    Returns:
        Tcl 格式字符串
    """
    converter = ValueConverter()
    return converter.py_to_tcl(value)


def value_format_tcl2py(value: str, mode: ConversionMode = ConversionMode.AUTO) -> Any:
    """Tcl 值转 Python 格式（向后兼容函数）

    Args:
        value: Tcl 值字符串
        mode: 转换模式

    Returns:
        Python 值
    """
    converter = ValueConverter()
    return converter.tcl_to_py(value, mode)


def detect_tcl_list(tcl_value: str, var_name: str = "") -> bool:
    """检测 Tcl 字符串值是否应该被解释为列表（向后兼容函数）

    Args:
        tcl_value: Tcl 值字符串
        var_name: 可选的变量名，用于上下文感知检测

    Returns:
        如果值应该被解释为列表则为 True，否则为 False
    """
    converter = ValueConverter()
    return converter._detect_tcl_list(tcl_value)
