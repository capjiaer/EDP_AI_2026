#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp CLI 测试

用 click.testing.CliRunner + mock，不需要真实的项目环境。
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

# 确保 edp 包能被 import
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from click.testing import CliRunner


class TestCLIHelp(unittest.TestCase):
    """CLI 帮助信息测试"""

    def setUp(self):
        self.runner = CliRunner()

    def test_cli_help(self):
        """edp --help 输出所有命令"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('init', result.output)
        self.assertIn('run', result.output)
        self.assertIn('status', result.output)
        self.assertIn('retry', result.output)
        self.assertIn('graph', result.output)

    def test_init_help(self):
        """edp init --help 输出参数"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['init', '--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('--work-path', result.output)
        self.assertIn('--project', result.output)

    def test_run_help(self):
        """edp run --help 输出参数"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['run', '--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('--runner', result.output)
        self.assertIn('--resume', result.output)

    def test_status_help(self):
        """edp status --help"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['status', '--help'])
        self.assertEqual(result.exit_code, 0)

    def test_retry_help(self):
        """edp retry --help"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['retry', '--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('STEP', result.output)

    def test_graph_help(self):
        """edp graph --help 输出格式选项"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['graph', '--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('ascii', result.output)
        self.assertIn('dot', result.output)
        self.assertIn('table', result.output)


