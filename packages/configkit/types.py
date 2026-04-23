#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 类型定义

提供类型提示和类型常量，用于增强代码的类型安全性。
"""

from typing import (
    Any, Dict, List, Tuple, Optional, Union, Callable, TypeVar, Generic,
    Protocol, runtime_checkable, TypedDict, Iterator, Iterable
)
from pathlib import Path
from tkinter import Tcl
from enum import Enum


# 基本类型别名
ConfigValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
ConfigDict = Dict[str, ConfigValue]
TclValue = str  # Tcl 中所有值都是字符串


class ConversionMode(Enum):
    """转换模式枚举

    定义 Tcl 值转 Python 值时的转换策略。
    """
    AUTO = "auto"      # 自动检测类型
    STRING = "str"     # 总是作为字符串
    LIST = "list"      # 空格分隔的值转换为列表


class VariableSyntax(Enum):
    """变量引用语法枚举

    支持不同的变量引用语法格式。
    """
    SIMPLE = "$"           # 简单语法：$var
    BRACED = "${}"         # 花括号语法：${var}
    NESTED = "$()"         # 嵌套语法：$(dict(key))
    TCL_BRACE = "${}"      # Tcl 花括号：${dict(key)}


class ValueType(Enum):
    """值类型枚举

    定义支持的值类型。
    """
    BOOL = "bool"
    NONE = "none"
    NUMBER = "number"
    STRING = "string"
    LIST = "list"
    DICT = "dict"


# 泛型类型变量
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class FileFormat(Protocol):
    """文件格式协议

    定义配置文件格式的基本接口。
    """

    @staticmethod
    def load(file_path: Path) -> ConfigDict:
        """加载配置文件

        Args:
            file_path: 文件路径

        Returns:
            配置字典
        """
        ...

    @staticmethod
    def dump(data: ConfigDict, file_path: Path) -> None:
        """保存配置到文件

        Args:
            data: 配置数据
            file_path: 文件路径
        """
        ...

    @staticmethod
    def parse(content: str) -> ConfigDict:
        """解析配置内容

        Args:
            content: 配置内容字符串

        Returns:
            配置字典
        """
        ...

    @staticmethod
    def serialize(data: ConfigDict) -> str:
        """序列化配置数据

        Args:
            data: 配置数据

        Returns:
            配置字符串
        """
        ...


class MergeStrategy(Protocol):
    """合并策略协议

    定义字典合并策略的接口。
    """

    def __call__(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """合并两个字典

        Args:
            dict1: 第一个字典
            dict2: 第二个字典

        Returns:
            合并后的字典
        """
        ...


class VariableExpander(Protocol):
    """变量展开器协议

    定义变量引用展开的接口。
    """

    def expand(self, text: str, context: Dict[str, Any]) -> str:
        """展开文本中的变量引用

        Args:
            text: 包含变量引用的文本
            context: 变量上下文

        Returns:
            展开后的文本
        """
        ...


class TypeConverter(Protocol):
    """类型转换器协议

    定义类型转换的接口。
    """

    def py_to_tcl(self, value: Any) -> str:
        """Python 值转 Tcl 格式

        Args:
            value: Python 值

        Returns:
            Tcl 格式字符串
        """
        ...

    def tcl_to_py(self, value: str, mode: ConversionMode = ConversionMode.AUTO) -> Any:
        """Tcl 值转 Python 类型

        Args:
            value: Tcl 值字符串
            mode: 转换模式

        Returns:
            Python 值
        """
        ...


# TypedDict 定义
class ConfigSource(TypedDict):
    """配置源信息"""
    path: str
    format: str
    mtime: float
    size: int


class VariableReference(TypedDict):
    """变量引用信息"""
    variable: str
    start_pos: int
    end_pos: int
    syntax: VariableSyntax


class ConversionContext(TypedDict, total=False):
    """转换上下文"""
    mode: ConversionMode
    preserve_types: bool
    expand_variables: bool
    strict_mode: bool
    type_info: Dict[str, ValueType]


class ParseResult(TypedDict):
    """解析结果"""
    data: ConfigDict
    errors: List[str]
    warnings: List[str]
    source_info: Optional[ConfigSource]


# 函数类型别名
MergeFunc = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
ConvertFunc = Callable[[Any], str]
ValidateFunc = Callable[[ConfigDict], bool]
ErrorHandler = Callable[[Exception], None]


# 复杂类型别名
ConfigLoader = Callable[[Path], ConfigDict]
ConfigDumper = Callable[[ConfigDict, Path], None]
FileFilter = Callable[[Path], bool]
PathResolver = Callable[[str, Optional[Path]], Path]


# Tcl 解释器类型别名
TclInterpreter = Tcl  # 直接使用 tkinter.Tcl 作为类型别名


# 工具类型
class DefaultDict(Dict[str, Any]):
    """默认字典类型

    提供默认值的字典类型，用于配置管理。
    """

    def __init__(self, default_factory: Optional[Callable[[], Any]] = None):
        """初始化默认字典

        Args:
            default_factory: 默认值工厂函数
        """
        super().__init__()
        self._default_factory = default_factory

    def __getitem__(self, key: str) -> Any:
        """获取值，如果不存在则使用默认值

        Args:
            key: 键名

        Returns:
            值或默认值
        """
        try:
            return super().__getitem__(key)
        except KeyError:
            if self._default_factory is not None:
                value = self._default_factory()
                self[key] = value
                return value
            raise


# 类型检查工具
def is_dict(value: Any) -> bool:
    """检查值是否为字典类型"""
    return isinstance(value, dict)


def is_list(value: Any) -> bool:
    """检查值是否为列表类型"""
    return isinstance(value, list)


def is_primitive(value: Any) -> bool:
    """检查值是否为基本类型"""
    return value is None or isinstance(value, (str, int, float, bool))


def get_value_type(value: Any) -> ValueType:
    """获取值的类型

    Args:
        value: 任意值

    Returns:
        值类型枚举
    """
    if isinstance(value, bool):
        return ValueType.BOOL
    elif value is None:
        return ValueType.NONE
    elif isinstance(value, (int, float)):
        return ValueType.NUMBER
    elif isinstance(value, str):
        return ValueType.STRING
    elif isinstance(value, list):
        return ValueType.LIST
    elif isinstance(value, dict):
        return ValueType.DICT
    else:
        return ValueType.STRING  # 默认为字符串
