#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit.work_path - 工作路径初始化

在 WORK_PATH 下创建项目/块/用户/分支的目录结构。
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union

import yaml
from datetime import datetime

from ..dirkit import DirKit
from ..project_finder import ProjectFinder
from ..branch_linker import (
    BranchLinker, parse_branch_step,
    save_branch_source, load_branch_source
)

logger = logging.getLogger(__name__)


def get_current_user() -> str:
    """获取当前用户名"""
    for env_var in ['USER', 'USERNAME', 'LOGNAME']:
        user = os.environ.get(env_var)
        if user:
            return user
    import getpass
    try:
        return getpass.getuser()
    except Exception:
        return "unknown_user"


def _ensure_shared_dir(path: Path) -> None:
    """确保目录对同组/其他用户可写，让其他人也能在其下创建子目录。

    使用 setgid (2xxx) + group rwx，新文件自动继承组。
    如果权限设置失败（如 NFS root_squash），静默忽略——权限可能已被 admin 预设好。
    """
    try:
        os.chmod(path, 0o2777)
    except OSError:
        pass


class WorkPathInitializer:
    """工作路径初始化器"""

    DEFAULT_BRANCH_DIRS = ['cmds', 'data', 'hooks', 'runs']
    DEFAULT_BRANCH_FILES = ['user_config.tcl', 'user_config.yaml']

    def __init__(self, edp_center_path: Union[str, Path]):
        """
        初始化 WorkPathInitializer

        Args:
            edp_center_path: edp_center 资源库路径
        """
        self.edp_center = Path(edp_center_path)
        if not self.edp_center.exists():
            raise FileNotFoundError(f"edp_center 不存在: {self.edp_center}")

        self.initialize_path = self.edp_center / "flow" / "initialize"
        self.project_finder = ProjectFinder(self.initialize_path)
        self.branch_linker = BranchLinker()

    # --- 项目查找（委托给 ProjectFinder）---

    def find_project(self, project_name: str) -> List[Dict[str, str]]:
        return self.project_finder.find_project(project_name)

    def get_project_info(self, project_name: str,
                         foundry: Optional[str] = None,
                         node: Optional[str] = None) -> Dict[str, str]:
        return self.project_finder.get_project_info(project_name, foundry, node)

    def list_projects(self, foundry: Optional[str] = None,
                      node: Optional[str] = None) -> List[Dict[str, str]]:
        return self.project_finder.list_projects(foundry, node)

    def resolve_context(self, path: Union[str, Path] = None) -> Optional[Dict[str, str]]:
        """从路径推断项目上下文（向上查找 .edp_version）"""
        if path is None:
            path = Path.cwd()
        return self.project_finder.resolve_context(Path(path))

    # --- 版本信息 ---

    def _create_or_update_version(self, project_path: Path,
                                  project_name: str, project_node: str,
                                  foundry: str, node: str, blocks: List[str]) -> None:
        """创建或更新 .edp_version 文件"""
        import getpass
        now = datetime.now().isoformat()
        user = getpass.getuser()
        version_file = project_path / '.edp_version'

        if version_file.exists():
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    info = yaml.safe_load(f) or {}
            except Exception:
                info = {}
            info.setdefault('blocks', {})
            if 'version' not in info:
                info['version'] = project_node
        else:
            info = {
                'project': project_name,
                'version': project_node,
                'foundry': foundry,
                'node': node,
                'created_at': now,
                'created_by': user,
                'blocks': {},
            }

        for block_name in blocks:
            if block_name not in info['blocks']:
                info['blocks'][block_name] = {
                    'created_at': now,
                    'created_by': user,
                    'users': {},
                }

        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                yaml.dump(info, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
        except Exception:
            pass

    # --- 版本记录 ---

    def _record_user_branch(self, project_path: Path, block_name: str,
                            user_name: str, branch_name: str) -> None:
        """在 .edp_version 中记录 user/branch 信息"""
        version_file = project_path / '.edp_version'
        if not version_file.exists():
            return

        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                info = yaml.safe_load(f) or {}
        except Exception:
            return

        info.setdefault('blocks', {})
        block_info = info['blocks'].setdefault(block_name, {
            'created_at': datetime.now().isoformat(),
            'created_by': user_name,
            'users': {},
        })

        users = block_info.setdefault('users', {})
        user_info = users.setdefault(user_name, {'branches': {}})
        branches = user_info.setdefault('branches', {})

        if branch_name not in branches:
            branches[branch_name] = {
                'created_at': datetime.now().isoformat(),
            }

        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                yaml.dump(info, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
        except Exception:
            pass

    # --- 分支结构 ---

    def _create_branch_structure(self, branch_path: Path,
                                  flow_base_path: Optional[Path] = None,
                                  flow_overlay_path: Optional[Path] = None) -> Dict[str, Path]:
        """创建分支目录结构（cmds, data, hooks, runs + 配置文件）+ hook 模板"""
        branch_path.mkdir(parents=True, exist_ok=True)

        created_dirs = {}
        for dir_name in self.DEFAULT_BRANCH_DIRS:
            (branch_path / dir_name).mkdir(parents=True, exist_ok=True)
            created_dirs[dir_name] = branch_path / dir_name

        created_files = {}
        for file_name in self.DEFAULT_BRANCH_FILES:
            file_path = branch_path / file_name
            if not file_path.exists():
                file_path.touch()
            created_files[file_name] = file_path

        # 生成 hook 模板文件
        if flow_base_path:
            self._generate_hook_templates(branch_path / "hooks",
                                           flow_base_path, flow_overlay_path)

        return {
            'directories': created_dirs,
            'files': created_files,
            'branch_path': branch_path,
        }

    def _generate_hook_templates(self, hooks_dir: Path,
                                  flow_base_path: Path,
                                  flow_overlay_path: Optional[Path]) -> None:
        """根据 step.yaml 预建 hook 模板文件，让 user 知道有哪些 hook 点可用。"""
        from flowkit.loader.step_loader import StepRegistry

        registry = StepRegistry()
        registry.load_with_override(flow_base_path, flow_overlay_path)

        all_tools = registry.get_all_tools()
        all_globals = "global edp " + " ".join(all_tools)

        for tool_name in all_tools:
            tool_hooks_dir = hooks_dir / tool_name
            tool_hooks_dir.mkdir(parents=True, exist_ok=True)

            for step_name, step_data in registry.get_tool_steps(tool_name).items():
                sub_steps = step_data.get('sub_steps', [])
                step_hooks_dir = tool_hooks_dir / step_name
                step_hooks_dir.mkdir(parents=True, exist_ok=True)

                # step 级 hooks
                self._write_hook_template(
                    step_hooks_dir / "step.pre",
                    f"Step-level pre hook for {tool_name}.{step_name}\n"
                    f"Runs before ALL sub_steps of {step_name}.",
                    proc_name=f"{step_name}_step_pre",
                    globals_str=all_globals,
                )
                self._write_hook_template(
                    step_hooks_dir / "step.post",
                    f"Step-level post hook for {tool_name}.{step_name}\n"
                    f"Runs after ALL sub_steps of {step_name}.",
                    proc_name=f"{step_name}_step_post",
                    globals_str=all_globals,
                )

                # sub_step 级 hooks
                for sub in sub_steps:
                    self._write_hook_template(
                        step_hooks_dir / f"{sub}.pre",
                        f"Pre hook for sub_step '{sub}' in {tool_name}.{step_name}\n"
                        f"Runs before {sub}().",
                        proc_name=f"{step_name}_{sub}_pre",
                        globals_str=all_globals,
                    )
                    self._write_hook_template(
                        step_hooks_dir / f"{sub}.post",
                        f"Post hook for sub_step '{sub}' in {tool_name}.{step_name}\n"
                        f"Runs after {sub}().",
                        proc_name=f"{step_name}_{sub}_post",
                        globals_str=all_globals,
                    )
                    self._write_hook_template(
                        step_hooks_dir / f"{sub}.replace",
                        f"Replace hook for sub_step '{sub}' in {tool_name}.{step_name}\n"
                        f"Replaces the entire {sub}() call.\n"
                        f"Write your own implementation below.",
                        proc_name=f"{step_name}_{sub}_replace",
                        globals_str=all_globals,
                    )

    @staticmethod
    def _write_hook_template(file_path: Path, description: str,
                              proc_name: str = "", globals_str: str = "") -> None:
        """写入 hook 模板文件（proc 定义模板，不覆盖已有文件）"""
        if file_path.exists():
            return  # 不覆盖用户已有的 hook

        lines = [
            f"# {description}",
            f"# Fill in your code inside the proc body, or delete this file if not needed.",
            "",
        ]
        if proc_name:
            lines.append(f"proc {proc_name} {{}} {{")
            if globals_str:
                lines.append(f"    {globals_str}")
            lines.append("")
            lines.append(f"    # Your code here")
            lines.append(f"}}")
        else:
            lines.append("# Your code here")

        lines.append("")
        file_path.write_text('\n'.join(lines), encoding='utf-8')

    # --- 核心接口 ---

    def init_project(self, work_path: Union[str, Path],
                     project_name: str,
                     project_node: str,
                     blocks: Optional[List[str]] = None,
                     foundry: Optional[str] = None,
                     node: Optional[str] = None) -> Dict[str, Path]:
        """
        初始化项目结构到 WORK_PATH 下

        Args:
            work_path: WORK_PATH 根目录路径
            project_name: 项目名称
            project_node: 项目节点名称（如 P85）
            blocks: 块名称列表
            foundry: 可选
            node: 可选

        Returns:
            创建信息字典
        """
        project_info = self.project_finder.get_project_info(project_name, foundry, node)
        foundry = project_info['foundry']
        node = project_info['node']

        work_path = Path(work_path).resolve()
        project_path = work_path / project_name / project_node

        if blocks is None:
            blocks = []

        # 创建目录（宽松权限：允许其他用户在其下创建子目录）
        project_path.mkdir(parents=True, exist_ok=True)
        _ensure_shared_dir(project_path)

        # 版本信息
        self._create_or_update_version(
            project_path, project_name, project_node, foundry, node, blocks
        )

        # 创建 blocks
        block_paths = {}
        for block_name in blocks:
            block_path = project_path / block_name
            block_path.mkdir(parents=True, exist_ok=True)
            _ensure_shared_dir(block_path)
            block_paths[block_name] = block_path

        return {
            'work_path': work_path,
            'project': project_name,
            'project_node': project_path,
            'foundry': foundry,
            'node': node,
            'blocks': block_paths,
        }

    def init_user_workspace(self,
                            work_path: Optional[Union[str, Path]] = None,
                            project_name: Optional[str] = None,
                            project_node: Optional[str] = None,
                            block_name: Optional[str] = None,
                            user_name: Optional[str] = None,
                            branch_name: str = "branch1",
                            from_branch_step: Optional[str] = None,
                            link_mode: bool = True,
                            current_dir: Optional[Union[str, Path]] = None) -> Dict:
        """
        初始化用户工作环境（创建 user/branch 目录结构）

        支持两种模式：
        1. 显式模式：提供 work_path, project_name, project_node, block_name
        2. 自动模式：从当前工作目录推断
        """
        if user_name is None:
            user_name = get_current_user()

        # 显式模式
        if work_path and project_name and project_node and block_name:
            work_path = Path(work_path).resolve()
            project_info = self.get_project_info(project_name)
            foundry = project_info['foundry']
            node = project_info['node']
        else:
            # 自动模式 — 从 cwd 向上查找 .edp_version
            detected = self.resolve_context(current_dir)
            if not detected:
                raise ValueError(
                    "无法从当前路径推断项目信息。\n"
                    "请确保在项目路径下，或显式提供所有参数。"
                )
            work_path = Path(detected['work_path']).resolve()
            project_name = detected['project_name']
            project_node = detected['project_node']
            block_name = detected.get('block_name')
            if not block_name:
                raise ValueError(
                    "当前路径未包含 block 信息。\n"
                    "请进入 block 目录，或显式提供 block_name 参数。"
                )
            foundry = detected['foundry']
            node = detected['node']

        # 构建分支路径
        branch_path = (
            work_path / project_name / project_node /
            block_name / user_name / branch_name
        )

        # flow 路径（用于生成 hook 模板）
        flow_base_path = self.initialize_path / foundry / node / 'common_prj'
        flow_overlay_path = self.initialize_path / foundry / node / project_name

        # 创建分支结构
        result = self._create_branch_structure(
            branch_path,
            flow_base_path=flow_base_path,
            flow_overlay_path=flow_overlay_path,
        )

        # 记录 user/branch 到 .edp_version
        project_path = work_path / project_name / project_node
        self._record_user_branch(project_path, block_name, user_name, branch_name)

        # 处理 from_branch_step
        if from_branch_step:
            copy_info = self.branch_linker.copy_step_from_branch(
                work_path, project_name, project_node, block_name,
                from_branch_step, branch_path, user_name, link_mode
            )

            source_branch_path = (
                work_path / project_name / project_node /
                block_name / copy_info['source_user'] / copy_info['source_branch']
            )
            linked_dirs = self.branch_linker.link_other_dirs(
                source_branch_path, branch_path, link_mode
            )

            result['copied_from'] = from_branch_step
            result['link_mode'] = link_mode
            result['linked_dirs'] = linked_dirs

            save_branch_source(branch_path, from_branch_step, copy_info, link_mode)

        return result

    def get_branch_source_info(self, branch_path: Union[str, Path]) -> Optional[Dict]:
        """获取分支来源信息"""
        return load_branch_source(Path(branch_path))
