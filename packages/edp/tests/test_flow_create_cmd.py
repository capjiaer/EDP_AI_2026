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
            self.assertFalse((root / "hooks" / "pnr_innovus" / "place").exists())

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

    def test_flowcreate_shows_provided_and_activated_steps_for_tool(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            ctx = self._mock_context(tmp)
            tool_dir = ctx["flow_overlay_path"] / "cmds" / "pnr_innovus"
            tool_dir.mkdir(parents=True, exist_ok=True)
            (tool_dir / "step.yaml").write_text(
                (
                    "pnr_innovus:\n"
                    "  supported_steps:\n"
                    "    place:\n"
                    "      invoke: [\"innovus -init $edp(script)\"]\n"
                    "      sub_steps: [global_place]\n"
                ),
                encoding="utf-8",
            )
            ctx["tool_selection"] = {"place": "pnr_innovus", "route": "pnr_innovus"}

            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = ctx
                result = self.runner.invoke(
                    cli,
                    [
                        "--edp-center", tmpdir, "flowcreate",
                        "--tool", "pnr_innovus",
                        "--step", "route",
                        "--sub-steps", "route",
                        "--invoke", "innovus -init $edp(script)",
                    ],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Tool 'pnr_innovus' visibility", result.output)
            self.assertIn("provided steps (1): place", result.output)
            self.assertIn("activated steps (2): place, route", result.output)

    def test_flowcreate_merges_base_supported_steps_for_visibility(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            ctx = self._mock_context(tmp)

            # Keep selected tool step.yaml only in base, overlay has none.
            base_tool_dir = ctx["flow_base_path"] / "cmds" / "pnr_innovus"
            base_tool_dir.mkdir(parents=True, exist_ok=True)
            (base_tool_dir / "step.yaml").write_text(
                (
                    "pnr_innovus:\n"
                    "  supported_steps:\n"
                    "    place:\n"
                    "      invoke: [\"innovus -init $edp(script)\"]\n"
                    "      sub_steps: [global_place]\n"
                ),
                encoding="utf-8",
            )
            ctx["tool_selection"] = {"place": "pnr_innovus"}

            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = ctx
                result = self.runner.invoke(
                    cli,
                    [
                        "--edp-center", tmpdir, "flowcreate",
                        "--tool", "pnr_innovus",
                        "--step", "route",
                        "--sub-steps", "route",
                        "--invoke", "innovus -init $edp(script)",
                    ],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("provided steps (1): place", result.output)

    def test_flowcreate_collects_multi_invoke_segments_interactively(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = self._mock_context(tmp)
                user_input = "\n".join([
                    "pnr_innovus",
                    "route",
                    "route",
                    "innovus -init $edp(script)",
                    "{tee} $edp(step).log",
                    "",
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            step_yaml = (tmp / "flow_overlay" / "cmds" / "pnr_innovus" / "step.yaml").read_text(encoding="utf-8")
            self.assertIn('invoke:', step_yaml)
            self.assertIn('- innovus -init $edp(script)', step_yaml)
            self.assertIn('- \'{tee} $edp(step).log\'', step_yaml)
            self.assertIn("Current invoke (2 segment(s))", result.output)
            self.assertIn("Joined command: innovus -init $edp(script) {tee} $edp(step).log", result.output)

    def test_flowcreate_tool_selection_supports_numeric_choice(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = self._mock_context(tmp)
                user_input = "\n".join([
                    "1",                            # tool: pnr_innovus
                    "newstep",
                    "newstep",
                    "innovus -init $edp(script)",
                    "",
                    "",
                ])
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "flowcreate"],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Available tools:", result.output)
            self.assertIn("[1] pnr_innovus", result.output)
            self.assertIn("Tool: pnr_innovus", result.output)

    def test_flowcreate_suggests_calibre_default_invoke_for_drc(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = self._mock_context(tmp)
                user_input = "\n".join([
                    "drc",   # step
                    "drc",   # sub-steps
                    "",      # accept suggested first invoke segment
                    "",      # finish invoke segments
                    "",      # trailing newline
                ])
                result = self.runner.invoke(
                    cli,
                    [
                        "--edp-center", tmpdir, "flowcreate",
                        "--tool", "pv_calibre",
                    ],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Invoke segment [calibre -drc -hier -turbo {cpu_num}]", result.output)
            step_yaml = (tmp / "flow_overlay" / "cmds" / "pv_calibre" / "step.yaml").read_text(encoding="utf-8")
            self.assertIn("- calibre -drc -hier -turbo {cpu_num}", step_yaml)

    def test_flowcreate_suggests_sta_pt_default_invoke(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with patch.object(self.flow_module, "_resolve_context") as mock_ctx:
                mock_ctx.return_value = self._mock_context(tmp)
                user_input = "\n".join([
                    "setup",  # step
                    "setup",  # sub-steps
                    "",       # accept suggested first invoke segment
                    "",       # finish invoke segments
                    "",       # trailing newline
                ])
                result = self.runner.invoke(
                    cli,
                    [
                        "--edp-center", tmpdir, "flowcreate",
                        "--tool", "sta_pt",
                    ],
                    input=user_input,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Invoke segment [pt_shell -file $edp(script)]", result.output)
            step_yaml = (tmp / "flow_overlay" / "cmds" / "sta_pt" / "step.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("- pt_shell -file $edp(script)", step_yaml)


if __name__ == "__main__":
    unittest.main(verbosity=2)
