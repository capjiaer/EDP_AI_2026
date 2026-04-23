#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
from pathlib import Path
from typing import List, Optional

from ._script_utils import _posix


def collect_source_files(builder, tool_name: str, step_name: str,
                         exclude: Optional[List[str]] = None) -> List[Path]:
    """收集 Phase 1 中将被 source 的 Tcl 文件（按加载顺序）。"""
    exclude = set(exclude or [])
    source_files: List[Path] = []

    def _append_glob_files(directory: Path) -> None:
        if not directory.exists():
            return
        for f in sorted(directory.glob("*.tcl")):
            if f.name.startswith("README") or f.name in exclude:
                continue
            source_files.append(f.resolve())

    _append_glob_files(builder.common_packages_path / "tcl_packages" / "default")
    _append_glob_files(builder.common_packages_path / "tcl_packages" / tool_name)
    _append_glob_files(builder.flow_base_path / "tcl_packages")
    if builder.overlay_path:
        _append_glob_files(builder.overlay_path / "tcl_packages")
    _append_glob_files(builder.flow_base_path / "cmds" / tool_name / "procs")
    _append_glob_files(builder.flow_base_path / "cmds" / tool_name / "vendor_procs")

    if builder.registry.has_step(tool_name, step_name):
        steps_dir = builder.flow_base_path / "cmds" / tool_name / "steps" / step_name
        for sub in builder.registry.get_sub_steps(tool_name, step_name):
            sub_file = steps_dir / f"{sub}.tcl"
            if sub_file.exists():
                source_files.append(sub_file.resolve())

    hooks_dir = builder.workdir_path / "hooks" / tool_name / step_name
    if hooks_dir.exists():
        hook_files = sorted(
            f for f in hooks_dir.iterdir()
            if (
                f.is_file()
                and not f.name.startswith('.')
                and builder._is_effective_hook_file(f)
            )
        )
        source_files.extend(f.resolve() for f in hook_files)

    return source_files


def pretty_conflict_path(builder, file_path: str) -> str:
    """将冲突路径格式化为更易读的相对路径。"""
    p = Path(file_path)
    bases = [
        builder.workdir_path.resolve(),
        builder.flow_base_path.resolve(),
        builder.common_packages_path.resolve(),
    ]
    if builder.overlay_path:
        bases.append(builder.overlay_path.resolve())

    for base in bases:
        try:
            rel = p.resolve().relative_to(base)
            return f"{base.name}/{_posix(rel)}"
        except Exception:
            continue
    return _posix(p.resolve())


def validate_proc_conflicts(builder, tool_name: str, step_name: str) -> None:
    """检查 source 链路中的 proc 定义冲突（同名跨文件定义）。"""
    proc_to_files = defaultdict(list)
    for tcl_file in collect_source_files(builder, tool_name, step_name):
        try:
            content = tcl_file.read_text(encoding='utf-8')
        except Exception:
            continue
        for proc_name in builder._PROC_DEF_PATTERN.findall(content):
            proc_to_files[proc_name].append(tcl_file)

    conflicts = {}
    for proc_name, files in proc_to_files.items():
        unique_files = []
        seen = set()
        for f in files:
            s = str(f)
            if s not in seen:
                seen.add(s)
                unique_files.append(s)
        if len(unique_files) > 1:
            conflicts[proc_name] = unique_files

    if not conflicts:
        return

    details = []
    for proc_name, files in sorted(conflicts.items()):
        details.append(f"- {proc_name}")
        for f in files:
            details.append(f"    - {pretty_conflict_path(builder, f)}")
    raise ValueError(
        f"Proc definition conflicts detected for {tool_name}.{step_name}:\n"
        + "\n".join(details)
    )
