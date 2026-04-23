#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import List, Optional


def _posix(p: Path) -> str:
    """将路径转换为正斜杠格式（Tcl 兼容）"""
    return str(p).replace("\\", "/")


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
