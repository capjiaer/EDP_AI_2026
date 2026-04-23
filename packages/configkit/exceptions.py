#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 异常定义

提供统一的异常层次结构，用于配置处理过程中的错误处理。
"""

from typing import Optional, Dict, Any
from pathlib import Path


class ConfigKitError(Exception):
    """ConfigKit 基础异常类

    所有 ConfigKit 异常的基类，提供统一的错误处理接口。
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """初始化异常

        Args:
            message: 错误消息
            context: 错误上下文信息
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.context['error_type'] = self.__class__.__name__

    def __str__(self) -> str:
        """返回格式化的错误消息"""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式

        Returns:
            包含异常信息的字典
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'context': self.context
        }


class FileError(ConfigKitError):
    """文件操作异常

    当文件读取、写入或解析过程中发生错误时抛出。
    """

    def __init__(self, message: str, file_path: Optional[Path] = None,
                 context: Optional[Dict[str, Any]] = None):
        """初始化文件异常

        Args:
            message: 错误消息
            file_path: 相关文件路径
            context: 额外的上下文信息
        """
        context = context or {}
        if file_path:
            context['file_path'] = str(file_path)
        super().__init__(message, context)


class FileNotFoundError(FileError):
    """文件未找到异常"""
    pass


class ParseError(ConfigKitError):
    """解析异常

    当配置文件解析失败时抛出。
    """

    def __init__(self, message: str, file_path: Optional[Path] = None,
                 line_number: Optional[int] = None, column_number: Optional[int] = None,
                 context: Optional[Dict[str, Any]] = None):
        """初始化解析异常

        Args:
            message: 错误消息
            file_path: 相关文件路径
            line_number: 错误行号
            column_number: 错误列号
            context: 额外的上下文信息
        """
        context = context or {}
        if file_path:
            context['file_path'] = str(file_path)
        if line_number is not None:
            context['line_number'] = line_number
        if column_number is not None:
            context['column_number'] = column_number
        super().__init__(message, context)


class ValidationError(ConfigKitError):
    """验证异常

    当配置验证失败时抛出。
    """

    def __init__(self, message: str, field_path: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """初始化验证异常

        Args:
            message: 错误消息
            field_path: 字段路径（如 "server.port"）
            context: 额外的上下文信息
        """
        context = context or {}
        if field_path:
            context['field_path'] = field_path
        super().__init__(message, context)


class ConversionError(ConfigKitError):
    """转换异常

    当类型转换或格式转换失败时抛出。
    """

    def __init__(self, message: str, source_type: Optional[str] = None,
                 target_type: Optional[str] = None, value: Any = None,
                 context: Optional[Dict[str, Any]] = None):
        """初始化转换异常

        Args:
            message: 错误消息
            source_type: 源类型
            target_type: 目标类型
            value: 导致错误的值
            context: 额外的上下文信息
        """
        context = context or {}
        if source_type:
            context['source_type'] = source_type
        if target_type:
            context['target_type'] = target_type
        if value is not None:
            context['value'] = repr(value)
        super().__init__(message, context)


class VariableError(ConfigKitError):
    """变量处理异常

    当变量引用展开或处理失败时抛出。
    """

    def __init__(self, message: str, variable_name: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """初始化变量异常

        Args:
            message: 错误消息
            variable_name: 相关变量名
            context: 额外的上下文信息
        """
        context = context or {}
        if variable_name:
            context['variable_name'] = variable_name
        super().__init__(message, context)


class CircularReferenceError(VariableError):
    """循环引用异常

    当检测到循环引用时抛出。
    """
    pass


class TclError(ConfigKitError):
    """Tcl 相关异常

    当 Tcl 解释器操作失败时抛出。
    """

    def __init__(self, message: str, tcl_command: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """初始化 Tcl 异常

        Args:
            message: 错误消息
            tcl_command: 相关的 Tcl 命令
            context: 额外的上下文信息
        """
        context = context or {}
        if tcl_command:
            context['tcl_command'] = tcl_command
        super().__init__(message, context)


# 向后兼容的异常别名（与原版 edp_configkit 兼容）
class ConfigError(ConfigKitError):
    """配置错误（向后兼容）"""
    pass


class EDPFileNotFoundError(FileNotFoundError):
    """文件未找到错误（向后兼容）"""
    pass
