#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit Tcl 文件输出模块。

将多个 YAML/Tcl 配置文件按覆盖链合成为单个 Tcl 文件，
并标注各文件间的变量覆盖关系（[override] / [new]）。
"""

import logging
import re
from pathlib import Path
from tkinter import Tcl
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 共享工具函数
# ---------------------------------------------------------------------------

def _build_tcl_key(parent_keys: List[str], key: str) -> str:
    """将层级 key 路径构建为 Tcl 数组键名。

    Examples:
        _build_tcl_key([], 'cpu_num')          → 'cpu_num'
        _build_tcl_key(['pv_calibre'], 'lsf')  → 'pv_calibre(lsf)'
        _build_tcl_key(['pv_calibre', 'lsf'], 'cpu_num') → 'pv_calibre(lsf,cpu_num)'
    """
    if parent_keys:
        return f"{parent_keys[0]}({','.join(parent_keys[1:] + [key])})"
    return key


def _tcl_quote_element(value: str) -> str:
    """将字符串安全地作为 Tcl list 元素，用花括号保护含空格或特殊字符的值。"""
    if not value or re.search(r'[ \t\n\r{}[\]"\\$]', value):
        return "{" + value + "}"
    return value


# ---------------------------------------------------------------------------
# dict 展平
# ---------------------------------------------------------------------------

def _flatten_dict(data: Dict[str, Any],
                  parent_keys: Optional[List[str]] = None) -> List[Tuple[str, Any]]:
    """将嵌套字典递归展平为 (tcl_key, python_value) 列表。

    返回的 value 保持 Python 原生类型，由调用方负责编码为 Tcl 字符串。
    """
    parent_keys = parent_keys or []
    result: List[Tuple[str, Any]] = []

    for key, value in data.items():
        if isinstance(value, dict):
            result.extend(_flatten_dict(value, parent_keys + [key]))
        elif isinstance(value, list):
            for i, elem in enumerate(value):
                if isinstance(elem, dict):
                    full_key = ".".join(parent_keys + [key])
                    raise ValueError(
                        f"Unsupported value at '{full_key}[{i}]': "
                        "list elements must be scalars, not dicts. "
                        "Use a nested mapping instead."
                    )
            result.append((_build_tcl_key(parent_keys, key), value))
        else:
            result.append((_build_tcl_key(parent_keys, key), value))

    return result


# ---------------------------------------------------------------------------
# Python 值 → Tcl 写出格式
# ---------------------------------------------------------------------------

def _encode_value(py_value: Any, expand_fn=None) -> Tuple[str, bool]:
    """将 Python 值转换为 (tcl_str, is_command) 对。

    is_command=True  → 写成 ``set key tcl_str``      (如 [list ...])
    is_command=False → 写成 ``set key {tcl_str}``    (普通字符串/数值)
    """
    if py_value is None:
        return "", False

    if isinstance(py_value, bool):
        return ("1" if py_value else "0"), False

    if isinstance(py_value, (int, float)):
        return str(py_value), False

    if isinstance(py_value, list):
        elements = " ".join(_tcl_quote_element(str(v)) for v in py_value)
        return f"[list {elements}]", True

    # 字符串：支持 $var 引用展开
    str_val = str(py_value)
    if expand_fn is not None:
        str_val = expand_fn(str_val)
    return str_val, False


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def files_to_tcl(*input_files: Union[str, Path],
                 output_file: Union[str, Path],
                 edp_vars: Optional[Dict[str, str]] = None) -> Path:
    """将多个 YAML/Tcl 配置文件按覆盖链合成为单个 Tcl 文件。

    处理规则：
    - 后面的文件覆盖前面文件的变量，并标注 ``[override]``。
    - 后面的文件新增变量标注 ``[new]``。
    - YAML 中的 ``$var`` 引用在合成时展开（基于已处理文件的变量状态）。
    - bool 类型编码为 Tcl 惯例的 ``1``/``0``。
    - list 类型编码为 Tcl ``[list ...]`` 命令（非字面字符串）。
    """
    interp = Tcl()
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if edp_vars:
        for key, value in edp_vars.items():
            interp.eval(f"set edp({key}) {{{value}}}")

    # --- 内部辅助 ---

    def _get_interp_var(var_name: str) -> str:
        try:
            return interp.eval(f"set {var_name}")
        except Exception:
            return ""

    def _expand_refs(value: str) -> str:
        """将值中的 $var(key) 和 $var 引用替换为 interp 中的当前值。"""
        def _sub_array(m):
            val = _get_interp_var(m.group(1))
            return val if val else m.group(0)

        def _sub_simple(m):
            val = _get_interp_var(m.group(1))
            return val if val else m.group(0)

        result = re.sub(r"\$(\w+\([^)]+\))", _sub_array, value)
        result = re.sub(r"\$(\w+)", _sub_simple, result)
        return result

    def _var_exists(tcl_key: str) -> bool:
        try:
            return interp.eval(f"info exists {tcl_key}") == "1"
        except Exception:
            return False

    def _get_var(tcl_key: str) -> str:
        try:
            return interp.eval(f"set {tcl_key}")
        except Exception:
            return ""

    def _set_interp(tcl_key: str, tcl_str: str, is_command: bool) -> None:
        if is_command:
            interp.eval(f"set {tcl_key} {tcl_str}")
        else:
            interp.eval(f"set {tcl_key} {{{tcl_str}}}")

    # --- 写出 ---

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("# Generated by ConfigKit\n")
        out.write(f"# Input files: {len(input_files)}\n")

        if edp_vars:
            out.write("\n# --- framework variables ---\n")
            for key, value in edp_vars.items():
                out.write(f"set edp({key}) {{{value}}}\n")

        out.write("\n")

        for file_idx, input_file in enumerate(input_files):
            file_path = Path(input_file)
            if not file_path.exists():
                logger.warning("files_to_tcl: input file not found, skipping: %s", file_path)
                continue

            out.write(f"# --- source from: {file_path.resolve()} ---\n")
            ext = file_path.suffix.lower()

            if ext in (".yaml", ".yml"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                entries = _flatten_dict(data)
                for tcl_key, py_value in entries:
                    # 仅对字符串做 $var 展开；bool/int/list 不需要
                    expand = _expand_refs if isinstance(py_value, str) else None
                    tcl_str, is_command = _encode_value(py_value, expand_fn=expand)

                    mark = ""
                    if file_idx > 0:
                        if _var_exists(tcl_key):
                            old_val = _get_var(tcl_key)
                            current_repr = tcl_str if is_command else tcl_str
                            if old_val != current_repr:
                                mark = f"   # [override] was {{{old_val}}}"
                        else:
                            mark = "   # [new]"

                    if is_command:
                        out.write(f"set {tcl_key} {tcl_str}{mark}\n")
                    else:
                        out.write(f"set {tcl_key} {{{tcl_str}}}{mark}\n")

                    _set_interp(tcl_key, tcl_str, is_command)

                out.write("\n")

            elif ext in (".tcl", ".tk"):
                content = file_path.read_text(encoding="utf-8")
                interp.eval(f"source {{{file_path.resolve()}}}")
                out.write(content)
                if not content.endswith("\n"):
                    out.write("\n")
                out.write("\n")

    return output_path
