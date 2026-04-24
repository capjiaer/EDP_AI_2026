#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit - 现代化的配置转换库

这是原版 edp_configkit 的现代化重写版本，保持向后兼容的同时引入了现代化改进：

**核心功能：**
- Python ↔ Tcl 双向转换
- YAML ↔ Tcl 文件格式转换
- 变量引用展开 ($var, ${var})
- 类型信息保持
- 嵌套结构支持

**现代化改进：**
- 完整的类型提示
- 面向对象设计
- 更好的错误处理
- 性能优化
- 扩展性增强

**基本用法：**

```python
# 加载 YAML 文件
from configkit import yamlfiles2dict, files2dict

# 加载单个或多个 YAML 文件（支持变量引用展开）
config = yamlfiles2dict('config1.yaml', 'config2.yaml')

# 加载混合格式文件
config = files2dict('config.yaml', 'settings.tcl')

# 面向对象接口
from configkit.core import DictOperations, TclBridge

dict_ops = DictOperations()
config = dict_ops.load_yaml('config.yaml')

tcl_bridge = TclBridge()
interp = tcl_bridge.dict_to_interp(config)
result = tcl_bridge.interp_to_dict()
```

**向后兼容：**
保持与原版 edp_configkit 的 API 兼容性，可以直接替换使用。
"""

__version__ = '2.0.0'
__author__ = 'EDP Team'

# 核心功能导入
from .core import (
    # 字典操作
    DictOperations,
    merge_dict,
    yamlfiles2dict,
    files2dict,

    # 值转换器
    ValueConverter,

    # Tcl 桥接器
    TclBridge,
)

# 向后兼容的函数接口
from .core.dict_ops import (
    merge_dict,
    yamlfiles2dict,
    files2dict,
)

from .core.value_converter import (
    value_format_py2tcl,
    value_format_tcl2py,
    detect_tcl_list,
)

from .core.tcl_bridge_compat import (
    dict2tclinterp,
    tclinterp2dict,
    tclinterp2tclfile,
    tclfiles2tclinterp,
    expand_variable_references,
    files2tcl,
)

from .core.type_conversion import (
    get_var_type,
    convert_list_element,
    convert_value,
    value_format_tcl2py_list_item,
)

# 异常导入
from .exceptions import (
    ConfigKitError,
    FileError,
    FileNotFoundError,
    ParseError,
    ValidationError,
    ConversionError,
    VariableError,
    TclError,
    # 向后兼容
    ConfigError,
    EDPFileNotFoundError,
)

# 类型导入
from .types import (
    # 基本类型
    ConfigValue,
    ConfigDict,
    TclValue,

    # 枚举类型
    ConversionMode,
    ValueType,
    VariableSyntax,

    # 协议和接口
    FileFormat,
    MergeStrategy,
    VariableExpander,
    TypeConverter,

    # 类型别名
    MergeFunc,
    ConvertFunc,
    ConfigLoader,
    ConfigDumper,

    # 工具函数
    is_dict,
    is_list,
    is_primitive,
    get_value_type,
)

__all__ = [
    # 版本信息
    '__version__',
    '__author__',

    # 核心类
    'DictOperations',
    'ValueConverter',
    'TclBridge',

    # 字典操作函数
    'merge_dict',
    'yamlfiles2dict',
    'files2dict',

    # 值格式转换函数
    'value_format_py2tcl',
    'value_format_tcl2py',
    'detect_tcl_list',

    # Python <-> Tcl 转换函数
    'dict2tclinterp',
    'tclinterp2dict',
    'expand_variable_references',

    # 文件操作函数
    'tclinterp2tclfile',
    'tclfiles2tclinterp',
    'files2tcl',

    # 类型转换函数
    'get_var_type',
    'convert_list_element',
    'convert_value',
    'value_format_tcl2py_list_item',

    # 异常类
    'ConfigKitError',
    'FileError',
    'FileNotFoundError',
    'ParseError',
    'ValidationError',
    'ConversionError',
    'VariableError',
    'TclError',
    'ConfigError',  # 向后兼容
    'EDPFileNotFoundError',  # 向后兼容

    # 类型定义
    'ConfigValue',
    'ConfigDict',
    'TclValue',
    'ConversionMode',
    'ValueType',
    'VariableSyntax',

    # 工具函数
    'is_dict',
    'is_list',
    'is_primitive',
    'get_value_type',
]

# 便利函数
def load_yaml(*file_paths: str, expand_variables: bool = True) -> dict:
    """加载 YAML 文件的便利函数

    Args:
        *file_paths: 一个或多个 YAML 文件路径
        expand_variables: 是否展开变量引用

    Returns:
        合并后的配置字典
    """
    return yamlfiles2dict(*file_paths, expand_variables=expand_variables)


def load_config(*file_paths: str, mode: str = 'auto') -> dict:
    """加载混合格式配置文件的便利函数

    Args:
        *file_paths: 一个或多个配置文件路径
        mode: 转换模式 ('auto', 'str', 'list')

    Returns:
        合并后的配置字典
    """
    conversion_mode = ConversionMode.AUTO if mode == 'auto' else (
        ConversionMode.STRING if mode == 'str' else ConversionMode.LIST
    )
    return files2dict(*file_paths, mode=conversion_mode)


# 设置基础配置
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
