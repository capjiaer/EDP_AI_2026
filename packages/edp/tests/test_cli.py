#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp CLI 基础回归测试（与当前实现保持一致）
"""

import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from click.testing import CliRunner


class TestCLIHelp(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_cli_help_lists_commands(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        for cmd in ["init", "run", "status", "retry", "graph", "doctor", "flow"]:
            self.assertIn(cmd, result.output)

    def test_init_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["init", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--project", result.output)
        self.assertIn("--version", result.output)
        self.assertIn("--block", result.output)

    def test_run_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["run", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--dry-run", result.output)
        self.assertIn("--debug", result.output)
        self.assertIn("--info", result.output)

    def test_status_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["status", "--help"])
        self.assertEqual(result.exit_code, 0)

    def test_retry_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["retry", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("STEP", result.output)
        self.assertIn("--dry-run", result.output)
        self.assertIn("--debug", result.output)
        self.assertIn("--info", result.output)

    def test_graph_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["graph", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ascii", result.output)
        self.assertIn("dot", result.output)
        self.assertIn("table", result.output)
        self.assertIn("--select", result.output)

    def test_doctor_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["doctor", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--strict", result.output)
        self.assertIn("--json", result.output)

    def test_flow_help(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["flow", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("create", result.output)


class TestMissingEdpCenter(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_init_requires_edp_center(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["init", "-prj", "dongting", "-ver", "P85"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("edp_center", result.output.lower())

    def test_run_requires_edp_center(self):
        from edp.cli import cli
        result = self.runner.invoke(cli, ["run"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("edp_center", result.output.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
