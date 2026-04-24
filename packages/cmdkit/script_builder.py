#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cmdkit.script_builder - 脚本生成器

根据 flow 目录结构和覆盖链，为每个 step 生成可执行的 Tcl 脚本和 shell 启动脚本。

生成的脚本分三个阶段：
  Phase 1: Source — source 所有 proc 定义和配置（绝对路径）
  Config:  source config.tcl — 独立配置文件，由 configkit.files2tcl 生成
  Phase 2: Execute — 按 step.yaml 声明的顺序调用 sub_step，hook 按需包裹

另外根据 step.yaml 的 invoke 列表 + config.yaml 的变量值，生成 .sh 启动包装。
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from configkit import yamlfiles2dict
from flowkit.loader.step_loader import StepRegistry
from ._invoke_resolver import build_step_shell as _build_step_shell
from ._invoke_resolver import resolve_invoke as _resolve_invoke
from ._invoke_resolver import validate_safe_invoke_item as _validate_safe_invoke_item
from ._proc_conflict import validate_proc_conflicts
from ._script_sections import build_debug_script as _build_debug_script
from ._script_sections import build_header as _build_header
from ._script_sections import generate_config_tcl as _generate_config_tcl
from ._script_utils import _posix, _source_block


class ScriptBuilder:
    """脚本生成器

    知道目录结构，自动从 flow 目录加载 step.yaml、config.yaml，
    结合 workdir 的 hooks，生成最终的 Tcl 脚本和 shell 启动脚本。
    """

    def __init__(self,
                 flow_base_path: Path,
                 workdir_path: Path,
                 overlay_path: Optional[Path] = None,
                 common_packages_path: Optional[Path] = None,
                 preferred_shell: Optional[str] = None):
        self.flow_base_path = Path(flow_base_path)
        self.workdir_path = Path(workdir_path)
        self.overlay_path = Path(overlay_path) if overlay_path else None
        default_common_packages_path = (
            self.flow_base_path.parent.parent.parent.parent.parent / "common_packages"
        )
        resolved_common_packages_path = (
            Path(common_packages_path) if common_packages_path else default_common_packages_path
        )
        self._validate_common_packages_path(resolved_common_packages_path)
        self.common_packages_path = resolved_common_packages_path
        self.preferred_shell = self._detect_shell(preferred_shell)

        self.registry = StepRegistry()
        self.registry.load_with_override(self.flow_base_path, self.overlay_path)

    @staticmethod
    def _validate_common_packages_path(common_packages_path: Path) -> None:
        """拒绝历史旧目录 resources/common_packages，避免双路径混用。"""
        normalized = common_packages_path.resolve(strict=False).as_posix()
        if normalized.endswith("/resources/common_packages"):
            raise ValueError(
                "Unsupported common_packages path: resources/common_packages is retired. "
                "Use resources/flow/common_packages instead."
            )

    @staticmethod
    def _detect_shell(preferred_shell: Optional[str] = None) -> str:
        """自动检测当前 shell，返回 bash 或 csh"""
        shell_hint = (preferred_shell or os.environ.get("SHELL", "")).lower()
        if "tcsh" in shell_hint or "csh" in shell_hint:
            return "csh"
        return "bash"

    # ── edp vars ──

    def _build_edp_vars(self, tool_name: str, step_name: str,
                        debug: bool = False) -> Dict[str, str]:
        """构建 edp 命名空间变量（框架内置变量）"""
        parts = self.flow_base_path.parts
        try:
            idx = parts.index("initialize")
            foundry = parts[idx + 1] if idx + 1 < len(parts) else ""
            node = parts[idx + 2] if idx + 2 < len(parts) else ""
        except ValueError:
            foundry = ""
            node = ""

        project = self.overlay_path.name if self.overlay_path else "common"

        script_name = f"{step_name}_debug.tcl" if debug else f"{step_name}.tcl"
        tcl_path = self.workdir_path / "cmds" / tool_name / script_name
        run_dir = self.workdir_path / "runs" / tool_name / step_name

        result = {
            "step": step_name,
            "script": _posix(tcl_path.resolve()),
            "workdir": _posix(run_dir.resolve()),
            "tool": tool_name,
            "foundry": foundry,
            "node": node,
            "project": project,
        }

        # sub_steps 列表
        if self.registry.has_step(tool_name, step_name):
            sub_steps = self.registry.get_sub_steps(tool_name, step_name)
            result["sub_steps"] = " ".join(sub_steps)

        # 激活的 hooks（有实际内容的 hook proc）
        hooks_dir = self.workdir_path / "hooks" / tool_name / step_name
        active_hooks = []
        if hooks_dir.exists():
            for f in sorted(hooks_dir.iterdir()):
                if not f.is_file():
                    continue
                content = f.read_text(encoding='utf-8').strip()
                # 有内容且不只是模板注释（包含 "Your code here" 说明是空模板）
                if content and "Your code here" not in content:
                    active_hooks.append(f.name)
        if active_hooks:
            result["invoked_hooks"] = " ".join(active_hooks)

        return result

    # ── config.tcl 生成 ──

    def _generate_config_tcl(self, tool_name: str, step_name: str) -> Path:
        """用 configkit.files2tcl 生成 per-step 的 config.tcl"""
        return _generate_config_tcl(self, tool_name, step_name)

    # ── 主入口 ──

    def build_step_script(self, tool_name: str, step_name: str) -> str:
        """生成某个 step 的完整 Tcl 脚本"""
        validate_proc_conflicts(self, tool_name, step_name)
        sections = []

        header = self._build_header(tool_name, step_name)
        if header:
            sections.append(header)

        source_section = self._build_source_phase(tool_name, step_name)
        if source_section:
            sections.append(source_section)

        config_section = self._build_config_source(tool_name, step_name)
        if config_section:
            sections.append(config_section)

        exec_section = self._build_execute_phase(tool_name, step_name)
        if exec_section:
            sections.append(exec_section)

        return '\n\n'.join(filter(None, sections))

    def write_step_script(self, tool_name: str, step_name: str,
                          debug: bool = False) -> Path:
        """生成 config.tcl + .tcl + _debug.tcl + .sh 并写入文件"""
        # 1. 生成 per-step config.tcl
        self._generate_config_tcl(tool_name, step_name)

        # 2. 生成主 .tcl 脚本 → cmds/{tool}/
        tcl_content = self.build_step_script(tool_name, step_name)
        tcl_path = self.workdir_path / "cmds" / tool_name / f"{step_name}.tcl"
        tcl_path.parent.mkdir(parents=True, exist_ok=True)
        tcl_path.write_text(tcl_content, encoding='utf-8')

        # 3. 生成 debug 脚本 → cmds/{tool}/
        debug_content = self.build_debug_script(tool_name, step_name)
        debug_path = self.workdir_path / "cmds" / tool_name / f"{step_name}_debug.tcl"
        debug_path.write_text(debug_content, encoding='utf-8')

        # 4. 生成 shell 启动脚本（按当前 shell）→ runs/{tool}/{step}/
        shell_content = self.build_step_shell(
            tool_name, step_name, debug=debug
        )
        if shell_content:
            run_dir = self.workdir_path / "runs" / tool_name / step_name
            run_dir.mkdir(parents=True, exist_ok=True)
            ext = ".csh" if self.preferred_shell == "csh" else ".sh"
            script_name = f"{step_name}_debug{ext}" if debug else f"{step_name}{ext}"
            script_path = run_dir / script_name
            script_path.write_text(shell_content, encoding='utf-8')
            return script_path

        return tcl_path

    # ── Phase 1: Source ──

    def _build_source_phase(self, tool_name: str, step_name: str,
                            exclude: Optional[List[str]] = None) -> str:
        lines = [
            "# ============================================================",
            "# Phase 1: Source",
            "# ============================================================",
            ""
        ]

        _source_block(lines, "common_packages/default",
                      self.common_packages_path / "tcl_packages" / "default",
                      exclude=exclude)

        _source_block(lines, f"common_packages/{tool_name}",
                      self.common_packages_path / "tcl_packages" / tool_name)

        _source_block(lines, "tcl_packages (base)",
                      self.flow_base_path / "tcl_packages",
                      source_tag="base")

        if self.overlay_path:
            _source_block(lines, "tcl_packages (overlay)",
                          self.overlay_path / "tcl_packages",
                          source_tag="overlay")

        _source_block(lines, f"{tool_name}/procs",
                      self.flow_base_path / "cmds" / tool_name / "procs")

        # vendor_procs（如果有）
        _source_block(lines, f"{tool_name}/vendor_procs",
                      self.flow_base_path / "cmds" / tool_name / "vendor_procs")

        if self.registry.has_step(tool_name, step_name):
            steps_dir = self.flow_base_path / "cmds" / tool_name / "steps" / step_name
            sub_specs = self.registry.get_sub_step_specs(tool_name, step_name)
            has_any = False
            for spec in sub_specs:
                sub = spec.get("name", "")
                runner = spec.get("runner", "tcl")
                if runner != "tcl":
                    continue
                sub_file = steps_dir / f"{sub}.tcl"
                if sub_file.exists():
                    if not has_any:
                        lines.append(f"# --- {tool_name}/steps/{step_name} ---")
                        has_any = True
                    lines.append(f"source {_posix(sub_file.resolve())}")
                else:
                    if not has_any:
                        lines.append(f"# --- {tool_name}/steps/{step_name} ---")
                        has_any = True
                    lines.append(f"# WARNING: {_posix(sub_file)} not found")
            if has_any:
                lines.append("")

        # source hook proc definitions（workdir/hooks/{tool}/{step}/）
        hooks_dir = self.workdir_path / "hooks" / tool_name / step_name
        if hooks_dir.exists():
            hook_files = sorted(
                f for f in hooks_dir.iterdir()
                if (
                    f.is_file()
                    and not f.name.startswith('.')
                    and self._is_effective_hook_file(f)
                )
            )
            if hook_files:
                lines.append(f"# --- hooks/{tool_name}/{step_name} (proc definitions) ---")
                for f in hook_files:
                    lines.append(f"source {_posix(f.resolve())}")
                lines.append("")

        return '\n'.join(lines)

    # ── Config Source ──

    def _build_config_source(self, tool_name: str, step_name: str) -> str:
        """生成 config.tcl 的 source 语句"""
        config_path = self.workdir_path / "cmds" / tool_name / f"{step_name}_config.tcl"
        lines = [
            "# ============================================================",
            "# Config Variables",
            f"# Generated from: base -> overlay -> user_config",
            f"# See {config_path.name} for details and variable tracing",
            "# ============================================================",
            "",
            f"source {_posix(config_path.resolve())}",
            "",
        ]
        return '\n'.join(lines)

    # ── Phase 2: Execute ──

    def _build_execute_phase(self, tool_name: str, step_name: str) -> str:
        lines = [
            "# ============================================================",
            "# Phase 2: Execute",
            "# ============================================================",
            ""
        ]

        if not self.registry.has_step(tool_name, step_name):
            lines.append(f"# WARNING: step '{step_name}' not found in {tool_name}")
            return '\n'.join(lines)

        sub_specs = self.registry.get_sub_step_specs(tool_name, step_name)
        steps_dir = self.flow_base_path / "cmds" / tool_name / "steps" / step_name

        for spec in sub_specs:
            sub = spec.get("name", "")
            runner = spec.get("runner", "tcl")
            if runner == "shell":
                cmd = spec.get("command", "")
                lines.append(f"# shell sub-step: {sub}")
                if cmd:
                    lines.append(f'puts ">>> [shell:{sub}] {cmd}"')
                    lines.append(f'if {{[catch {{exec bash -lc "{cmd.replace(chr(34), chr(92)+chr(34))}"}} err]}} {{')
                    lines.append(f'    error "shell sub-step {sub} failed: $err"')
                    lines.append("}")
                else:
                    script_file = steps_dir / f"{sub}.sh"
                    source_comment = _posix(script_file.resolve()) if script_file.exists() else f"{_posix(script_file)} (not found)"
                    lines.append(f"# {source_comment}")
                    lines.append(f'if {{![file exists "{_posix(script_file)}"]}} {{')
                    lines.append(f'    error "shell sub-step script not found: {_posix(script_file)}"')
                    lines.append("}")
                    lines.append(f'if {{[catch {{exec bash "{_posix(script_file.resolve())}"}} err]}} {{')
                    lines.append(f'    error "shell sub-step {sub} failed: $err"')
                    lines.append("}")
                lines.append("")
                continue

            sub_file = steps_dir / f"{sub}.tcl"
            source_comment = _posix(sub_file.resolve()) if sub_file.exists() else f"{_posix(sub_file)} (not found)"
            lines.append(f"# {source_comment}")
            lines.append("")
            lines.append(sub)
            lines.append("")

        return '\n'.join(lines)

    # ── Hooks ──

    def _find_step_hook(self, tool_name: str, step_name: str,
                         hook_type: str) -> Optional[Path]:
        """查找 step 级 hook（step.pre / step.post），仅工作目录生效。"""
        hooks_dir = self.workdir_path / "hooks" / tool_name / step_name
        hook_file = hooks_dir / f"step.{hook_type}"
        if hook_file.exists():
            return hook_file
        return None

    def _find_sub_step_hook(self, tool_name: str, step_name: str,
                            sub_step: str, hook_type: str) -> Optional[Path]:
        """查找 sub-step 级 hook（例如 global_place.pre/post），仅工作目录生效。"""
        filename = f"{sub_step}.{hook_type}"
        hooks_dir = self.workdir_path / "hooks" / tool_name / step_name
        hook_file = hooks_dir / filename
        if hook_file.exists():
            return hook_file
        return None

    @staticmethod
    def _is_effective_hook_file(hook_file: Path) -> bool:
        """判断 hook 文件是否是有效自定义实现（过滤 init 默认模板）。"""
        if not hook_file.exists() or not hook_file.is_file():
            return False
        content = hook_file.read_text(encoding='utf-8').strip()
        if not content:
            return False
        # init 生成的默认模板占位内容，不应被执行或调用
        if "your code here" in content.lower():
            return False
        return True

    # ── Header ──

    def _build_header(self, tool_name: str, step_name: str) -> str:
        return _build_header(self, tool_name, step_name)

    # ── LSF Config ──

    _COND_PATTERN = re.compile(r'\{(\w+)\}')
    _EDP_PATTERN = re.compile(r'\$edp\((\w+)\)')
    _VAR_PATTERN = re.compile(r'\$(\w+)')
    _UNSAFE_SHELL_PATTERNS = ("&&", "||", ";", "$(", "`", "\n", "\r")
    _PROC_DEF_PATTERN = re.compile(r'^\s*proc\s+([^\s\{]+)\s*\{', re.MULTILINE)

    def _load_config_dict(self, tool_name: str) -> dict:
        """加载 config.yaml 覆盖链，返回原始字典"""
        config_files = []
        base_config = self.flow_base_path / "cmds" / tool_name / "config.yaml"
        if base_config.exists():
            config_files.append(base_config)
        if self.overlay_path:
            overlay_config = self.overlay_path / "cmds" / tool_name / "config.yaml"
            if overlay_config.exists():
                config_files.append(overlay_config)
        user_config = self.workdir_path / "user_config.yaml"
        if user_config.exists():
            config_files.append(user_config)

        if not config_files:
            return {}

        try:
            return yamlfiles2dict(*config_files, expand_variables=False)
        except Exception:
            return {}

    def get_lsf_config(self, tool_name: str, step_name: str) -> dict:
        """解析 LSF 配置（tool 级 → step 级覆盖）

        Returns:
            {'lsf_mode': 0|1, 'cpu_num': int, 'queue': str, ...}
        """
        config = self._load_config_dict(tool_name)
        tool_config = config.get(tool_name, {})
        if not isinstance(tool_config, dict):
            return {'lsf_mode': 0}

        result = {}

        # tool 级 lsf 配置
        tool_lsf = tool_config.get('lsf', {})
        if isinstance(tool_lsf, dict):
            for key in [
                'lsf_mode', 'cpu_num', 'queue', 'mem_limit',
                'wall_time', 'extra_opts', 'job_name', 'hosts'
            ]:
                if key in tool_lsf:
                    result[key] = tool_lsf[key]

        # step 级 lsf 配置（覆盖 tool 级）
        step_config = tool_config.get(step_name, {})
        if isinstance(step_config, dict):
            step_lsf = step_config.get('lsf', {})
            if isinstance(step_lsf, dict):
                for key in [
                    'lsf_mode', 'cpu_num', 'queue', 'mem_limit',
                    'wall_time', 'extra_opts', 'job_name', 'hosts'
                ]:
                    if key in step_lsf:
                        result[key] = step_lsf[key]

        # 类型转换
        if 'lsf_mode' in result:
            result['lsf_mode'] = int(result['lsf_mode'])
        if 'cpu_num' in result:
            result['cpu_num'] = int(result['cpu_num'])

        if result.get('lsf_mode', 0) == 0:
            return {'lsf_mode': 0}

        return result

    # ── Invoke Resolution ──

    def _resolve_invoke(self, tool_name: str, step_name: str,
                        debug: bool = False) -> str:
        """解析 invoke 列表，拼接成完整命令"""
        return _resolve_invoke(self, tool_name, step_name, debug=debug)

    def _validate_safe_invoke_item(self, item: str, tool_name: str, step_name: str) -> None:
        """阻断高风险 shell 注入片段。"""
        _validate_safe_invoke_item(self, item, tool_name, step_name)

    # ── .sh Generation ──

    def build_step_shell(self, tool_name: str, step_name: str,
                         debug: bool = False,
                         shell_type: Optional[str] = None) -> str:
        """生成 .sh 启动脚本"""
        return _build_step_shell(self, tool_name, step_name, debug=debug, shell_type=shell_type)

    # ── Debug Script Generation ──

    def build_debug_script(self, tool_name: str, step_name: str) -> str:
        """生成 debug 版脚本：定义所有 proc，不自动执行，加载 edp_debug 交互 CLI"""
        return _build_debug_script(self, tool_name, step_name)
