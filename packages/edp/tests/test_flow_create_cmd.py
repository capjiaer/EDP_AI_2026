#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp flow create command tests
"""

import tempfile
import unittest
import importlib
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from click.testing import CliRunner


class TestFlowCreateCmd(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.flow_module = importlib.import_module("edp.commands.flow_cmd")

    def _mock_context(self, tmp: Path):
        flow_overlay = tmp / "flow_overlay"
        flow_base = tmp / "flow_base"
        branch = tmp / "branch"
        flow_overlay.mkdir(parents=True, exist_ok=True)
        flow_base.mkdir(parents=True, exist_ok=True)
        branch.mkdir(parents=True, exist_ok=True)
        return {
            "branch_path": branch,
            "flow_base_path": flow_base,
            "flow_overlay_path": flow_overlay,
            "graph_configs": [tmp / "graph_config.yaml"],
            "tool_selection": {"place": "pnr_innovus"},
            "project_info": {},
        }

    def test_flow_create_generates_scaffold(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = self._mock_context(tmp)
                user_input = "\n".join([
                    "pnr_innovus",
                    "place",
                    "global_place,detail_place",
                    "innovus -init $edp(script)",
                    "y",
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            root = tmp / "flow_overlay"
            self.assertTrue((root / "cmds" / "pnr_innovus" / "step.yaml").exists())
            self.assertTrue((root / "cmds" / "pnr_innovus" / "config.yaml").exists())
            self.assertTrue((root / "cmds" / "pnr_innovus" / "steps" / "place" / "global_place.tcl").exists())
            self.assertTrue((root / "cmds" / "pnr_innovus" / "steps" / "place" / "detail_place.tcl").exists())
            self.assertTrue((root / "hooks" / "pnr_innovus" / "place" / "step.pre").exists())

    def test_flow_create_existing_step_fails(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            ctx = self._mock_context(tmp)
            existing = ctx["flow_overlay_path"] / "cmds" / "pnr_innovus"
            existing.mkdir(parents=True, exist_ok=True)
            (existing / "step.yaml").write_text(
                "pnr_innovus:\n  supported_steps:\n    place:\n      invoke: [\"innovus -init $edp(script)\"]\n      sub_steps: [global_place]\n",
                encoding="utf-8",
            )

            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = ctx
                result = self.runner.invoke(
                    cli,
                    [
                        "--edp-center", tmpdir, "flowcreate",
                        "--tool", "pnr_innovus",
                        "--step", "place",
                        "--sub-steps", "global_place",
                        "--invoke", "innovus -init $edp(script)",
                        "--with-hooks",
                    ],
                )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("already exists", result.output)

    def test_flow_create_sub_steps_written_to_step_yaml(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = self._mock_context(tmp)
                result = self.runner.invoke(
                    cli,
                    [
                        "--edp-center", tmpdir, "flowcreate",
                        "--tool", "pnr_innovus",
                        "--step", "cts",
                        "--sub-steps", "cts_init,cts_opt",
                        "--invoke", "innovus -init $edp(script)",
                        "--no-hooks",
                    ],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            step_yaml = (tmp / "flow_overlay" / "cmds" / "pnr_innovus" / "step.yaml").read_text(encoding="utf-8")
            self.assertIn("cts_init", step_yaml)
            self.assertIn("cts_opt", step_yaml)
            self.assertFalse((tmp / "flow_overlay" / "hooks" / "pnr_innovus" / "cts").exists())

    def test_flowcreate_can_run_without_branch_context(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            init_path = tmp / "flow" / "initialize" / "SAMSUNG" / "S4"
            (init_path / "common_prj").mkdir(parents=True, exist_ok=True)
            (init_path / "dongting").mkdir(parents=True, exist_ok=True)

            with patch.object(self.flow_module, "_resolve_context", side_effect=KeyError("branch_path")):
                user_input = "\n".join([
                    "1",                            # foundry: SAMSUNG
                    "1",                            # node: S4
                    "1",                            # project: dongting
                    "pnr_innovus",                  # tool
                    "place",                        # step
                    "global_place,detail_place",    # sub-steps
                    "innovus -init $edp(script)",   # invoke
                    "y",                            # with-hooks
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            root = init_path / "dongting"
            self.assertTrue((root / "cmds" / "pnr_innovus" / "step.yaml").exists())

    def test_flowcreate_fallback_accepts_numeric_selection(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            init_path = tmp / "flow" / "initialize" / "SAMSUNG" / "S4"
            (init_path / "common_prj").mkdir(parents=True, exist_ok=True)
            (init_path / "dongting").mkdir(parents=True, exist_ok=True)

            with patch.object(self.flow_module, "_resolve_context", side_effect=KeyError("branch_path")):
                user_input = "\n".join([
                    "1",                            # foundry: SAMSUNG
                    "1",                            # node: S4
                    "1",                            # project: dongting
                    "pnr_innovus",
                    "place",
                    "global_place",
                    "innovus -init $edp(script)",
                    "n",
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            root = init_path / "dongting"
            self.assertTrue((root / "cmds" / "pnr_innovus" / "step.yaml").exists())

    def test_flowcreate_fallback_can_confirm_new_foundry_node_project(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Keep one existing project list so selection prompt has baseline.
            base_init = tmp / "flow" / "initialize" / "SAMSUNG" / "S4"
            (base_init / "common_prj").mkdir(parents=True, exist_ok=True)
            (base_init / "dongting").mkdir(parents=True, exist_ok=True)

            with patch.object(self.flow_module, "_resolve_context", side_effect=KeyError("branch_path")):
                user_input = "\n".join([
                    "MY_FOUNDRY",                   # not number and not in list
                    "y",                            # confirm new foundry
                    "N3",                           # new node
                    "y",                            # confirm new node
                    "my_proj",                      # new project
                    "y",                            # confirm new project
                    "pnr_innovus",
                    "place",
                    "global_place",
                    "innovus -init $edp(script)",
                    "n",
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            root = tmp / "flow" / "initialize" / "MY_FOUNDRY" / "N3" / "my_proj"
            self.assertTrue((root / "cmds" / "pnr_innovus" / "step.yaml").exists())

    def test_flowcreate_new_step_yaml_contains_invoke_tutor_header(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            init_path = tmp / "flow" / "initialize" / "SAMSUNG" / "S4"
            (init_path / "common_prj").mkdir(parents=True, exist_ok=True)
            (init_path / "dongting").mkdir(parents=True, exist_ok=True)

            with patch.object(self.flow_module, "_resolve_context", side_effect=KeyError("branch_path")):
                user_input = "\n".join([
                    "1",                            # foundry
                    "1",                            # node
                    "1",                            # project
                    "pnr_innovus",
                    "place",
                    "global_place",
                    "innovus -init $edp(script)",
                    "n",
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            step_yaml = (init_path / "dongting" / "cmds" / "pnr_innovus" / "step.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("# invoke tutor (quick):", step_yaml)
            self.assertIn("$edp(script)", step_yaml)
            self.assertIn("tool(step,var) > tool(var)", step_yaml)
            self.assertIn("base config < overlay config < user_config", step_yaml)
            self.assertIn("-threads {cpu_num}", step_yaml)
            self.assertIn("Expanded command shape (when vars exist)", step_yaml)


if __name__ == "__main__":
    unittest.main(verbosity=2)
