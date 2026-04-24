#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit Tcl 桥接器模块

提供 Python 字典和 Tcl 解释器之间的双向转换功能。
这是原版 edp_configkit 的核心功能，负责：
1. Python 字典 ↔ Tcl 解释器转换
2. 类型信息保持
3. 变量引用展开
4. 文件格式转换

现代化改进：
1. 更好的内存管理
2. 优化的性能
3. 增强的错误处理
4. 面向对象设计
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from tkinter import Tcl

from ..types import ConfigDict, ConversionMode, ValueType, TclInterpreter
from ..exceptions import TclError, ConversionError, FileError
from .value_converter import ValueConverter


class TclBridge:
    """Python 和 Tcl 之间的桥接器

    提供双向转换和变量引用展开功能。
    """

    # 类型信息数组名称
    TYPE_ARRAY_NAME = "__configkit_types__"
    _SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self,
                 interp: Optional[Tcl] = None,
                 value_converter: Optional[ValueConverter] = None):
        """初始化 Tcl 桥接器

        Args:
            interp: 可选的 Tcl 解释器实例
            value_converter: 可选的值转换器实例
        """
        self.interp = interp if interp is not None else Tcl()
        self.value_converter = value_converter if value_converter is not None else ValueConverter()
        self._type_info_enabled = True

    def dict_to_interp(self, data: Dict[str, Any],
                       interp: Optional[Tcl] = None) -> Tcl:
        """将 Python 字典转换为 Tcl 解释器

        同时记录类型信息以便正确转换回 Python。

        Args:
            data: 要转换的字典
            interp: 可选的 Tcl 解释器，如果为 None 则使用 self.interp

        Returns:
            包含字典数据的 Tcl 解释器

        Examples:
            >>> bridge = TclBridge()
            >>> data = {'server': {'host': 'localhost', 'port': 8080}}
            >>> interp = bridge.dict_to_interp(data)
            >>> interp.eval('set server(host)')
            'localhost'
        """
        target_interp = interp if interp is not None else self.interp

        # 初始化类型信息数组
        if self._type_info_enabled:
            target_interp.eval(f"array set {self.TYPE_ARRAY_NAME} {{}}")

        # 递归设置变量
        self._set_dict_variables(target_interp, data, [])

        return target_interp

    def interp_to_dict(self,
                       interp: Optional[Tcl] = None,
                       mode: ConversionMode = ConversionMode.AUTO) -> Dict[str, Any]:
        """将 Tcl 解释器转换为 Python 字典

        利用保存的类型信息正确转换类型。

        Args:
            interp: 可选的 Tcl 解释器
            mode: 转换模式

        Returns:
            Python 字典
        """
        from . import type_conversion

        target_interp = interp if interp is not None else self.interp

        # 检查是否有类型信息
        has_type_info = self._has_type_info(target_interp)

        result = {}
        all_vars = target_interp.eval("info vars").split()

        # Tcl 内置变量，需要跳过
        tcl_builtin_vars = {
            'tcl_version', 'tcl_patchLevel', 'tcl_platform',
            'argv', 'argc', 'argv0', 'tcl_interactive',
            'errorCode', 'errorInfo', 'tcl_pkgPath',
            'auto_path', 'env', 'tcl_library', 'tcl_defaultExtension'
        }

        processed_arrays = set()

        for var_name in all_vars:
            # 跳过类型信息数组和 Tcl 内置变量
            if var_name == self.TYPE_ARRAY_NAME or var_name in tcl_builtin_vars:
                continue

            # 检查是否是数组
            try:
                is_array = target_interp.eval(f"array exists {var_name}") == "1"
            except Exception:
                # 如果无法检查是否为数组，跳过这个变量
                continue

            if is_array:
                # 处理数组变量，但避免重复处理
                if var_name not in processed_arrays:
                    try:
                        result[var_name] = self._convert_array(target_interp, var_name,
                                                              has_type_info, mode)
                        processed_arrays.add(var_name)
                    except Exception:
                        # 如果转换失败，跳过这个数组
                        continue
            else:
                # 处理简单变量
                try:
                    result[var_name] = self._convert_variable(target_interp, var_name,
                                                             has_type_info, None, mode)
                except Exception:
                    # 如果转换失败，跳过这个变量
                    continue

        return result

    def merge_and_expand(self,
                        base_dict: Dict[str, Any],
                        new_dict: Dict[str, Any]) -> Dict[str, Any]:
        """合并字典并展开变量引用

        Args:
            base_dict: 基础字典（包含已定义的变量）
            new_dict: 新字典（可能包含变量引用）

        Returns:
            合并并展开变量引用后的字典
        """
        # 将基础字典转换到 Tcl 解释器
        self.dict_to_interp(base_dict)

        # 添加新字典到解释器
        self.dict_to_interp(new_dict)

        # 展开变量引用
        self.expand_variables()

        # 转换回字典
        return self.interp_to_dict()

    def expand_variables(self, interp: Optional[Tcl] = None) -> None:
        """展开 Tcl 解释器中的变量引用

        Args:
            interp: 可选的 Tcl 解释器
        """
        target_interp = interp if interp is not None else self.interp
        self._expand_all_variables(target_interp)

    def load_tcl_file(self,
                      file_path: Union[str, Path],
                      mode: ConversionMode = ConversionMode.AUTO) -> Dict[str, Any]:
        """加载 Tcl 文件到字典

        Args:
            file_path: Tcl 文件路径
            mode: 转换模式

        Returns:
            Python 字典
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileError(
                f"Tcl file not found: {file_path}",
                file_path=file_path
            )

        # 创建新的解释器并加载文件
        temp_interp = Tcl()
        try:
            temp_interp.eval(f"source {{{file_path}}}")
            return self.interp_to_dict(temp_interp, mode)
        except Exception as e:
            raise TclError(
                f"Failed to load Tcl file: {str(e)}",
                tcl_command=f"source {{{file_path}}}",
                context={'file_path': str(file_path), 'original_error': str(e)}
            )

    def save_tcl_file(self,
                      interp: Optional[Tcl] = None,
                      output_file: Union[str, Path] = None) -> None:
        """保存 Tcl 解释器到文件

        Args:
            interp: 可选的 Tcl 解释器
            output_file: 输出文件路径
        """
        target_interp = interp if interp is not None else self.interp
        output_path = Path(output_file)

        # 获取所有变量
        all_vars = target_interp.eval("info vars").split()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Generated by ConfigKit\n\n")

            for var_name in all_vars:
                if var_name == self.TYPE_ARRAY_NAME:
                    continue

                # 检查是否是数组
                is_array = target_interp.eval(f"array exists {var_name}") == "1"

                if is_array:
                    # 写入数组元素
                    self._write_array_to_file(target_interp, f, var_name)
                else:
                    # 写入简单变量
                    self._write_variable_to_file(target_interp, f, var_name)

    # 私有方法

    def _set_dict_variables(self,
                           interp: Tcl,
                           data: Dict[str, Any],
                           parent_keys: List[str]) -> None:
        """递归设置字典变量到 Tcl 解释器"""
        for key, value in data.items():
            self._validate_tcl_segment(key)
            if isinstance(value, dict):
                # 递归处理嵌套字典
                # 对于 {'server': {'host': 'localhost'}}，我们希望：
                # 第一次：key='server', value={'host': 'localhost'}, parent_keys=[]
                # 递归：key='server', value={'host': 'localhost'}, parent_keys=[]
                #       然后内部处理：key='host', value='localhost', parent_keys=['server']
                self._set_dict_variables(interp, value, parent_keys + [key])
            elif isinstance(value, list):
                # 处理列表
                self._set_list_variable(interp, key, value, parent_keys)
            else:
                # 处理简单值
                if parent_keys:
                    # 嵌套变量：设置 server(host) = "localhost"
                    # 这里key是'host'，parent_keys是['server']
                    top_key = parent_keys[0]  # 'server'
                    nested_keys = parent_keys[1:] + [key]  # ['host']
                    self._validate_tcl_segment(top_key)
                    for nested_key in nested_keys:
                        self._validate_tcl_segment(nested_key)
                    array_indices = ','.join(nested_keys)  # 'host'
                    tcl_value = self.value_converter.py_to_tcl(value)
                    interp.eval(f"set {top_key}({array_indices}) {tcl_value}")

                    # 记录类型信息
                    if self._type_info_enabled:
                        type_key = f"{top_key}({array_indices})"
                        if isinstance(value, bool):
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) bool")
                        elif value is None:
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) none")
                        elif isinstance(value, (int, float)):
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) number")
                        else:
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) string")
                else:
                    # 顶层变量：enabled = "1"
                    self._validate_tcl_segment(key)
                    tcl_value = self.value_converter.py_to_tcl(value)
                    interp.eval(f"set {key} {tcl_value}")

                    # 记录类型信息
                    if self._type_info_enabled:
                        if isinstance(value, bool):
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({key}) bool")
                        elif value is None:
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({key}) none")
                        elif isinstance(value, (int, float)):
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({key}) number")
                        else:
                            interp.eval(f"set {self.TYPE_ARRAY_NAME}({key}) string")

    def _set_list_variable(self,
                          interp: Tcl,
                          key: str,
                          value: List[Any],
                          parent_keys: List[str]) -> None:
        """设置列表变量"""
        self._validate_tcl_segment(key)
        if parent_keys:
            # 嵌套列表：server(ports) = [list 80 443 8080]
            top_key = parent_keys[0]
            nested_keys = parent_keys[1:] + [key]
            self._validate_tcl_segment(top_key)
            for nested_key in nested_keys:
                self._validate_tcl_segment(nested_key)
            array_indices = ','.join(nested_keys)
            type_key = f"{top_key}({array_indices})"
        else:
            # 顶层列表：ports = [list 80 443 8080]
            top_key = key
            array_indices = None
            type_key = key

        # 记录这是列表类型
        if self._type_info_enabled:
            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) list")

        # 转换列表元素为 Tcl 格式
        tcl_elements = []
        for i, item in enumerate(value):
            # 记录每个元素的类型
            if self._type_info_enabled:
                element_type_key = f"{type_key},{i}"
                self._record_element_type(interp, element_type_key, item)

            # 转换元素
            tcl_elements.append(self.value_converter.py_to_tcl(item))

        # 设置列表值
        tcl_value = f"[list {' '.join(tcl_elements)}]"

        if parent_keys:
            # 数组变量：server(ports) = [list 80 443 8080]
            interp.eval(f"set {top_key}({array_indices}) {tcl_value}")
        else:
            # 简单变量：ports = [list 80 443 8080]
            interp.eval(f"set {top_key} {tcl_value}")

    def _record_element_type(self, interp: Tcl, type_key: str, item: Any) -> None:
        """记录列表元素的类型信息"""
        if isinstance(item, bool):
            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) bool")
        elif item is None:
            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) none")
        elif isinstance(item, (int, float)):
            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) number")
        elif isinstance(item, list):
            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) list")
        else:
            interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key}) string")

    def _validate_tcl_segment(self, segment: str) -> None:
        """校验 Tcl 变量名片段，避免命令注入。"""
        if not isinstance(segment, str) or not segment:
            raise ConversionError("Invalid Tcl variable segment: empty or non-string")
        if not self._SAFE_SEGMENT_PATTERN.fullmatch(segment):
            raise ConversionError(
                f"Invalid Tcl variable segment '{segment}'. "
                "Only letters, digits, '_', '-', '.' are allowed."
            )

    def _get_type_key(self, key: str, parent_keys: List[str]) -> str:
        """获取类型信息的键名"""
        if parent_keys:
            return f"{key}({','.join(parent_keys)})"
        return key

    def _has_type_info(self, interp: Tcl) -> bool:
        """检查解释器是否有类型信息"""
        try:
            interp.eval(f"info exists {self.TYPE_ARRAY_NAME}")
            return interp.eval(f"info exists {self.TYPE_ARRAY_NAME}") == "1"
        except Exception:
            return False

    def _convert_variable(self,
                         interp: Tcl,
                         var_name: str,
                         has_type_info: bool,
                         index: Optional[str],
                         mode: ConversionMode) -> Any:
        """转换单个变量"""
        from . import type_conversion

        # 获取类型
        if has_type_info:
            type_key = var_name
            if index is not None:
                type_key = f"{var_name}({index})"

            try:
                var_type = interp.eval(f"set {self.TYPE_ARRAY_NAME}({type_key})")
                return type_conversion.convert_value(interp, var_name, var_type, index, has_type_info)
            except Exception:
                # 获取类型失败，使用默认转换
                pass

        # 默认转换
        if index is None:
            value_str = interp.eval(f"set {var_name}")
        else:
            value_str = interp.eval(f"set {var_name}({index})")
        return self.value_converter.tcl_to_py(value_str, mode)

    def _convert_array(self,
                      interp: Tcl,
                      var_name: str,
                      has_type_info: bool,
                      mode: ConversionMode) -> Dict[str, Any]:
        """转换数组变量"""
        # 获取数组元素
        try:
            array_elements = interp.eval(f"array names {var_name}").split()
        except Exception:
            return {}

        result = {}
        for element in array_elements:
            try:
                # 获取数组元素的值
                value_str = interp.eval(f"set {var_name}({element})")

                # 检查这个元素是否有类型信息
                element_type = "unknown"
                if has_type_info:
                    try:
                        element_type = interp.eval(f"set {self.TYPE_ARRAY_NAME}({var_name},{element})")
                    except Exception:
                        pass

                # 根据类型转换值
                if element_type == "bool":
                    value = value_str == "1" or value_str.lower() == "true"
                elif element_type == "none":
                    value = None
                elif element_type == "number":
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                    except ValueError:
                        value = value_str
                else:
                    # 使用默认转换
                    value = self.value_converter.tcl_to_py(value_str, mode)

                # 设置到结果字典中
                result[element] = value

            except Exception:
                # 如果单个元素转换失败，跳过
                continue

        return result

    def _expand_all_variables(self, interp: Tcl) -> None:
        """展开所有变量引用"""
        all_vars = interp.eval("info vars").split()

        for var_name in all_vars:
            if var_name == self.TYPE_ARRAY_NAME:
                continue

            # 检查是否是数组
            is_array = interp.eval(f"array exists {var_name}") == "1"

            if is_array:
                self._expand_array_variables(interp, var_name)
            else:
                self._expand_simple_variable(interp, var_name)

    def _expand_simple_variable(self, interp: Tcl, var_name: str) -> None:
        """展开简单变量的引用"""
        try:
            current_value = interp.eval(f"set {var_name}")
            # 使用 subst 命令展开变量引用
            expanded_value = interp.eval(f"subst {{{current_value}}}")
            if expanded_value != current_value:
                interp.eval(f"set {var_name} {{{expanded_value}}}")
        except Exception:
            # 展开失败，保持原值
            pass

    def _expand_array_variables(self, interp: Tcl, var_name: str) -> None:
        """展开数组变量的引用"""
        array_elements = interp.eval(f"array names {var_name}").split()

        for element in array_elements:
            try:
                current_value = interp.eval(f"set {var_name}({element})")
                expanded_value = interp.eval(f"subst {{{current_value}}}")
                if expanded_value != current_value:
                    interp.eval(f"set {var_name}({element}) {{{expanded_value}}}")
            except Exception:
                # 展开失败，保持原值
                pass

    def _write_variable_to_file(self, interp: Tcl, file, var_name: str) -> None:
        """写入简单变量到文件"""
        value = interp.eval(f"set {var_name}")
        file.write(f"set {var_name} {{{value}}}\n")

    def _write_array_to_file(self, interp: Tcl, file, var_name: str) -> None:
        """写入数组变量到文件"""
        array_elements = interp.eval(f"array names {var_name}").split()

        for element in array_elements:
            value = interp.eval(f"set {var_name}({element})")
            file.write(f"set {var_name}({element}) {{{value}}}\n")
