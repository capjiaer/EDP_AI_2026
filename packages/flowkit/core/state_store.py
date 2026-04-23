#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.core.state_store - 执行状态持久化

每个 step 跑完后将终态写入磁盘，支持断点续跑。
只写终态（FINISHED/FAILED/SKIPPED），不在文件里的就是 INIT。
"""

from pathlib import Path
from typing import Dict, Optional

import yaml

from .step import StepStatus


class StateStore:
    """执行状态持久化

    Args:
        state_file: 状态文件路径（如 workdir/.edp_state.yaml）
    """

    # 顶层 key，用于记录使用的 graph config
    GRAPH_CONFIG_KEY = '_graph_config'

    def __init__(self, state_file: Path):
        self.state_file = Path(state_file)

    def save(self, step_id: str, status: StepStatus,
             execution_time: float = 0.0, error: str = "") -> None:
        """保存一个 step 的终态

        Args:
            step_id: 步骤 ID
            status: 终态（FINISHED/FAILED/SKIPPED）
            execution_time: 执行耗时（秒）
            error: 错误信息（如有）
        """
        state = self._load_raw()

        state[step_id] = {
            'status': status.value,
            'execution_time': execution_time,
        }
        if error:
            state[step_id]['error'] = error

        self._write(state)

    def load(self) -> Dict[str, StepStatus]:
        """加载所有已持久化的状态

        Returns:
            {step_id: StepStatus}，只包含终态，没有的 step 不在 dict 里
        """
        state = self._load_raw()
        result = {}
        for sid, info in state.items():
            if sid.startswith('_'):
                continue
            try:
                status = StepStatus(info['status'])
                result[sid] = status
            except ValueError:
                continue
        return result

    def save_graph_config(self, graph_config_name: str) -> None:
        """记录使用的 graph config 文件名"""
        state = self._load_raw()
        state[self.GRAPH_CONFIG_KEY] = graph_config_name
        self._write(state)

    def load_graph_config(self) -> Optional[str]:
        """读取记录的 graph config 文件名，无记录返回 None"""
        state = self._load_raw()
        value = state.get(self.GRAPH_CONFIG_KEY)
        return str(value) if value else None

    def clear_step(self, step_id: str) -> None:
        """清除单个步骤的状态（retry 时调用）"""
        states = self._load_raw()
        states.pop(step_id, None)
        if states:
            self._write(states)
        else:
            self.clear()

    def clear(self) -> None:
        """清空状态文件（重新开始时调用）"""
        if self.state_file.exists():
            self.state_file.unlink()

    def exists(self) -> bool:
        """状态文件是否存在（用于判断是否有可恢复的状态）"""
        return self.state_file.exists()

    # --- 内部方法 ---

    def _load_raw(self) -> dict:
        """读取原始 YAML，不存在则返回空 dict"""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write(self, state: dict) -> None:
        """写入 YAML 文件"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            yaml.dump(state, f, default_flow_style=False, allow_unicode=True)
