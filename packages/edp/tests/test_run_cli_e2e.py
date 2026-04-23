#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp run CLI 轻量端到端测试

目标：
- 验证 -debug/-info 参数能传递到 Executor
- 验证不同 SHELL 下 debug 启动器后缀（.sh/.csh）
"""

import tempfile
import unittest
import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from click.testing import CliRunner


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class _DummyScriptBuilder:
    def __init__(self, *args, **kwargs):
        self.preferred_shell = "bash"
        self.workdir_path = Path(tempfile.gettempdir())


class TestRunCliE2E(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.run_module = importlib.import_module("edp.commands.run")
        self.retry_module = importlib.import_module("edp.commands.retry")

    def test_debug_and_info_flags_are_passed_to_executor(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            branch = Path(tmpdir) / "branch"
            branch.mkdir(parents=True, exist_ok=True)

            with patch.object(self.run_module, "_resolve_context") as mock_resolve_context, patch.object(
                self.run_module, "_pick_graph_config"
            ) as mock_pick_graph, patch(
                "cmdkit.ScriptBuilder", _DummyScriptBuilder
            ), patch.object(
                self.run_module, "Executor"
            ) as mock_executor_cls:
                mock_resolve_context.return_value = {
                    "branch_path": branch,
                    "flow_base_path": Path(tmpdir) / "flow_base",
                    "flow_overlay_path": Path(tmpdir) / "flow_overlay",
                    "graph_configs": [Path(tmpdir) / "graph_config.yaml"],
                    "tool_selection": {"place": "pnr_innovus"},
                    "project_info": {},
                }
                mock_pick_graph.return_value = Path(tmpdir) / "graph_config.yaml"

                report = SimpleNamespace(
                    success=True, failed_steps=[], skipped_steps=[], total_time=0.0
                )
                mock_executor = mock_executor_cls.return_value
                mock_executor.run_single.return_value = report

                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "run", "place", "-debug", "-info"],
                )

                self.assertEqual(result.exit_code, 0, result.output)
                kwargs = mock_executor_cls.call_args.kwargs
                self.assertTrue(kwargs["debug"])
                self.assertTrue(kwargs["verbose"])

    def test_debug_run_generates_csh_launcher_when_shell_is_tcsh(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            branch = tmp / "branch"
            flow_base = tmp / "flow_base"
            branch.mkdir(parents=True, exist_ok=True)

            _write(
                flow_base / "cmds" / "pnr_innovus" / "step.yaml",
                """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -init $edp(script)"
      sub_steps:
        - do_place
""".strip(),
            )
            _write(
                flow_base / "cmds" / "pnr_innovus" / "steps" / "place" / "do_place.tcl",
                "proc do_place {} { puts \"ok\" }",
            )

            with patch.object(self.run_module, "_resolve_context") as mock_resolve_context, patch.object(
                self.run_module, "_pick_graph_config"
            ) as mock_pick_graph:
                mock_resolve_context.return_value = {
                    "branch_path": branch,
                    "flow_base_path": flow_base,
                    "flow_overlay_path": tmp / "flow_overlay_not_exist",
                    "graph_configs": [tmp / "graph_config.yaml"],
                    "tool_selection": {"place": "pnr_innovus"},
                    "project_info": {},
                }
                mock_pick_graph.return_value = tmp / "graph_config.yaml"

                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "run", "place", "-dr", "-debug"],
                    env={"SHELL": "/bin/tcsh"},
                )

                self.assertEqual(result.exit_code, 0, result.output)
                self.assertTrue(
                    (branch / "runs" / "pnr_innovus" / "place" / "place_debug.csh").exists()
                )

    def test_debug_run_generates_bash_launcher_when_shell_is_bash(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            branch = tmp / "branch"
            flow_base = tmp / "flow_base"
            branch.mkdir(parents=True, exist_ok=True)

            _write(
                flow_base / "cmds" / "pnr_innovus" / "step.yaml",
                """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -init $edp(script)"
      sub_steps:
        - do_place
""".strip(),
            )
            _write(
                flow_base / "cmds" / "pnr_innovus" / "steps" / "place" / "do_place.tcl",
                "proc do_place {} { puts \"ok\" }",
            )

            with patch.object(self.run_module, "_resolve_context") as mock_resolve_context, patch.object(
                self.run_module, "_pick_graph_config"
            ) as mock_pick_graph:
                mock_resolve_context.return_value = {
                    "branch_path": branch,
                    "flow_base_path": flow_base,
                    "flow_overlay_path": tmp / "flow_overlay_not_exist",
                    "graph_configs": [tmp / "graph_config.yaml"],
                    "tool_selection": {"place": "pnr_innovus"},
                    "project_info": {},
                }
                mock_pick_graph.return_value = tmp / "graph_config.yaml"

                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "run", "place", "-dr", "-debug"],
                    env={"SHELL": "/bin/bash"},
                )

                self.assertEqual(result.exit_code, 0, result.output)
                self.assertTrue(
                    (branch / "runs" / "pnr_innovus" / "place" / "place_debug.sh").exists()
                )

    def test_retry_debug_info_flags_are_passed_to_executor(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            branch = Path(tmpdir) / "branch"
            branch.mkdir(parents=True, exist_ok=True)

            with patch.object(self.retry_module, "_resolve_context") as mock_resolve_context, patch.object(
                self.retry_module, "_pick_graph_config"
            ) as mock_pick_graph, patch.object(
                self.retry_module, "StateStore"
            ) as mock_state_store_cls, patch.object(
                self.retry_module, "WorkflowBuilder"
            ) as mock_builder_cls, patch(
                "cmdkit.ScriptBuilder", _DummyScriptBuilder
            ), patch.object(
                self.retry_module, "Executor"
            ) as mock_executor_cls:
                mock_resolve_context.return_value = {
                    "branch_path": branch,
                    "flow_base_path": Path(tmpdir) / "flow_base",
                    "flow_overlay_path": Path(tmpdir) / "flow_overlay",
                    "graph_configs": [Path(tmpdir) / "graph_config.yaml"],
                    "tool_selection": {"place": "pnr_innovus"},
                    "project_info": {},
                }
                mock_pick_graph.return_value = Path(tmpdir) / "graph_config.yaml"

                mock_store = mock_state_store_cls.return_value
                mock_store.exists.return_value = True
                mock_store.load_graph_config.return_value = "graph_config.yaml"
                mock_store.load.return_value = {"place": self.retry_module.StepStatus.FAILED}

                mock_builder = mock_builder_cls.return_value
                mock_builder.create_workflow.return_value = SimpleNamespace()

                report = SimpleNamespace(
                    success=True, failed_steps=[], skipped_steps=[], total_time=0.0
                )
                mock_executor = mock_executor_cls.return_value
                mock_executor.run.return_value = report

                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "retry", "place", "-dr", "-debug", "-info"],
                )

                self.assertEqual(result.exit_code, 0, result.output)
                kwargs = mock_executor_cls.call_args.kwargs
                self.assertTrue(kwargs["dry_run"])
                self.assertTrue(kwargs["debug"])
                self.assertTrue(kwargs["verbose"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
