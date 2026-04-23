#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit.dirkit - 目录和文件操作工具

提供文件和目录的复制、链接、创建等操作功能。
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union


class DirKit:
    """目录和文件操作工具类"""

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化 DirKit

        Args:
            base_path: 基础路径，所有操作将相对于此路径
        """
        self.base_path = Path(base_path) if base_path else None

    def _resolve(self, path: Union[str, Path]) -> Path:
        """解析路径，如果设置了 base_path 则相对于 base_path"""
        path = Path(path)
        if self.base_path:
            return self.base_path / path
        return path

    def ensure_dir(self, dir_path: Union[str, Path]) -> Path:
        """
        确保目录存在，如果不存在则创建

        Args:
            dir_path: 目录路径

        Returns:
            目录的 Path 对象
        """
        dir_path = self._resolve(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path],
                  overwrite: bool = True) -> Path:
        """
        复制文件

        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            目标文件的 Path 对象

        Raises:
            FileNotFoundError: 源文件不存在
            FileExistsError: 目标文件已存在且 overwrite=False
        """
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src_path}")

        dst_path = self._resolve(dst)

        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在: {dst_path}")

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return dst_path

    def copy_dir(self, src: Union[str, Path], dst: Union[str, Path],
                 overwrite: bool = True, ignore: Optional[List[str]] = None) -> Path:
        """
        复制目录

        Args:
            src: 源目录路径
            dst: 目标目录路径
            overwrite: 是否覆盖已存在的文件
            ignore: 忽略的文件/目录名称列表

        Returns:
            目标目录的 Path 对象
        """
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f"源目录不存在: {src_path}")
        if not src_path.is_dir():
            raise ValueError(f"源路径不是目录: {src_path}")

        dst_path = self._resolve(dst)

        if dst_path.exists() and overwrite:
            shutil.rmtree(dst_path)
        elif dst_path.exists():
            raise FileExistsError(f"目标目录已存在: {dst_path}")

        dst_path.parent.mkdir(parents=True, exist_ok=True)

        if ignore:
            def ignore_func(directory, files):
                return [f for f in files
                        if f in ignore or any(f.startswith(i + os.sep) for i in ignore)]
            shutil.copytree(src_path, dst_path, ignore=ignore_func)
        else:
            shutil.copytree(src_path, dst_path)

        return dst_path

    def link_file(self, src: Union[str, Path], dst: Union[str, Path],
                  overwrite: bool = True) -> Path:
        """
        创建文件的符号链接

        Args:
            src: 源文件路径
            dst: 目标链接路径
            overwrite: 是否覆盖已存在的链接

        Returns:
            目标链接的 Path 对象
        """
        src_path = Path(src).resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src_path}")

        dst_path = self._resolve(dst)

        if dst_path.exists() or dst_path.is_symlink():
            if overwrite:
                dst_path.unlink()
            else:
                raise FileExistsError(f"目标链接已存在: {dst_path}")

        dst_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            rel_src = os.path.relpath(src_path, dst_path.parent)
            dst_path.symlink_to(rel_src)
        except (OSError, ValueError):
            dst_path.symlink_to(src_path)

        return dst_path

    def link_dir(self, src: Union[str, Path], dst: Union[str, Path],
                 overwrite: bool = True) -> Path:
        """
        创建目录的符号链接

        Args:
            src: 源目录路径
            dst: 目标链接路径
            overwrite: 是否覆盖已存在的链接

        Returns:
            目标链接的 Path 对象
        """
        src_path = Path(src).resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"源目录不存在: {src_path}")
        if not src_path.is_dir():
            raise ValueError(f"源路径不是目录: {src_path}")

        dst_path = self._resolve(dst)

        if dst_path.exists() or dst_path.is_symlink():
            if overwrite:
                if dst_path.is_symlink():
                    dst_path.unlink()
                else:
                    shutil.rmtree(dst_path)
            else:
                raise FileExistsError(f"目标链接已存在: {dst_path}")

        dst_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            rel_src = os.path.relpath(src_path, dst_path.parent)
            dst_path.symlink_to(rel_src, target_is_directory=True)
        except (OSError, ValueError):
            dst_path.symlink_to(src_path, target_is_directory=True)

        return dst_path

    def remove(self, path: Union[str, Path], recursive: bool = False) -> bool:
        """
        删除文件或目录

        Args:
            path: 要删除的路径
            recursive: 如果是目录，是否递归删除

        Returns:
            是否成功删除
        """
        target_path = self._resolve(path)

        if not target_path.exists():
            return False

        try:
            if target_path.is_symlink():
                target_path.unlink()
            elif target_path.is_file():
                target_path.unlink()
            elif target_path.is_dir():
                if recursive:
                    shutil.rmtree(target_path)
                else:
                    target_path.rmdir()
            return True
        except Exception:
            return False

    def find_files(self, pattern: str, root: Optional[Union[str, Path]] = None,
                   recursive: bool = True) -> List[Path]:
        """
        查找匹配模式的文件

        Args:
            pattern: 文件名模式（支持通配符）
            root: 搜索根目录，默认使用 base_path
            recursive: 是否递归搜索

        Returns:
            匹配的文件路径列表
        """
        search_root = self.base_path if self.base_path else Path(root or '.')
        if not search_root.exists():
            return []

        if recursive:
            matches = list(search_root.rglob(pattern))
        else:
            matches = list(search_root.glob(pattern))

        return [m for m in matches if m.is_file()]

    def find_dirs(self, pattern: str, root: Optional[Union[str, Path]] = None,
                  recursive: bool = True) -> List[Path]:
        """
        查找匹配模式的目录

        Args:
            pattern: 目录名模式（支持通配符）
            root: 搜索根目录，默认使用 base_path
            recursive: 是否递归搜索

        Returns:
            匹配的目录路径列表
        """
        search_root = self.base_path if self.base_path else Path(root or '.')
        if not search_root.exists():
            return []

        if recursive:
            matches = list(search_root.rglob(pattern))
        else:
            matches = list(search_root.glob(pattern))

        return [m for m in matches if m.is_dir()]
