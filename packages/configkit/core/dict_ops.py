#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 字典操作模块

提供字典合并、配置文件加载等核心功能。
现代化改进：
1. 完整的类型提示
2. 更好的错误处理
3. 支持多种配置格式
4. 性能优化
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Union, List, Optional, Callable, TypeVar, overload
from functools import lru_cache

from ..exceptions import FileError, FileNotFoundError, ParseError
from ..types import ConfigDict, ConfigValue, MergeStrategy, ConversionMode
from .value_converter import ValueConverter


T = TypeVar('T', bound=Dict[str, Any])


class DictOperations:
    """字典操作类

    提供字典合并、配置加载等功能的面向对象接口。
    """

    def __init__(self,
                 list_merge_strategy: str = 'append',
                 type_converter: Optional[ValueConverter] = None):
        """初始化字典操作器

        Args:
            list_merge_strategy: 列表合并策略 ('append', 'replace', 'extend')
            type_converter: 类型转换器实例
        """
        self.list_merge_strategy = list_merge_strategy
        self.type_converter = type_converter or ValueConverter()

    def merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """合并两个字典

        Args:
            dict1: 第一个字典
            dict2: 第二个字典（会覆盖 dict1 中的值）

        Returns:
            合并后的字典
        """
        return merge_dict(dict1, dict2, list_merge_strategy=self.list_merge_strategy)

    def load_yaml(self, *file_paths: Union[str, Path],
                  expand_variables: bool = True) -> Dict[str, Any]:
        """加载 YAML 文件

        Args:
            *file_paths: 一个或多个 YAML 文件路径
            expand_variables: 是否展开变量引用

        Returns:
            合并后的配置字典

        Raises:
            FileNotFoundError: 文件不存在
            ParseError: YAML 解析错误
        """
        return yamlfiles2dict(*file_paths, expand_variables=expand_variables)

    def load_files(self, *file_paths: Union[str, Path],
                   mode: ConversionMode = ConversionMode.AUTO,
                   skip_errors: bool = False) -> Dict[str, Any]:
        """加载混合格式文件

        Args:
            *file_paths: 一个或多个配置文件路径（YAML 或 Tcl）
            mode: Tcl 值转换模式
            skip_errors: 是否跳过错误文件

        Returns:
            合并后的配置字典
        """
        return files2dict(*file_paths, mode=mode, skip_errors=skip_errors)

    def deep_merge(self, *dicts: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并多个字典

        Args:
            *dicts: 多个字典

        Returns:
            合并后的字典
        """
        result: Dict[str, Any] = {}
        for d in dicts:
            result = self.merge(result, d)
        return result


def merge_dict(dict1: Dict[str, Any],
               dict2: Dict[str, Any],
               list_merge_strategy: str = 'append') -> Dict[str, Any]:
    """递归合并两个字典

    如果有冲突，dict2 的值会覆盖 dict1 的值。
    对于列表，根据策略决定是追加还是替换。

    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        list_merge_strategy: 列表合并策略
            - 'append': 将 dict2 的列表项追加到 dict1 (默认)
            - 'replace': 用 dict2 的列表替换 dict1 的列表
            - 'extend': 类似 append，但会去重

    Returns:
        合并后的字典

    Examples:
        >>> dict1 = {'a': 1, 'b': {'c': 2}}
        >>> dict2 = {'b': {'d': 3}, 'e': 4}
        >>> merge_dict(dict1, dict2)
        {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}

        >>> dict1 = {'a': [1, 2]}
        >>> dict2 = {'a': [3, 4]}
        >>> merge_dict(dict1, dict2)
        {'a': [1, 2, 3, 4]}

        >>> merge_dict(dict1, dict2, list_merge_strategy='replace')
        {'a': [3, 4]}
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result:
            # 处理已有的键
            if isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = merge_dict(
                    result[key], value, list_merge_strategy
                )
            elif isinstance(result[key], list) and isinstance(value, list):
                # 根据策略合并列表
                if list_merge_strategy == 'append':
                    result[key] = result[key] + value
                elif list_merge_strategy == 'replace':
                    result[key] = value
                elif list_merge_strategy == 'extend':
                    # 合并并去重（适用于可哈希的元素）
                    combined = result[key] + value
                    try:
                        result[key] = list(dict.fromkeys(combined))
                    except TypeError:
                        # 如果元素不可哈希，直接追加
                        result[key] = combined
                else:
                    # 未知策略，默认追加
                    result[key] = result[key] + value
            else:
                # 其他类型，dict2 覆盖 dict1
                result[key] = value
        else:
            # 新键，直接添加
            result[key] = value

    return result


def yamlfiles2dict(*yaml_files: Union[str, Path],
                   expand_variables: bool = True) -> Dict[str, Any]:
    """将一个或多个 YAML 文件转换为合并的字典

    支持 YAML 值中的变量引用，如 $var 或 ${var}。
    变量引用会在文件间和文件内展开。

    Args:
        *yaml_files: 一个或多个 YAML 文件路径
        expand_variables: 是否展开变量引用（如 $a, ${a}）。
                          如果为 True，在同一文件中前面定义的变量或
                          在前面文件中定义的变量将被展开。默认为 True。

    Returns:
        包含所有 YAML 文件合并内容的字典

    Raises:
        FileNotFoundError: 如果任何 YAML 文件不存在
        ParseError: 如果 YAML 解析错误

    Examples:
        >>> # config1.yaml
        >>> base_url: "http://example.com"
        >>> # config2.yaml
        >>> api_url: "${base_url}/api"
        >>> result = yamlfiles2dict('config1.yaml', 'config2.yaml')
        >>> print(result['api_url'])
        "http://example.com/api"

        >>> # 不展开变量
        >>> result = yamlfiles2dict('config1.yaml', 'config2.yaml',
        ...                          expand_variables=False)
        >>> print(result['api_url'])
        "${base_url}/api"
    """
    from .tcl_bridge import TclBridge

    result: Dict[str, Any] = {}
    tcl_bridge = TclBridge() if expand_variables else None

    for yaml_file in yaml_files:
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            raise FileNotFoundError(
                f"YAML file not found: {yaml_file}",
                file_path=yaml_path
            )

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_dict = yaml.safe_load(f)

            if not yaml_dict:  # 处理空 YAML 文件
                continue

            if expand_variables and tcl_bridge:
                # 使用 Tcl 桥接器展开变量引用
                if result:  # 如果已经有内容，使用 merge_and_expand
                    result = tcl_bridge.merge_and_expand(result, yaml_dict)
                else:  # 如果是第一个文件，直接转换并展开
                    result = yaml_dict
                    # 单独展开变量引用
                    temp_interp = tcl_bridge.dict_to_interp(result)
                    tcl_bridge.expand_variables(temp_interp)
                    result = tcl_bridge.interp_to_dict(temp_interp)
            else:
                # 不展开变量，直接合并
                result = merge_dict(result, yaml_dict)

        except yaml.YAMLError as e:
            raise ParseError(
                f"Failed to parse YAML file: {str(e)}",
                file_path=yaml_path,
                context={'yaml_error': str(e)}
            )
        except Exception as e:
            if expand_variables:
                raise ParseError(
                    f"Failed to process YAML file: {str(e)}",
                    file_path=yaml_path,
                    context={'original_error': str(e)}
                )
            else:
                raise

    return result


def files2dict(*input_files: Union[str, Path],
               mode: ConversionMode = ConversionMode.AUTO,
               skip_errors: bool = False) -> Dict[str, Any]:
    """将混合的 YAML 和 Tcl 文件转换为单个 Python 字典

    文件按顺序处理并合并到单个字典中。

    Args:
        *input_files: 一个或多个 YAML 或 Tcl 文件路径
        mode: Tcl 值的转换模式 ("auto", "str", 或 "list")
        skip_errors: 是否跳过导致错误的文件（True）还是抛出异常（False）

    Returns:
        包含所有输入文件合并内容的字典

    Raises:
        ValueError: 如果没有提供输入文件
        FileNotFoundError: 如果文件不存在且 skip_errors 为 False

    Examples:
        >>> # 混合格式
        >>> result = files2dict('config.yaml', 'settings.tcl')

        >>> # 跳过错误文件
        >>> result = files2dict('config.yaml', 'missing.tcl',
        ...                     skip_errors=True)
    """
    if not input_files:
        raise ValueError("At least one input file must be provided")

    result_dict: Dict[str, Any] = {}

    for input_file in input_files:
        file_path = Path(input_file)

        try:
            if not file_path.exists():
                if skip_errors:
                    continue
                else:
                    raise FileNotFoundError(
                        f"Input file not found: {input_file}",
                        file_path=file_path
                    )

            # 根据扩展名确定文件类型
            file_ext = file_path.suffix.lower()

            if file_ext in ('.yaml', '.yml'):
                # 处理 YAML 文件
                try:
                    with open(file_path, 'r', encoding='utf-8') as yf:
                        yaml_dict = yaml.safe_load(yf)

                    if yaml_dict:  # 跳过空 YAML 文件
                        result_dict = merge_dict(result_dict, yaml_dict)

                except yaml.YAMLError as e:
                    if not skip_errors:
                        raise ParseError(
                            f"YAML parsing error: {str(e)}",
                            file_path=file_path,
                            context={'yaml_error': str(e)}
                        )

            elif file_ext in ('.tcl', '.tk'):
                # 处理 Tcl 文件
                from .tcl_bridge import TclBridge

                try:
                    tcl_bridge = TclBridge()
                    tcl_dict = tcl_bridge.load_tcl_file(file_path, mode=mode)
                    result_dict = merge_dict(result_dict, tcl_dict)

                except Exception as e:
                    if not skip_errors:
                        raise ParseError(
                            f"Tcl file processing error: {str(e)}",
                            file_path=file_path,
                            context={'tcl_error': str(e)}
                        )
            else:
                # 未知文件类型
                if not skip_errors:
                    raise FileError(
                        f"Unknown file extension: {file_ext}",
                        file_path=file_path,
                        context={'extension': file_ext}
                    )

        except Exception as e:
            if not skip_errors:
                raise

    return result_dict


# 性能优化的辅助函数
@lru_cache(maxsize=128)
def _get_file_mtime(file_path: Path) -> float:
    """获取文件修改时间（带缓存）

    Args:
        file_path: 文件路径

    Returns:
        文件修改时间戳
    """
    return file_path.stat().st_mtime


def has_file_changed(file_path: Path, cached_mtime: Optional[float] = None) -> bool:
    """检查文件是否已更改

    Args:
        file_path: 文件路径
        cached_mtime: 缓存的修改时间

    Returns:
        文件是否已更改
    """
    if not file_path.exists():
        return True

    current_mtime = _get_file_mtime(file_path)
    if cached_mtime is None:
        return True

    return current_mtime != cached_mtime
