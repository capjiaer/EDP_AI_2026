#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dirkit 核心功能测试
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dirkit.dirkit import DirKit
from dirkit.branch_linker import BranchLinker, parse_branch_step, save_branch_source, load_branch_source
from dirkit.project_finder import ProjectFinder
from dirkit.work_path import WorkPathInitializer, get_current_user


class TestDirKit(unittest.TestCase):
    """测试 DirKit 基础操作"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dirkit = DirKit(base_path=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ensure_dir(self):
        result = self.dirkit.ensure_dir("a/b/c")
        self.assertTrue(result.exists())
        self.assertTrue(result.is_dir())

    def test_ensure_dir_idempotent(self):
        self.dirkit.ensure_dir("a")
        self.dirkit.ensure_dir("a")
        self.assertTrue((Path(self.test_dir) / "a").exists())

    def test_copy_file(self):
        src = Path(self.test_dir) / "src" / "test.txt"
        src.parent.mkdir(parents=True)
        src.write_text("hello", encoding='utf-8')

        result = self.dirkit.copy_file(str(src), "dst/test.txt")
        self.assertTrue(result.exists())
        self.assertEqual(result.read_text(encoding='utf-8'), "hello")

    def test_copy_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.dirkit.copy_file("/nonexistent/file.txt", "dst.txt")

    def test_copy_dir(self):
        src_dir = Path(self.test_dir) / "src_dir"
        src_dir.mkdir()
        (src_dir / "a.txt").write_text("a")
        (src_dir / "sub").mkdir()
        (src_dir / "sub" / "b.txt").write_text("b")

        result = self.dirkit.copy_dir(str(src_dir), "dst_dir")
        self.assertTrue(result.exists())
        self.assertTrue((result / "sub" / "b.txt").exists())

    def test_remove_file(self):
        f = Path(self.test_dir) / "test.txt"
        f.write_text("hello")
        self.assertTrue(self.dirkit.remove("test.txt"))
        self.assertFalse(f.exists())

    def test_remove_nonexistent(self):
        self.assertFalse(self.dirkit.remove("nonexistent"))

    def test_find_files(self):
        (Path(self.test_dir) / "a.txt").write_text("a")
        sub = Path(self.test_dir) / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("b")

        results = self.dirkit.find_files("*.txt")
        self.assertEqual(len(results), 2)


class TestParseBranchStep(unittest.TestCase):
    """测试分支步骤解析"""

    def test_two_dots_current_user(self):
        user, branch, step = parse_branch_step("branch1.pnr_innovus.init", "zhangsan")
        self.assertEqual(user, "zhangsan")
        self.assertEqual(branch, "branch1")
        self.assertEqual(step, "pnr_innovus.init")

    def test_three_dots_specified_user(self):
        user, branch, step = parse_branch_step("zhangsan.branch1.pnr_innovus.init", "lisi")
        self.assertEqual(user, "zhangsan")
        self.assertEqual(branch, "branch1")
        self.assertEqual(step, "pnr_innovus.init")

    def test_no_dot_raises(self):
        with self.assertRaises(ValueError):
            parse_branch_step("branch1", "zhangsan")

    def test_one_dot_raises(self):
        with self.assertRaises(ValueError):
            parse_branch_step("branch1.init", "zhangsan")


class TestProjectFinder(unittest.TestCase):
    """测试项目查找"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        config = Path(self.test_dir) / "flow" / "initialize" / "SAMSUNG" / "S8"
        config.mkdir(parents=True)
        (config / "common_prj").mkdir()
        (config / "dongting").mkdir()
        (config / "other_project").mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_project(self):
        finder = ProjectFinder(Path(self.test_dir) / "flow" / "initialize")
        results = finder.find_project("dongting")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['foundry'], 'SAMSUNG')

    def test_find_nonexistent(self):
        finder = ProjectFinder(Path(self.test_dir) / "flow" / "initialize")
        self.assertEqual(len(finder.find_project("nonexistent")), 0)

    def test_list_projects_excludes_common_prj(self):
        finder = ProjectFinder(Path(self.test_dir) / "flow" / "initialize")
        names = [p['project'] for p in finder.list_projects()]
        self.assertIn('dongting', names)
        self.assertNotIn('common_prj', names)

    def test_get_project_info_unique(self):
        finder = ProjectFinder(Path(self.test_dir) / "flow" / "initialize")
        info = finder.get_project_info("dongting")
        self.assertEqual(info['node'], 'S8')

    def test_get_project_info_not_found(self):
        finder = ProjectFinder(Path(self.test_dir) / "flow" / "initialize")
        with self.assertRaises(ValueError):
            finder.get_project_info("nonexistent")

    def test_resolve_context(self):
        """测试从路径推断上下文"""
        # 创建 WORK_PATH 结构
        work = Path(self.test_dir) / "WORK"
        project_node = work / "dongting" / "P85"
        project_node.mkdir(parents=True)

        import yaml
        version_info = {
            'project': 'dongting',
            'version': 'P85',
            'foundry': 'SAMSUNG',
            'node': 'S4',
        }
        (project_node / ".edp_version").write_text(
            yaml.dump(version_info), encoding='utf-8'
        )
        (project_node / "block1").mkdir()

        finder = ProjectFinder(Path(self.test_dir) / "flow" / "initialize")

        # 在 project/version 级别 → 应推断出 project 信息
        detected = finder.resolve_context(project_node)
        self.assertIsNotNone(detected)
        self.assertEqual(detected['project_name'], 'dongting')
        self.assertEqual(detected['project_node'], 'P85')

        # 在 block 级别 → 应额外推断出 block_name
        detected = finder.resolve_context(project_node / "block1")
        self.assertIsNotNone(detected)
        self.assertEqual(detected['block_name'], 'block1')

        # 在 user/branch 级别 → 应推断出 user 和 branch
        user_branch = project_node / "block1" / "zhangsan" / "main_branch"
        user_branch.mkdir(parents=True)
        detected = finder.resolve_context(user_branch)
        self.assertIsNotNone(detected)
        self.assertEqual(detected['user'], 'zhangsan')
        self.assertEqual(detected['branch'], 'main_branch')


