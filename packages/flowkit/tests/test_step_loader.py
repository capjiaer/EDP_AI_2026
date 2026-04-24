#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from flowkit.loader.step_loader import StepRegistry


class TestStepLoaderSubStepSpecs(unittest.TestCase):
    def test_supports_mixed_sub_step_formats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            step_file = Path(tmpdir) / "step.yaml"
            step_file.write_text(
                """
pnr_innovus:
  supported_steps:
    place:
      invoke: ["innovus -init $edp(script)"]
      sub_steps:
        - global_place
        - name: run_external
          runner: shell
          command: "echo shell_ok"
""",
                encoding="utf-8",
            )
            registry = StepRegistry()
            registry.register_tool_steps(step_file)

            names = registry.get_sub_steps("pnr_innovus", "place")
            specs = registry.get_sub_step_specs("pnr_innovus", "place")

            self.assertEqual(names, ["global_place", "run_external"])
            self.assertEqual(specs[0]["runner"], "tcl")
            self.assertEqual(specs[1]["runner"], "shell")
            self.assertEqual(specs[1]["command"], "echo shell_ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)

