#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.loader.step_loader - 步骤加载器

管理工具的步骤注册和查询，支持覆盖链加载。

新 step.yaml 格式：
    pnr_innovus:
      supported_steps:
        place:
          invoke: ["innovus -init {script}", "|& tee {step}.log"]
          sub_steps: [global_place, detail_place]

覆盖链：common_prj → project，同名 step 整体覆盖，新增 step 追加。
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class StepRegistry:
    """步骤注册表

    管理所有工具的步骤注册，支持覆盖链合并。

    内部存储结构：
        _registry: {
            "pnr_innovus": {
                "place": {
                    "sub_steps": ["global_place", "detail_place"],
                    "invoke": ["innovus -init {script}", ...]
                }
            }
        }
    """

    def __init__(self):
        self._registry: Dict[str, Dict[str, Dict[str, Any]]] = {}

    @staticmethod
    def _normalize_sub_steps(sub_steps: Any, tool_name: str, step_name: str) -> List[Dict[str, str]]:
        """Normalize sub_steps into spec list: [{name, runner, command?}]"""
        if sub_steps is None:
            return []
        if not isinstance(sub_steps, list):
            raise ValueError(
                f"工具 {tool_name} 步骤 {step_name} 的 sub_steps 格式无效，应为列表"
            )

        normalized: List[Dict[str, str]] = []
        for idx, item in enumerate(sub_steps):
            if isinstance(item, str):
                name = item.strip()
                if not name:
                    raise ValueError(
                        f"工具 {tool_name} 步骤 {step_name} 的 sub_steps[{idx}] 不能为空字符串"
                    )
                normalized.append({"name": name, "runner": "tcl"})
                continue

            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                runner = str(item.get("runner", "tcl")).strip().lower()
                if not name:
                    raise ValueError(
                        f"工具 {tool_name} 步骤 {step_name} 的 sub_steps[{idx}] 缺少 name"
                    )
                if runner not in ("tcl", "shell"):
                    raise ValueError(
                        f"工具 {tool_name} 步骤 {step_name} 的 sub_steps[{idx}] runner 无效: {runner}"
                    )
                spec: Dict[str, str] = {"name": name, "runner": runner}
                if runner == "shell":
                    cmd = item.get("command", "")
                    if cmd is not None and str(cmd).strip():
                        spec["command"] = str(cmd).strip()
                normalized.append(spec)
                continue

            raise ValueError(
                f"工具 {tool_name} 步骤 {step_name} 的 sub_steps[{idx}] 格式无效，"
                "应为字符串或字典"
            )
        return normalized

    def register_tool_steps(self, step_file: Path) -> None:
        """从 step.yaml 文件注册工具步骤

        Args:
            step_file: step.yaml 文件路径（位于 cmds/<tool>/step.yaml）

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果文件格式无效
        """
        if not step_file.exists():
            raise FileNotFoundError(f"步骤文件不存在: {step_file}")

        with open(step_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        for tool_name, tool_data in data.items():
            if not isinstance(tool_data, dict):
                raise ValueError(f"工具 {tool_name} 的数据格式无效，应为字典")

            supported_steps = tool_data.get('supported_steps', {})
            if not isinstance(supported_steps, dict):
                raise ValueError(f"工具 {tool_name} 的 supported_steps 格式无效，应为字典")

            if tool_name not in self._registry:
                self._registry[tool_name] = {}

            for step_name, step_data in supported_steps.items():
                if isinstance(step_data, dict):
                    sub_steps = self._normalize_sub_steps(
                        step_data.get("sub_steps", []), tool_name, step_name
                    )
                    invoke = step_data.get("invoke", [])
                else:
                    raise ValueError(
                        f"工具 {tool_name} 步骤 {step_name} 格式无效，"
                        f"应为 {{invoke: [...], sub_steps: [...]}}"
                    )
                self._registry[tool_name][step_name] = {
                    "sub_steps": list(sub_steps),
                    "invoke": list(invoke),
                }

    def merge_tool_steps(self, step_file: Path) -> None:
        """从 step.yaml 文件合并工具步骤（覆盖链用）

        同名 step 整体覆盖，新增 step 追加。

        Args:
            step_file: project 级 step.yaml 文件路径
        """
        if not step_file.exists():
            return

        with open(step_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        for tool_name, tool_data in data.items():
            if not isinstance(tool_data, dict):
                continue

            supported_steps = tool_data.get('supported_steps', {})
            if not isinstance(supported_steps, dict):
                continue

            if tool_name not in self._registry:
                self._registry[tool_name] = {}

            for step_name, step_data in supported_steps.items():
                if isinstance(step_data, dict):
                    sub_steps = self._normalize_sub_steps(
                        step_data.get("sub_steps", []), tool_name, step_name
                    )
                    invoke = step_data.get("invoke", [])
                else:
                    continue
                self._registry[tool_name][step_name] = {
                    "sub_steps": list(sub_steps),
                    "invoke": list(invoke),
                }

    # --- 查询接口 ---

    def get_sub_steps(self, tool_name: str, step_name: str) -> List[str]:
        """获取步骤的 sub_step 有序列表"""
        if tool_name not in self._registry:
            raise ValueError(f"工具 {tool_name} 未注册")
        if step_name not in self._registry[tool_name]:
            raise ValueError(f"工具 {tool_name} 没有步骤 {step_name}")
        specs = self._registry[tool_name][step_name]["sub_steps"]
        return [str(s.get("name", "")) for s in specs if isinstance(s, dict)]

    def get_sub_step_specs(self, tool_name: str, step_name: str) -> List[Dict[str, str]]:
        """获取步骤的 sub_step 规格列表（含 runner）。"""
        if tool_name not in self._registry:
            raise ValueError(f"工具 {tool_name} 未注册")
        if step_name not in self._registry[tool_name]:
            raise ValueError(f"工具 {tool_name} 没有步骤 {step_name}")
        specs = self._registry[tool_name][step_name]["sub_steps"]
        return [dict(s) for s in specs]

    def get_invoke(self, tool_name: str, step_name: str) -> List[str]:
        """获取步骤的 invoke 列表"""
        if tool_name not in self._registry:
            raise ValueError(f"工具 {tool_name} 未注册")
        if step_name not in self._registry[tool_name]:
            raise ValueError(f"工具 {tool_name} 没有步骤 {step_name}")
        return list(self._registry[tool_name][step_name]["invoke"])

    def get_tool_steps(self, tool_name: str) -> Dict[str, Dict[str, Any]]:
        """获取工具的所有步骤

        Returns:
            {step_name: {"sub_steps": [...], "invoke": [...]}} 字典
        """
        return dict(self._registry.get(tool_name, {}))

    def get_all_tools(self) -> List[str]:
        """获取所有注册的工具名称"""
        return list(self._registry.keys())

    def get_all_steps(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """获取完整注册表"""
        return {tool: dict(steps) for tool, steps in self._registry.items()}

    def get_step_count(self, tool_name: str) -> int:
        """获取工具的步骤数量"""
        return len(self._registry.get(tool_name, {}))

    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否已注册"""
        return tool_name in self._registry

    def has_step(self, tool_name: str, step_name: str) -> bool:
        """检查工具是否有指定步骤"""
        return tool_name in self._registry and step_name in self._registry[tool_name]

    # --- 目录级别加载 ---

    def load_from_flow_path(self, base_path: Path) -> None:
        """从 flow 目录加载所有工具的 step.yaml（覆盖链 base 级）

        扫描 base_path/cmds/*/step.yaml，注册所有工具。

        Args:
            base_path: flow base 路径（如 initialize/SAMSUNG/S4/common_prj/）
        """
        cmds_dir = base_path / "cmds"
        if not cmds_dir.exists():
            return

        for tool_dir in cmds_dir.iterdir():
            if tool_dir.is_dir() and not tool_dir.name.startswith('.'):
                step_file = tool_dir / "step.yaml"
                if step_file.exists():
                    self.register_tool_steps(step_file)

    def merge_from_flow_path(self, base_path: Path) -> None:
        """从 flow 目录合并工具步骤（覆盖链 overlay 级）

        扫描 base_path/cmds/*/step.yaml，同名 step 整体覆盖。

        Args:
            base_path: flow overlay 路径（如 initialize/SAMSUNG/S4/dongting/）
        """
        cmds_dir = base_path / "cmds"
        if not cmds_dir.exists():
            return

        for tool_dir in cmds_dir.iterdir():
            if tool_dir.is_dir() and not tool_dir.name.startswith('.'):
                step_file = tool_dir / "step.yaml"
                if step_file.exists():
                    self.merge_tool_steps(step_file)

    def load_with_override(self, base_path: Path,
                           overlay_path: Optional[Path] = None) -> None:
        """按覆盖链加载工具步骤

        先加载 base_path，再用 overlay_path 覆盖。

        Args:
            base_path: base 路径（如 common_prj/）
            overlay_path: 可选 overlay 路径（如 dongting/）
        """
        self.load_from_flow_path(base_path)
        if overlay_path:
            self.merge_from_flow_path(overlay_path)


def load_tools_from_flow_path(base_path: Path,
                               overlay_path: Optional[Path] = None) -> StepRegistry:
    """便捷函数：从 flow 目录加载所有工具

    Args:
        base_path: base flow 路径
        overlay_path: 可选 overlay 路径

    Returns:
        加载好的 StepRegistry 实例
    """
    registry = StepRegistry()
    registry.load_with_override(base_path, overlay_path)
    return registry