class TestBranchSource(unittest.TestCase):
    """测试分支来源信息"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load(self):
        branch_path = Path(self.test_dir) / "branch1"
        branch_path.mkdir()

        copy_info = {
            'source_user': 'zhangsan',
            'source_branch': 'branch1',
            'source_step': '/some/path/runs/pnr.init',
            'target_step': '/target/runs/pnr.init',
            'step_name': 'pnr.init',
        }
        save_branch_source(branch_path, "branch1.pnr.init", copy_info, True)

        loaded = load_branch_source(branch_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['source']['from_branch_step'], 'branch1.pnr.init')
        self.assertEqual(loaded['mode'], 'link')

    def test_load_nonexistent(self):
        self.assertIsNone(load_branch_source(Path(self.test_dir) / "nonexistent"))


class TestWorkPathInitializer(unittest.TestCase):
    """测试 WorkPathInitializer"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # 创建模拟 edp_center 结构
        config = Path(self.test_dir) / "edp_center" / "flow" / "initialize" / "F1" / "N1"
        config.mkdir(parents=True)
        (config / "common_prj").mkdir()
        (config / "proj1").mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_project(self):
        """测试初始化项目结构"""
        work_path = Path(self.test_dir) / "WORK"
        initializer = WorkPathInitializer(Path(self.test_dir) / "edp_center")

        result = initializer.init_project(
            work_path, "proj1", "P85",
            blocks=["block1", "block2"]
        )

        # 验证目录结构
        project_node = work_path / "proj1" / "P85"
        self.assertTrue(project_node.exists())
        self.assertTrue((project_node / "block1").exists())
        self.assertTrue((project_node / "block2").exists())
        self.assertTrue((project_node / ".edp_version").exists())

        # 验证 blocks 信息
        self.assertIn('block1', result['blocks'])
        self.assertIn('block2', result['blocks'])

    def test_init_user_workspace(self):
        """测试创建用户分支"""
        work_path = Path(self.test_dir) / "WORK"
        initializer = WorkPathInitializer(Path(self.test_dir) / "edp_center")

        # 先初始化项目
        initializer.init_project(work_path, "proj1", "P85")

        # 创建分支
        result = initializer.init_user_workspace(
            work_path=work_path,
            project_name="proj1",
            project_node="P85",
            block_name="block1",
            user_name="testuser",
            branch_name="branch1",
        )

        branch_path = work_path / "proj1" / "P85" / "block1" / "testuser" / "branch1"
        self.assertTrue(branch_path.exists())
        self.assertTrue((branch_path / "cmds").is_dir())
        self.assertTrue((branch_path / "data").is_dir())
        self.assertTrue((branch_path / "hooks").is_dir())
        self.assertTrue((branch_path / "runs").is_dir())
        self.assertTrue((branch_path / "user_config.tcl").exists())
        self.assertTrue((branch_path / "user_config.yaml").exists())


class TestGetCurrentUser(unittest.TestCase):

    def test_returns_string(self):
        user = get_current_user()
        self.assertIsInstance(user, str)
        self.assertNotEqual(user, "")


if __name__ == '__main__':
    unittest.main(verbosity=2)
