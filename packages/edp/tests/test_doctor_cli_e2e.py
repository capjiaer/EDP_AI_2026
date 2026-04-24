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
        self.runner = CliRunner()
        self.doctor_module = importlib.import_module("edp.commands.doctor")

    def test_doctor_json_output_success_when_only_warnings(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "flow" / "initialize").mkdir(parents=True, exist_ok=True)

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
            (root / "flow" / "initialize").mkdir(parents=True, exist_ok=True)

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
                self.assertIn("Doctor found blocking issues.", result.output)

    def test_doctor_fails_when_legacy_common_packages_exists(self):
        from edp.cli import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "flow" / "initialize").mkdir(parents=True, exist_ok=True)
            (root / "common_packages").mkdir(parents=True, exist_ok=True)

            with patch.object(self.doctor_module, "_resolve_context") as mock_context:
                mock_context.side_effect = click.ClickException("not in branch path")
                result = self.runner.invoke(
                    cli,
                    ["--edp-center", tmpdir, "doctor"],
                    env={"SHELL": "/bin/bash"},
                )
                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("Legacy directory is not allowed", result.output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
