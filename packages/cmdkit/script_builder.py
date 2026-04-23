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

from configkit import yamlfiles2dict, files2tcl
from flowkit.loader.step_loader import StepRegistry


def _posix(p: Path) -> str:
    """将路径转换为正斜杠格式（Tcl 兼容）"""
    return str(p).replace('\\', '/')


def _source_block(lines: list, comment: str, search_dir: Path,
                  exclude: Optional[List[str]] = None,
                  source_tag: Optional[str] = None) -> None:
    """向 lines 追加一个 source 块，只有目录存在且有 .tcl 文件时才追加"""
    if not search_dir.exists():
        return
    exclude = exclude or []
    tcl_files = sorted(
        f for f in search_dir.glob("*.tcl")
        if not f.name.startswith("README") and f.name not in exclude
    )
    if not tcl_files:
        return
    lines.append(f"# --- {comment} ---")
    for f in tcl_files:
        if source_tag:
            lines.append(f"# [{source_tag}] source {_posix(f.resolve())}")
        lines.append(f"source {_posix(f.resolve())}")
    lines.append("")


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
        self.common_packages_path = (
            Path(common_packages_path) if common_packages_path
            else flow_base_path.parent.parent.parent.parent.parent / "common_packages"
        )
        self.preferred_shell = self._detect_shell(preferred_shell)

        self.registry = StepRegistry()
        self.registry.load_with_override(self.flow_base_path, self.overlay_path)

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
        config_files = []

        def _find_config(directory: Path, filename_stem: str) -> Optional[Path]:
            """在目录下找 config 文件，优先 .yaml，fallback .tcl"""
            yaml_path = directory / f"{filename_stem}.yaml"
            if yaml_path.exists():
                return yaml_path
            tcl_path = directory / f"{filename_stem}.tcl"
            if tcl_path.exists():
                return tcl_path
            return None

        # 1. base config
        cfg = _find_config(self.flow_base_path / "cmds" / tool_name, "config")
        if cfg:
            config_files.append(cfg)

        # 2. overlay config
        if self.overlay_path:
            cfg = _find_config(self.overlay_path / "cmds" / tool_name, "config")
            if cfg:
                config_files.append(cfg)

        # 3. user config
        cfg = _find_config(self.workdir_path, "user_config")
        if cfg:
            config_files.append(cfg)

        output_path = self.workdir_path / "cmds" / tool_name / f"{step_name}_config.tcl"

        if not config_files:
            # 没有 config 文件，写一个空带 header 的
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                "# Generated by ConfigKit\n# No config files found.\n",
                encoding='utf-8'
            )
            return output_path

        edp_vars = self._build_edp_vars(tool_name, step_name)

        # 生成，并追加加载顺序说明
        result = files2tcl(
            *config_files,
            output_file=output_path,
            edp_vars=edp_vars,
        )

        # 在文件头部插入加载顺序说明
        content = result.read_text(encoding='utf-8')
        header_lines = [
            "# Config loading order (later overrides earlier):",
        ]
        for i, f in enumerate(config_files, 1):
            header_lines.append(f"#   {i}. {f.resolve()}")
        header_lines.append("#")
        header_lines.append("# [override] = this file changed a value from an earlier file, [new] = new variable.")
        header_lines.append("#")

        new_content = content.replace(
            "# Generated by ConfigKit\n",
            "# Generated by ConfigKit\n" + '\n'.join(header_lines) + "\n",
            1,
        )
        result.write_text(new_content, encoding='utf-8')

        return result

    # ── 主入口 ──

    def build_step_script(self, tool_name: str, step_name: str) -> str:
        """生成某个 step 的完整 Tcl 脚本"""
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
            sub_steps = self.registry.get_sub_steps(tool_name, step_name)
            has_any = False
            for sub in sub_steps:
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
                if f.is_file() and not f.name.startswith('.')
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

        sub_steps = self.registry.get_sub_steps(tool_name, step_name)
        steps_dir = self.flow_base_path / "cmds" / tool_name / "steps" / step_name

        # step.pre hook
        step_pre = self._find_step_hook(tool_name, step_name, "pre")
        if step_pre:
            proc_name = f"{step_name}_step_pre"
            lines.append(f"# --- step.pre: {proc_name} ---")
            lines.append(f"if {{[info procs {proc_name}] ne \"\"}} {{ {proc_name} }}")
            lines.append("")

        for sub in sub_steps:
            sub_file = steps_dir / f"{sub}.tcl"
            source_comment = _posix(sub_file.resolve()) if sub_file.exists() else f"{_posix(sub_file)} (not found)"
            lines.append(f"# {source_comment}")
            lines.append("")

            # sub_step.pre hook
            pre_proc = f"{step_name}_{sub}_pre"
            lines.append(f"if {{[info procs {pre_proc}] ne \"\"}} {{ {pre_proc} }}")

            # sub_step call
            lines.append(sub)
            lines.append("")

            # sub_step.post hook
            post_proc = f"{step_name}_{sub}_post"
            lines.append(f"if {{[info procs {post_proc}] ne \"\"}} {{ {post_proc} }}")
            lines.append("")

        # step.post hook
        step_post = self._find_step_hook(tool_name, step_name, "post")
        if step_post:
            proc_name = f"{step_name}_step_post"
            lines.append(f"# --- step.post: {proc_name} ---")
            lines.append(f"if {{[info procs {proc_name}] ne \"\"}} {{ {proc_name} }}")
            lines.append("")

        return '\n'.join(lines)

    # ── Hooks ──

    def _find_step_hook(self, tool_name: str, step_name: str,
                         hook_type: str) -> Optional[Path]:
        """查找 step 级 hook（step.pre / step.post）"""
        # workdir 优先
        hooks_dir = self.workdir_path / "hooks" / tool_name / step_name
        hook_file = hooks_dir / f"step.{hook_type}"
        if hook_file.exists():
            return hook_file
        # overlay
        if self.overlay_path:
            hook_file = self.overlay_path / "hooks" / tool_name / step_name / f"step.{hook_type}"
            if hook_file.exists():
                return hook_file
        # base
        hook_file = self.flow_base_path / "hooks" / tool_name / step_name / f"step.{hook_type}"
        if hook_file.exists():
            return hook_file
        return None

    # ── Header ──

    def _build_header(self, tool_name: str, step_name: str) -> str:
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        parts = self.flow_base_path.parts
        try:
            idx = parts.index("initialize")
            foundry = parts[idx + 1] if idx + 1 < len(parts) else "?"
            node = parts[idx + 2] if idx + 2 < len(parts) else "?"
        except ValueError:
            foundry = "?"
            node = "?"

        project = self.overlay_path.name if self.overlay_path else "common"

        lines = [
            "# ============================================================",
            "# Generated by EDP Framework",
            f"# Foundry: {foundry}  Node: {node}  Project: {project}",
            f"# Step: {step_name}  Tool: {tool_name}",
        ]

        # sub_steps 信息
        if self.registry.has_step(tool_name, step_name):
            sub_steps = self.registry.get_sub_steps(tool_name, step_name)
            lines.append(f"# Sub-steps: {' -> '.join(sub_steps)}")

        lines.extend([
            f"# Generated at: {now}",
            f"# Flow base: {_posix(self.flow_base_path.resolve())}",
            "# ============================================================",
        ])

        return '\n'.join(lines)

    # ── LSF Config ──

    _COND_PATTERN = re.compile(r'\{(\w+)\}')
    _EDP_PATTERN = re.compile(r'\$edp\((\w+)\)')
    _VAR_PATTERN = re.compile(r'\$(\w+)')

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
            for key in ['lsf_mode', 'cpu_num', 'queue', 'mem_limit', 'job_name']:
                if key in tool_lsf:
                    result[key] = tool_lsf[key]

        # step 级 lsf 配置（覆盖 tool 级）
        step_config = tool_config.get(step_name, {})
        if isinstance(step_config, dict):
            step_lsf = step_config.get('lsf', {})
            if isinstance(step_lsf, dict):
                for key in ['lsf_mode', 'cpu_num', 'queue', 'mem_limit', 'job_name']:
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
        invoke_list = self.registry.get_invoke(tool_name, step_name)
        if not invoke_list:
            return ""

        edp_vars = self._build_edp_vars(tool_name, step_name, debug=debug)
        config = self._load_config_dict(tool_name)
        tool_config = config.get(tool_name, {})

        def _resolve_var(var_name: str) -> str:
            """从 edp_vars → config 查找变量值"""
            if var_name in edp_vars:
                return edp_vars[var_name]
            # step 级
            step_cfg = tool_config.get(step_name, {})
            if isinstance(step_cfg, dict) and var_name in step_cfg:
                return str(step_cfg[var_name])
            # tool 级
            if var_name in tool_config:
                return str(tool_config[var_name])
            return ""

        resolved_items = []
        for item in invoke_list:
            # 条件变量 {var}
            cond_vars = self._COND_PATTERN.findall(item)
            if cond_vars:
                all_resolved = True
                resolved = item
                for var_name in cond_vars:
                    value = _resolve_var(var_name)
                    if not value:
                        all_resolved = False
                        break
                    resolved = resolved.replace(f"{{{var_name}}}", value)
                if not all_resolved:
                    continue
                item = resolved

            # $edp(var)
            for var_name in self._EDP_PATTERN.findall(item):
                value = edp_vars.get(var_name, "")
                item = item.replace(f"$edp({var_name})", value)

            # $var（必选变量）
            for var_name in self._VAR_PATTERN.findall(item):
                value = _resolve_var(var_name)
                item = item.replace(f"${var_name}", value)

            resolved_items.append(item)

        return " ".join(resolved_items)

    # ── .sh Generation ──

    def build_step_shell(self, tool_name: str, step_name: str,
                         debug: bool = False,
                         shell_type: Optional[str] = None) -> str:
        """生成 .sh 启动脚本"""
        command = self._resolve_invoke(tool_name, step_name, debug=debug)
        if not command:
            return ""

        run_dir = self.workdir_path / "runs" / tool_name / step_name
        tcl_path = self.workdir_path / "cmds" / tool_name / f"{step_name}.tcl"

        actual_shell = self._detect_shell(shell_type) if shell_type else self.preferred_shell
        shebang = "#!/bin/bash" if actual_shell == "bash" else "#!/bin/csh"
        lines = [
            shebang,
            f"# Generated by EDP Framework",
            f"# Step: {step_name}  Tool: {tool_name}",
            f"# Run directory: {_posix(run_dir.resolve())}",
            "",
            f"cd {_posix(run_dir.resolve())}",
            command,
        ]
        return '\n'.join(lines)

    # ── Debug Script Generation ──

    def build_debug_script(self, tool_name: str, step_name: str) -> str:
        """生成 debug 版脚本：定义所有 proc，不自动执行，加载 edp_debug 交互 CLI"""
        lines = [
            "# ============================================================",
            "# EDP Debug Mode",
            f"# Step: {step_name}  Tool: {tool_name}",
            "# Source this file in your tool's Tcl shell for interactive debug.",
            "# ============================================================",
            "",
        ]

        # Phase 1: Source (packages, procs, sub_step procs, hook procs)
        # NOTE: exclude edp_debug.tcl — it auto-inits and needs edp() vars from config
        source_section = self._build_source_phase(
            tool_name, step_name, exclude=['edp_debug.tcl']
        )
        if source_section:
            lines.append(source_section)

        # Config: source config.tcl (edp(sub_steps) etc. will be set here)
        config_section = self._build_config_source(tool_name, step_name)
        if config_section:
            lines.append(config_section)

        # Load edp_debug.tcl (reads edp(sub_steps) to build plan, auto-inits)
        debug_pkg = self.common_packages_path / "tcl_packages" / "default" / "edp_debug.tcl"
        if debug_pkg.exists():
            lines.append(f"# Load debug CLI")
            lines.append(f"source {_posix(debug_pkg.resolve())}")
        else:
            lines.append(f"# WARNING: edp_debug.tcl not found at {_posix(debug_pkg)}")

        return '\n'.join(lines)
