#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 类型转换模块

提供基于类型信息的值转换功能。
这是原版 edp_configkit 的核心功能，用于在 Tcl → Python 转换时保持类型信息。
"""

from typing import Any, Dict, Optional, List
from tkinter import Tcl

from ..types import ValueType
from ..exceptions import ConversionError
from .value_converter import ValueConverter


def get_var_type(interp: Tcl, var_name: str, idx: Optional[str] = None,
                has_type_info: bool = True) -> str:
    """从 Tcl 解释器中获取变量的类型信息

    Args:
        interp: Tcl 解释器
        var_name: 变量名
        idx: 可选的数组索引
        has_type_info: 是否有类型信息可用

    Returns:
        类型字符串: "bool", "none", "number", "list", "string", 或 "unknown"
    """
    if not has_type_info:
        return "unknown"

    type_array = "__configkit_types__"
    type_key = var_name if idx is None else f"{var_name}({idx})"

    try:
        return interp.eval(f"set {type_array}({type_key})")
    except Exception:
        return "unknown"


def convert_list_element(interp: Tcl, item: str, list_name: str,
                        index: int, has_type_info: bool) -> Any:
    """使用类型信息转换列表元素

    Args:
        interp: Tcl 解释器
        item: 列表元素字符串
        list_name: 列表变量名
        index: 元素在列表中的索引
        has_type_info: 是否有类型信息可用

    Returns:
        转换后的 Python 值
    """
    converter = ValueConverter()

    if has_type_info:
        try:
            # 使用逗号分隔格式: list_name,0, list_name,1 等
            element_type = interp.eval(f"set __configkit_types__({list_name},{index})")

            if element_type == "bool":
                return item == "1" or item.lower() == "true"
            elif element_type == "none":
                return None
            elif element_type == "number":
                try:
                    if '.' in item:
                        return float(item)
                    else:
                        return int(item)
                except ValueError:
                    return item
            elif element_type == "list":
                # 嵌套列表 - 需要解析并递归转换
                return _parse_nested_list(interp, item, list_name, index, has_type_info)
            else:
                return item
        except Exception:
            return item
    else:
        # 没有类型信息，使用默认转换
        return converter.tcl_to_py(item)


def _parse_nested_list(interp: Tcl, item: str, list_name: str,
                      parent_index: int, has_type_info: bool) -> List[Any]:
    """解析嵌套列表"""
    converter = ValueConverter()
    temp_interp = Tcl()

    try:
        # 尝试不同格式解析列表
        if item.startswith("[list ") and item.endswith("]"):
            result = temp_interp.eval(f"return {item}")
            parsed = temp_interp.splitlist(result)
        elif item.startswith("{") and item.endswith("}"):
            try:
                result = temp_interp.eval(f"return {item}")
                parsed = temp_interp.splitlist(result)
            except Exception:
                parsed = temp_interp.splitlist(item)
        else:
            parsed = temp_interp.splitlist(item)

        # 递归转换每个元素
        nested_list_name = f"{list_name},{parent_index}"
        return [convert_list_element(interp, elem, nested_list_name, i, has_type_info)
               for i, elem in enumerate(parsed)]

    except Exception:
        # 解析失败，返回单元素列表
        return [item]


def convert_value(interp: Tcl, var_name: str, var_type: str,
                 idx: Optional[str] = None, has_type_info: bool = True) -> Any:
    """基于类型信息转换值

    Args:
        interp: Tcl 解释器
        var_name: 变量名
        var_type: 变量类型
        idx: 可选的数组索引
        has_type_info: 是否有类型信息可用

    Returns:
        转换后的 Python 值
    """
    converter = ValueConverter()

    # 获取变量值
    try:
        if idx is None:
            value_str = interp.eval(f"set {var_name}")
        else:
            value_str = interp.eval(f"set {var_name}({idx})")
    except Exception:
        return None

    # 根据类型转换
    if not has_type_info or var_type == "unknown":
        return converter.tcl_to_py(value_str)

    if var_type == "bool":
        return value_str == "1" or value_str.lower() == "true"
    elif var_type == "none":
        return None
    elif var_type == "number":
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            return value_str
    elif var_type == "list":
        # 解析列表
        return _parse_typed_list(interp, value_str, var_name, has_type_info)
    elif var_type == "string":
        return value_str
    else:
        return converter.tcl_to_py(value_str)


def _parse_typed_list(interp: Tcl, value_str: str, list_name: str,
                     has_type_info: bool) -> List[Any]:
    """解析有类型信息的列表"""
    converter = ValueConverter()

    try:
        # 尝试解析为 Tcl 列表
        if value_str.startswith("[list ") and value_str.endswith("]"):
            result = interp.eval(f"return {value_str}")
            items = interp.splitlist(result)
        else:
            items = interp.splitlist(value_str)

        # 转换每个元素
        return [convert_list_element(interp, item, list_name, i, has_type_info)
               for i, item in enumerate(items)]

    except Exception:
        # 解析失败，尝试默认转换
        return [converter.tcl_to_py(value_str)]


# 向后兼容的辅助函数
def value_format_tcl2py_list_item(tcl_value: str) -> Any:
    """转换 Tcl 列表项为 Python 格式（向后兼容）

    在列表上下文中，{} 被视为空字符串，而不是 None。

    Args:
        tcl_value: Tcl 值字符串（来自列表）

    Returns:
        Python 表示的 Tcl 值
    """
    if tcl_value == '{}' or tcl_value == '""' or tcl_value == '':
        return ""

    converter = ValueConverter()
    return converter.tcl_to_py(tcl_value)
