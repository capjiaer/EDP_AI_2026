#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.core.step - 步骤定义模块

简化的步骤定义，只关注步骤本身的状态和配置。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class StepStatus(Enum):
    """步骤状态枚举"""
    INIT = "init"               # 初始状态
    READY = "ready"             # 准备就绪（依赖已满足）
    RUNNING = "running"         # 运行中
    FINISHED = "finished"       # 已完成
    FAILED = "failed"           # 失败
    SKIPPED = "skipped"         # 已跳过
    CANCELLED = "cancelled"     # 已取消
    RETRYING = "retrying"       # 重试中


@dataclass
class Step:
    """工作流步骤定义

    简化的步骤类，只关注步骤的配置和状态，不包含依赖关系。

    Attributes:
        id: 步骤ID（唯一标识符）
        name: 步骤名称
        cmd: 执行命令
        config: 配置参数
        status: 当前状态
        retry_count: 重试次数
        created_at: 创建时间
        updated_at: 更新时间
    """

    id: str
    name: str
    cmd: str = ""
    tool_name: str = ""
    sub_steps: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.INIT
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_status(self, new_status: StepStatus) -> None:
        """更新步骤状态"""
        self.status = new_status
        self.updated_at = datetime.now()

    def can_execute(self) -> bool:
        """检查步骤是否可以执行"""
        return self.status in [StepStatus.INIT, StepStatus.READY, StepStatus.RETRYING]

    def is_finished(self) -> bool:
        """检查步骤是否已完成（成功或跳过）"""
        return self.status in [StepStatus.FINISHED, StepStatus.SKIPPED]

    def is_failed(self) -> bool:
        """检查步骤是否失败"""
        return self.status == StepStatus.FAILED

    def can_retry(self, max_retries: int = 3) -> bool:
        """检查步骤是否可以重试"""
        return self.retry_count < max_retries

    def increment_retry(self) -> None:
        """增加重试计数"""
        self.retry_count += 1
        self.update_status(StepStatus.RETRYING)

    def reset(self) -> None:
        """重置步骤状态"""
        self.status = StepStatus.INIT
        self.retry_count = 0
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"Step(id={self.id}, status={self.status.value})"


class StepResult:
    """步骤执行结果"""

    def __init__(self, step_id: str, success: bool,
                 output: str = "", error: str = "",
                 execution_time: float = 0.0):
        self.step_id = step_id
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'step_id': self.step_id,
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat()
        }