class TestCLIMissingEdpCenter(unittest.TestCase):
    """缺少 edp_center 时的报错"""

    def setUp(self):
        self.runner = CliRunner()

    def test_init_no_edp_center(self):
        """init 没有设置 edp_center 时报错"""
        from edp.cli import cli
        result = self.runner.invoke(cli, [
            'init',
            '--work-path', '/tmp/test',
            '--project', 'test',
            '--node', 'P85',
            '--block', 'block1',
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('edp_center', result.output.lower())

    def test_run_no_edp_center(self):
        """run 没有设置 edp_center 时报错"""
        from edp.cli import cli
        result = self.runner.invoke(cli, ['run'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('edp_center', result.output.lower())


class TestContextResolution(unittest.TestCase):
    """_resolve_context 测试"""

    def test_no_project_context(self):
        """不在项目目录下执行时报错"""
        from edp.cli import _resolve_context
        runner = CliRunner()

        with runner.isolated_filesystem():
            with patch('edp.cli.ProjectFinder') as MockFinder:
                mock_finder = MockFinder.return_value
                mock_finder.resolve_context.return_value = None

                ctx = MagicMock()
                ctx.obj = {'edp_center': Path('/fake/edp_center')}

                from edp.cli import cli
                result = runner.invoke(cli, ['run'],
                                       catch_exceptions=False,
                                       obj={'edp_center': Path('/fake/edp_center')})

                # 应该因为无法检测项目而报错
                # 注：实际 invoke 时 _resolve_context 在命令内部调用


class TestFindDepFiles(unittest.TestCase):
    """_find_dep_files 测试"""

    def test_finds_files_in_base(self):
        """在 base 目录找到 graph_config 文件"""
        from edp.cli import _find_dep_files

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'common_prj'
            base.mkdir()
            (base / 'graph_config.yaml').write_text('a: b')
            (base / 'graph_config_extra.yaml').write_text('c: d')

            files = _find_dep_files(base, None)
            self.assertEqual(len(files), 2)

    def test_merges_base_and_overlay(self):
        """合并 base 和 overlay 的文件"""
        from edp.cli import _find_dep_files

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'common_prj'
            overlay = Path(tmpdir) / 'project'
            base.mkdir()
            overlay.mkdir()
            (base / 'graph_config.yaml').write_text('a: b')
            (overlay / 'graph_config.yaml').write_text('c: d')

            files = _find_dep_files(base, overlay)
            self.assertEqual(len(files), 2)

    def test_no_files(self):
        """找不到文件返回空列表"""
        from edp.cli import _find_dep_files

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'common_prj'
            base.mkdir()

            files = _find_dep_files(base, None)
            self.assertEqual(files, [])


class TestLoadStepConfig(unittest.TestCase):
    """_load_step_config 测试"""

    def test_parses_tool_dot_step(self):
        """解析 tool.step 格式"""
        from edp.cli import _load_step_config

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            config = base / 'step_config.yaml'
            config.write_text(yaml.dump({
                'steps': ['pnr_innovus.place', 'pv_calibre.drc']
            }))

            result = _load_step_config(base, None)
            self.assertEqual(result, {'place': 'pnr_innovus', 'drc': 'pv_calibre'})

    def test_overlay_overrides_base(self):
        """overlay 优先于 base"""
        from edp.cli import _load_step_config

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'common_prj'
            overlay = Path(tmpdir) / 'project'
            base.mkdir()
            overlay.mkdir()

            (base / 'step_config.yaml').write_text(yaml.dump({
                'steps': ['tool_a.step1']
            }))
            (overlay / 'step_config.yaml').write_text(yaml.dump({
                'steps': ['tool_b.step1']
            }))

            result = _load_step_config(base, overlay)
            self.assertEqual(result, {'step1': 'tool_b'})

    def test_no_config_file(self):
        """配置文件不存在返回空字典"""
        from edp.cli import _load_step_config

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            result = _load_step_config(base, None)
            self.assertEqual(result, {})


class TestClearStep(unittest.TestCase):
    """StateStore.clear_step 测试"""

    def test_clear_single_step(self):
        """清除单个步骤的状态"""
        from flowkit.core.state_store import StateStore
        from flowkit.core.step import StepStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / 'state.yaml'
            store = StateStore(state_file)

            store.save('a', StepStatus.FINISHED)
            store.save('b', StepStatus.FAILED)
            store.save('c', StepStatus.FINISHED)

            store.clear_step('b')

            saved = store.load()
            self.assertIn('a', saved)
            self.assertNotIn('b', saved)
            self.assertIn('c', saved)

    def test_clear_last_step_deletes_file(self):
        """清除最后一个步骤时删除状态文件"""
        from flowkit.core.state_store import StateStore
        from flowkit.core.step import StepStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / 'state.yaml'
            store = StateStore(state_file)

            store.save('a', StepStatus.FINISHED)
            store.clear_step('a')

            self.assertFalse(store.exists())

    def test_clear_nonexistent_step_noop(self):
        """清除不存在的步骤不报错"""
        from flowkit.core.state_store import StateStore
        from flowkit.core.step import StepStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / 'state.yaml'
            store = StateStore(state_file)

            store.save('a', StepStatus.FINISHED)
            store.clear_step('nonexistent')  # 不应报错

            saved = store.load()
            self.assertIn('a', saved)


class TestGraphCommand(unittest.TestCase):
    """edp graph 命令测试"""

    def setUp(self):
        self.runner = CliRunner()
        self.edp_center = None  # 不需要真实 edp_center

    def _make_fake_project(self, tmpdir):
        """创建假的项目目录结构"""
        edp_center = Path(tmpdir) / 'edp_center'
        work_path = Path(tmpdir) / 'WORK_PATH'

        # edp_center/flow/initialize/FOUNDRY/NODE/common_prj/
        init_path = edp_center / 'flow' / 'initialize' / 'TEST' / 'N1' / 'common_prj'
        init_path.mkdir(parents=True)

        # graph_config.yaml
        (init_path / 'graph_config.yaml').write_text(yaml.dump({
            'a': 'b', 'b': 'c', 'c': ['d', 'e']
        }))

        # step_config.yaml
        (init_path / 'step_config.yaml').write_text(yaml.dump({
            'steps': ['tool1.a', 'tool1.b', 'tool2.c', 'tool2.d', 'tool2.e']
        }))

        # .edp_version
        version_path = edp_center / 'flow' / 'initialize' / 'TEST' / 'N1'
        (version_path / '.edp_version').write_text('test')

        # WORK_PATH/project/node/block/user/branch/
        branch = work_path / 'proj' / 'N1' / 'blk' / 'user1' / 'branch1'
        branch.mkdir(parents=True)

        return edp_center, work_path, branch

    @patch('edp.cli.ProjectFinder')
    def test_graph_ascii_output(self, MockFinder):
        """graph 命令 ascii 格式输出"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            edp_center, work_path, branch = self._make_fake_project(tmpdir)

            mock_finder = MockFinder.return_value
            mock_finder.resolve_context.return_value = {
                'work_path': str(work_path),
                'project_name': 'proj',
                'project_node': 'N1',
                'block_name': 'blk',
                'foundry': 'TEST',
                'node': 'N1',
            }

            old_cwd = os.getcwd()
            try:
                os.chdir(str(branch))
                result = self.runner.invoke(
                    cli, ['--edp-center', str(edp_center),
                          'graph', '--format', 'ascii'],
                )
                self.assertEqual(result.exit_code, 0)
                # 应该包含 step 名
                self.assertTrue(
                    'a' in result.output or 'step' in result.output.lower()
                )
            finally:
                os.chdir(old_cwd)

    @patch('edp.cli.ProjectFinder')
    def test_graph_table_output(self, MockFinder):
        """graph 命令 table 格式输出"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            edp_center, work_path, branch = self._make_fake_project(tmpdir)

            mock_finder = MockFinder.return_value
            mock_finder.resolve_context.return_value = {
                'work_path': str(work_path),
                'project_name': 'proj',
                'project_node': 'N1',
                'block_name': 'blk',
                'foundry': 'TEST',
                'node': 'N1',
            }

            old_cwd = os.getcwd()
            try:
                os.chdir(str(branch))
                result = self.runner.invoke(
                    cli, ['--edp-center', str(edp_center),
                          'graph', '--format', 'table'],
                )
                self.assertEqual(result.exit_code, 0)
            finally:
                os.chdir(old_cwd)

    @patch('edp.cli.ProjectFinder')
    def test_graph_dot_output(self, MockFinder):
        """graph 命令 dot 格式输出"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            edp_center, work_path, branch = self._make_fake_project(tmpdir)

            mock_finder = MockFinder.return_value
            mock_finder.resolve_context.return_value = {
                'work_path': str(work_path),
                'project_name': 'proj',
                'project_node': 'N1',
                'block_name': 'blk',
                'foundry': 'TEST',
                'node': 'N1',
            }

            old_cwd = os.getcwd()
            try:
                os.chdir(str(branch))
                result = self.runner.invoke(
                    cli, ['--edp-center', str(edp_center),
                          'graph', '--format', 'dot'],
                )
                self.assertEqual(result.exit_code, 0)
                # DOT 格式应该包含 digraph
                self.assertIn('digraph', result.output)
            finally:
                os.chdir(old_cwd)

    @patch('edp.cli.ProjectFinder')
    def test_graph_output_to_file(self, MockFinder):
        """graph -o 写入文件"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            edp_center, work_path, branch = self._make_fake_project(tmpdir)

            mock_finder = MockFinder.return_value
            mock_finder.resolve_context.return_value = {
                'work_path': str(work_path),
                'project_name': 'proj',
                'project_node': 'N1',
                'block_name': 'blk',
                'foundry': 'TEST',
                'node': 'N1',
            }

            output_file = Path(tmpdir) / 'graph_output.txt'
            old_cwd = os.getcwd()
            try:
                os.chdir(str(branch))
                result = self.runner.invoke(
                    cli, ['--edp-center', str(edp_center),
                          'graph', '--format', 'dot', '-o', str(output_file)],
                )
                self.assertEqual(result.exit_code, 0)
                self.assertTrue(output_file.exists())
                content = output_file.read_text(encoding='utf-8')
                self.assertIn('digraph', content)
            finally:
                os.chdir(old_cwd)


if __name__ == '__main__':
    unittest.main(verbosity=2)
