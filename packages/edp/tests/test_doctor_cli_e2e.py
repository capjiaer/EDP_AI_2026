#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner


class TestDoctorCliE2E(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner(mix_stderr=False)
        self.doctor_module = importlib.import_module("edp.commands.doctor")

    def _make_valid_edp_center(self, root: Path) -> None:
        """创建最小有效的 edp_center 目录结构（无报错项）。"""
        (root / "flow" / "initialize").mkdir(parents=True, exist_ok=True)
        edp_debug = root / "flow" / "common_packages" / "tcl_packages" / "default" / "edp_debug.tcl"
        edp_debug.parent.mkdir(parents=True, exist_ok=True)
        edp_debug.write_text("# edp_debug stub\n", encoding="utf-8")

    def test_doctor_json_output_success_when_only_warnings(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_valid_edp_center(root)

            with patch.object(self.doctor_module, "_resolve_context") as mock_context, patch.object(
                self.doctor_module.shutil, "which", return_value=None
            ):
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor", "--json"],
                    env={"SHELL": ""},
                )
                self.assertEqual(result.exit_code, 0, result.output)
                payload = json.loads(result.output)
                self.assertEqual(payload["summary"]["errors"], 0)
                self.assertGreater(payload["summary"]["warnings"], 0)

    def test_doctor_strict_fails_when_warnings_exist(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_valid_edp_center(root)

            with patch.object(self.doctor_module, "_resolve_context") as mock_context, patch.object(
                self.doctor_module.shutil, "which", return_value=None
            ):
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor", "--strict"],
                    env={"SHELL": ""},
                )
                self.assertNotEqual(result.exit_code, 0)
                # --strict 的 "blocking issues" 走 stderr（mix_stderr=False）
                stderr = result.stderr_bytes.decode() if result.stderr_bytes else ""
                self.assertIn("Doctor found blocking issues.", result.output + stderr)

    def test_doctor_fails_when_legacy_common_packages_exists(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_valid_edp_center(root)
            (root / "common_packages").mkdir(parents=True, exist_ok=True)

            with patch.object(self.doctor_module, "_resolve_context") as mock_context:
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor"],
                    env={"SHELL": "/bin/bash"},
                )
                self.assertNotEqual(result.exit_code, 0)
                # ERR 条目在 stdout；"blocking issues" 可能在 stderr
                self.assertIn("Legacy directory is not allowed", result.output)

    def test_doctor_reports_missing_common_packages(self):
        """flow/common_packages 不存在时 doctor 报 ERR"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "flow" / "initialize").mkdir(parents=True, exist_ok=True)
            # 故意不创建 flow/common_packages

            with patch.object(self.doctor_module, "_resolve_context") as mock_context:
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor", "--json"],
                    env={"SHELL": "/bin/bash"},
                )
                payload = json.loads(result.output)
                checks = {c["check"]: c for c in payload["checks"]}
                self.assertEqual(checks["common_packages"]["level"], "ERR")

    def test_doctor_reports_missing_edp_debug_tcl(self):
        """edp_debug.tcl 缺失时 doctor 报 WARN"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "flow" / "initialize").mkdir(parents=True, exist_ok=True)
            # 创建 common_packages 但不放 edp_debug.tcl
            (root / "flow" / "common_packages" / "tcl_packages" / "default").mkdir(
                parents=True, exist_ok=True
            )

            with patch.object(self.doctor_module, "_resolve_context") as mock_context:
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor", "--json"],
                    env={"SHELL": "/bin/bash"},
                )
                payload = json.loads(result.output)
                checks = {c["check"]: c for c in payload["checks"]}
                self.assertEqual(checks["edp_debug_tcl"]["level"], "WARN")

    def test_doctor_checks_tcl_runtime(self):
        """Tcl 运行时检查出现在 JSON 报告中"""
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_valid_edp_center(root)

            with patch.object(self.doctor_module, "_resolve_context") as mock_context:
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor", "--json"],
                    env={"SHELL": "/bin/bash"},
                )
                payload = json.loads(result.output)
                checks = {c["check"]: c for c in payload["checks"]}
                self.assertIn("tcl_runtime", checks)
                # 在正常测试环境中 Tcl 应该可用
                self.assertEqual(checks["tcl_runtime"]["level"], "OK")

    def test_doctor_checks_flow_step_yaml(self):
        """进入 context 后检查 step.yaml 是否存在且可解析"""
        from edp.cli import cli
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_valid_edp_center(root)

            flow_base = root / "flow" / "initialize" / "FOUNDRY" / "NODE" / "common_prj"
            tool_dir = flow_base / "cmds" / "my_tool"
            tool_dir.mkdir(parents=True, exist_ok=True)
            (tool_dir / "step.yaml").write_text(
                "my_tool:\n  supported_steps:\n    run:\n      invoke: []\n",
                encoding="utf-8",
            )

            mock_ctx = {
                "branch_path": root / "workdir",
                "flow_base_path": flow_base,
                "flow_overlay_path": None,
            }

            # 创建一个假 graph_config，避免触发 ERR
            fake_graph = MagicMock()
            fake_graph.name = "graph_config.yaml"
            mock_state = MagicMock()
            mock_state.exists.return_value = False

            with patch.object(self.doctor_module, "_resolve_context", return_value=mock_ctx), \
                 patch.object(self.doctor_module, "_find_graph_configs", return_value=[fake_graph]), \
                 patch.object(self.doctor_module, "StateStore", return_value=mock_state):
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor", "--json"],
                    env={"SHELL": "/bin/bash"},
                )
                payload = json.loads(result.output)
                checks = {c["check"]: c for c in payload["checks"]}
                self.assertIn("flow_base_step_yaml", checks)
                self.assertEqual(checks["flow_base_step_yaml"]["level"], "OK")
                self.assertIn("flow_base_parse", checks)
                self.assertEqual(checks["flow_base_parse"]["level"], "OK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
