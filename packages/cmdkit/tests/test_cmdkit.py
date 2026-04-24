#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cmdkit 核心功能测试

测试 ScriptBuilder 的脚本生成能力：
- Header（foundry/node/project/sub_steps 信息）
- Phase 1: Source（source 所有 proc 定义）
- Config: source config.tcl（独立配置文件，由 configkit.files2tcl 生成）
- Phase 2: Execute（按 step.yaml 声明的顺序调用 sub_step，hook 包裹）
- Debug 脚本（定义 proc + config，不自动执行，加载 debug CLI）
- .sh 生成（invoke 变量解析 + shell 包装）
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmdkit.script_builder import ScriptBuilder


def _write(path: Path, content: str) -> None:
    """写文件并确保父目录存在"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


class TestScriptBuilderBase(unittest.TestCase):
    """测试 ScriptBuilder 基础功能

    目录结构：
      flow_base/
        cmds/pnr_innovus/
          step.yaml
          config.yaml
          procs/util.tcl
          steps/place/
            global_place.tcl
            detail_place.tcl
        tcl_packages/
          common.tcl
      workdir/
        hooks/pnr_innovus/place/
          global_place.pre          ← proc 定义
          global_place.post         ← proc 定义
        cmds/pnr_innovus/           (输出目录)
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.flow_base = self.test_dir / "flow_base"
        self.workdir = self.test_dir / "workdir"
        self.common_packages = self.test_dir / "common_packages"

        # --- flow_base 结构 ---
        _write(self.flow_base / "cmds" / "pnr_innovus" / "step.yaml", """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -init $edp(script)"
        - "{nowin}"
        - "|& tee $edp(step).log"
      sub_steps:
        - global_place
        - detail_place
""")

        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  version: "23.1"
  nowin: -nowin
  place:
    effort: high
    density: 0.6
""")

        _write(self.flow_base / "cmds" / "pnr_innovus" / "procs" / "util.tcl",
               "proc util_init {} {\n    puts \"util\"\n}")

        _write(self.flow_base / "cmds" / "pnr_innovus" / "steps" / "place" / "global_place.tcl",
               "proc global_place {} {\n    puts \"global_place\"\n}")
        _write(self.flow_base / "cmds" / "pnr_innovus" / "steps" / "place" / "detail_place.tcl",
               "proc detail_place {} {\n    puts \"detail_place\"\n}")

        _write(self.flow_base / "tcl_packages" / "common.tcl",
               "proc common_init {} {\n    puts \"common\"\n}")

        # --- workdir hook 结构 ---
        # hooks/{tool}/{step}/ 下的 proc 定义文件
        _write(self.workdir / "hooks" / "pnr_innovus" / "place" / "global_place.pre",
               "proc place_global_place_pre {} {\n    puts \"pre hook\"\n}")
        _write(self.workdir / "hooks" / "pnr_innovus" / "place" / "global_place.post",
               "proc place_global_place_post {} {\n    puts \"post hook\"\n}")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _builder(self, overlay=None, preferred_shell=None) -> ScriptBuilder:
        return ScriptBuilder(
            flow_base_path=self.flow_base,
            workdir_path=self.workdir,
            overlay_path=overlay,
            common_packages_path=self.common_packages,
            preferred_shell=preferred_shell,
        )


# ── Header ──

class TestHeader(TestScriptBuilderBase):

    def test_header_contains_step_tool(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("Step: place", script)
        self.assertIn("Tool: pnr_innovus", script)

    def test_header_contains_sub_steps(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("Sub-steps: global_place -> detail_place", script)


# ── Phase 1: Source ──

class TestSourcePhase(TestScriptBuilderBase):

    def test_source_includes_procs(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("util.tcl", script)
        self.assertIn("pnr_innovus/procs", script)

    def test_source_includes_sub_step_tcl(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("global_place.tcl", script)
        self.assertIn("detail_place.tcl", script)

    def test_source_includes_tcl_packages(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("common.tcl", script)
        self.assertIn("tcl_packages", script)
        self.assertIn("[base] source", script)

    def test_source_includes_hook_procs(self):
        """hooks 目录下的 proc 定义被 source"""
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("global_place.pre", script)
        self.assertIn("global_place.post", script)

    def test_conflicting_proc_definitions_raise(self):
        """同名 proc 若在不同 source 文件重复定义，应 fail-fast。"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "procs" / "dup.tcl", """
proc global_place {} {
    puts "duplicate"
}
""")
        builder = self._builder()
        with self.assertRaises(ValueError):
            builder.build_step_script("pnr_innovus", "place")

    def test_conflict_error_message_is_grouped_and_readable(self):
        """冲突报错应包含 proc 分组与可读路径。"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "procs" / "dup.tcl", """
proc global_place {} {
    puts "duplicate"
}
""")
        builder = self._builder()
        with self.assertRaises(ValueError) as ctx:
            builder.build_step_script("pnr_innovus", "place")
        msg = str(ctx.exception)
        self.assertIn("Proc definition conflicts detected for pnr_innovus.place", msg)
        self.assertIn("- global_place", msg)
        self.assertIn("flow_base/cmds/pnr_innovus/steps/place/global_place.tcl", msg)
        self.assertIn("flow_base/cmds/pnr_innovus/procs/dup.tcl", msg)

    def test_duplicate_proc_within_same_file_is_allowed(self):
        """同一文件内重复定义不判定为跨文件冲突。"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "steps" / "place" / "global_place.tcl", """
proc global_place {} {
    puts "v1"
}
proc global_place {} {
    puts "v2"
}
""")
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")
        self.assertIn("global_place.tcl", script)


# ── Config ──

class TestConfigSection(TestScriptBuilderBase):

    def test_config_section_present(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        self.assertIn("Config Variables", script)
        self.assertIn("config.tcl", script)

    def test_config_tcl_generated(self):
        """_generate_config_tcl 生成独立的 config 文件"""
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")

        config_path = self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        self.assertTrue(config_path.exists())
        content = config_path.read_text(encoding='utf-8')
        self.assertIn("set pnr_innovus(version)", content)
        self.assertIn("set pnr_innovus(place,effort)", content)

    def test_config_tcl_overlay_merge(self):
        """overlay config 覆盖 base config"""
        overlay = self.test_dir / "overlay"
        _write(overlay / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  place:
    effort: extreme
  extra_var: overlay_value
""")

        builder = self._builder(overlay=overlay)
        builder.write_step_script("pnr_innovus", "place")

        config_path = self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        content = config_path.read_text(encoding='utf-8')

        self.assertIn("{extreme}", content)
        self.assertIn("set pnr_innovus(version) {23.1}", content)
        self.assertIn("set pnr_innovus(extra_var) {overlay_value}", content)

    def test_config_tcl_no_config_file(self):
        """没有 config.yaml 时生成空 config.tcl"""
        (self.flow_base / "cmds" / "pnr_innovus" / "config.yaml").unlink()

        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")

        config_path = self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        self.assertTrue(config_path.exists())
        content = config_path.read_text(encoding='utf-8')
        self.assertIn("No config files found", content)


# ── Phase 2: Execute ──

class TestExecutePhase(TestScriptBuilderBase):

    def test_execute_order(self):
        """execute 阶段按 sub_step 声明顺序调用"""
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        exec_section = script.split("Phase 2: Execute")[1]
        gp_idx = exec_section.index("global_place")
        dp_idx = exec_section.index("detail_place")
        self.assertLess(gp_idx, dp_idx)

    def test_execute_does_not_emit_hook_calls(self):
        """execute 阶段不显式调用 hook proc。"""
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        exec_section = script.split("Phase 2: Execute")[1]
        self.assertNotIn("if {[info procs", exec_section)
        self.assertNotIn("place_global_place_pre", exec_section)
        self.assertNotIn("place_global_place_post", exec_section)
        self.assertNotIn("place_step_pre", exec_section)
        self.assertNotIn("place_step_post", exec_section)

    def test_no_hooks_when_none_defined(self):
        """没有 hook 文件时，Phase 1 不 source，execute 仅保留 sub_step 调用"""
        import shutil
        hooks_dir = self.workdir / "hooks" / "pnr_innovus" / "place"
        if hooks_dir.exists():
            shutil.rmtree(hooks_dir)

        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        # Phase 1 不应该 source hooks 目录
        self.assertNotIn("global_place.pre", script)
        self.assertNotIn("global_place.post", script)
        # execute 不生成 hook 调用
        exec_section = script.split("Phase 2: Execute")[1]
        self.assertNotIn("place_global_place_pre", exec_section)
        self.assertNotIn("place_global_place_post", exec_section)
        self.assertIn("global_place", exec_section)

    def test_default_template_hooks_are_ignored(self):
        """init 默认模板 hook（Your code here）不 source 不调用。"""
        hooks_dir = self.workdir / "hooks" / "pnr_innovus" / "place"
        _write(hooks_dir / "global_place.pre", """
# template
proc place_global_place_pre {} {
    # Your code here
}
""")
        _write(hooks_dir / "global_place.post", """
# template
proc place_global_place_post {} {
    # Your code here
}
""")
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")
        exec_section = script.split("Phase 2: Execute")[1]
        self.assertNotIn("place_global_place_pre", exec_section)
        self.assertNotIn("place_global_place_post", exec_section)


# ── Debug Script ──

class TestDebugScript(TestScriptBuilderBase):

    def test_debug_script_generated(self):
        """build_debug_script 生成非空内容"""
        builder = self._builder()
        debug = builder.build_debug_script("pnr_innovus", "place")

        self.assertIn("EDP Debug Mode", debug)
        self.assertIn("Step: place", debug)

    def test_debug_has_no_execute_phase(self):
        """debug 脚本不包含 Phase 2: Execute"""
        builder = self._builder()
        debug = builder.build_debug_script("pnr_innovus", "place")

        self.assertNotIn("Phase 2: Execute", debug)

    def test_debug_has_config_source(self):
        """debug 脚本包含 config.tcl source"""
        builder = self._builder()
        debug = builder.build_debug_script("pnr_innovus", "place")

        self.assertIn("config.tcl", debug)

    def test_debug_excludes_edp_debug_from_phase1(self):
        """debug 脚本的 Phase 1 不 source edp_debug.tcl"""
        # 创建 edp_debug.tcl
        _write(self.common_packages / "tcl_packages" / "default" / "edp_debug.tcl",
               "# debug cli")

        builder = self._builder()
        debug = builder.build_debug_script("pnr_innovus", "place")

        # edp_debug.tcl 应该只在最后出现一次（作为 Load debug CLI）
        occurrences = debug.count("edp_debug.tcl")
        self.assertEqual(occurrences, 1)
        # 确保它在 Phase 1 之后
        phase1_idx = debug.index("Phase 1: Source")
        debug_cli_idx = debug.index("edp_debug.tcl")
        config_idx = debug.index("config.tcl")
        self.assertLess(phase1_idx, config_idx)
        self.assertLess(config_idx, debug_cli_idx)

    def test_debug_includes_sub_step_procs(self):
        """debug 脚本 source sub_step proc 定义"""
        builder = self._builder()
        debug = builder.build_debug_script("pnr_innovus", "place")

        self.assertIn("global_place.tcl", debug)
        self.assertIn("detail_place.tcl", debug)


# ── edp vars ──

class TestEdpVars(TestScriptBuilderBase):

    def test_edp_vars_keys(self):
        """edp vars 包含必要的框架变量"""
        builder = self._builder()
        vars = builder._build_edp_vars("pnr_innovus", "place")

        self.assertEqual(vars["step"], "place")
        self.assertEqual(vars["tool"], "pnr_innovus")
        self.assertIn("script", vars)
        self.assertIn("workdir", vars)

    def test_edp_vars_sub_steps(self):
        """edp vars 包含 sub_steps 列表"""
        builder = self._builder()
        vars = builder._build_edp_vars("pnr_innovus", "place")

        self.assertEqual(vars["sub_steps"], "global_place detail_place")


# ── .sh Generation ──

class TestShellGeneration(TestScriptBuilderBase):

    def test_shell_generated(self):
        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place")

        self.assertTrue(len(sh) > 0)
        self.assertIn("#!/bin/bash", sh)
        self.assertIn("innovus", sh)

    def test_shell_edp_variables_resolved(self):
        """.sh 中 $edp(script) 被解析为实际路径"""
        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place")

        self.assertIn("step.tcl", sh)
        self.assertNotIn("$edp(", sh)

    def test_shell_conditional_var(self):
        """{nowin} 被解析为 config 值 -nowin"""
        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place")

        self.assertIn("-nowin", sh)
        self.assertNotIn("{nowin}", sh)

    def test_shell_conditional_var_unset_drops_item(self):
        """{var} 未设置时，整个 invoke 项被丢弃"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  version: "23.1"
""")

        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place")

        self.assertNotIn("-nowin", sh)
        self.assertIn("innovus", sh)

    def test_shell_deep_nested_var_not_matched(self):
        """深层嵌套变量不会被误匹配"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  version: "23.1"
  place:
    timing:
      effort: extreme
""")
        _write(self.flow_base / "cmds" / "pnr_innovus" / "step.yaml", """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -init $edp(script)"
        - "{effort}"
      sub_steps:
        - global_place
        - detail_place
""")

        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place")

        self.assertNotIn("extreme", sh)
        self.assertNotIn("{effort}", sh)

    def test_debug_shell_uses_debug_tcl(self):
        """debug shell 使用 step-dir debug.tcl"""
        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place", debug=True)

        self.assertIn("/debug.tcl", sh)
        self.assertNotIn("$edp(", sh)

    def test_csh_shell_generated(self):
        """支持单独生成 csh 脚本"""
        builder = self._builder()
        csh = builder.build_step_shell("pnr_innovus", "place", shell_type="csh")

        self.assertIn("#!/bin/csh", csh)
        self.assertIn("innovus", csh)

    def test_tool_level_var_resolved(self):
        """tool 级变量能被解析"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  version: "23.1"
  tech_lef: "/path/to/tech.lef"
""")
        _write(self.flow_base / "cmds" / "pnr_innovus" / "step.yaml", """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -init $edp(script)"
        - "-tech_lef {tech_lef}"
      sub_steps:
        - global_place
""")

        builder = self._builder()
        sh = builder.build_step_shell("pnr_innovus", "place")

        self.assertIn("/path/to/tech.lef", sh)

    def test_shell_rejects_unsafe_invoke_pattern(self):
        """invoke 含危险 shell 片段时应拒绝生成。"""
        _write(self.flow_base / "cmds" / "pnr_innovus" / "step.yaml", """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -init $edp(script); rm -rf /"
      sub_steps:
        - global_place
""")
        builder = self._builder()
        with self.assertRaises(ValueError):
            builder.build_step_shell("pnr_innovus", "place")


# ── File Writing ──

class TestWriteStepScript(TestScriptBuilderBase):

    def test_write_creates_tcl(self):
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")

        tcl_path = self.workdir / "cmds" / "pnr_innovus" / "place" / "step.tcl"
        self.assertTrue(tcl_path.exists())
        content = tcl_path.read_text(encoding='utf-8')
        self.assertIn("Phase 1: Source", content)
        self.assertIn("Phase 2: Execute", content)

    def test_write_creates_debug_tcl(self):
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")

        debug_path = self.workdir / "cmds" / "pnr_innovus" / "place" / "debug.tcl"
        self.assertTrue(debug_path.exists())
        content = debug_path.read_text(encoding='utf-8')
        self.assertIn("EDP Debug Mode", content)

    def test_write_creates_sh_in_runs(self):
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")

        sh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place.sh"
        self.assertTrue(sh_path.exists())
        content = sh_path.read_text(encoding='utf-8')
        self.assertIn("#!/bin/bash", content)
        csh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place.csh"
        self.assertFalse(csh_path.exists())

    def test_write_creates_csh_in_runs_when_shell_is_csh(self):
        builder = self._builder(preferred_shell="csh")
        builder.write_step_script("pnr_innovus", "place")

        csh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place.csh"
        self.assertTrue(csh_path.exists())
        content = csh_path.read_text(encoding='utf-8')
        self.assertIn("#!/bin/csh", content)
        sh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place.sh"
        self.assertFalse(sh_path.exists())

    def test_write_debug_creates_debug_sh(self):
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place", debug=True)

        sh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place_debug.sh"
        self.assertTrue(sh_path.exists())
        content = sh_path.read_text(encoding='utf-8')
        self.assertIn("/debug.tcl", content)
        csh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place_debug.csh"
        self.assertFalse(csh_path.exists())

    def test_write_debug_creates_debug_csh_when_shell_is_csh(self):
        builder = self._builder(preferred_shell="csh")
        builder.write_step_script("pnr_innovus", "place", debug=True)

        csh_path = self.workdir / "runs" / "pnr_innovus" / "place" / "place_debug.csh"
        self.assertTrue(csh_path.exists())
        content = csh_path.read_text(encoding='utf-8')
        self.assertIn("/debug.tcl", content)

    def test_write_creates_config_tcl(self):
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")

        config_path = self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        self.assertTrue(config_path.exists())


# ── Overlay Chain ──

class TestOverlayChain(TestScriptBuilderBase):

    def test_overlay_step_override(self):
        overlay = self.test_dir / "overlay"
        _write(overlay / "cmds" / "pnr_innovus" / "step.yaml", """
pnr_innovus:
  supported_steps:
    place:
      invoke:
        - "innovus -win -init $edp(script)"
      sub_steps:
        - global_place
        - detail_place
        - extra_step
""")

        builder = self._builder(overlay=overlay)

        steps = builder.registry.get_sub_steps("pnr_innovus", "place")
        self.assertIn("extra_step", steps)
        self.assertEqual(len(steps), 3)

        sh = builder.build_step_shell("pnr_innovus", "place")
        self.assertIn("-win", sh)

    def test_overlay_new_step(self):
        overlay = self.test_dir / "overlay"
        _write(overlay / "cmds" / "pnr_innovus" / "step.yaml", """
pnr_innovus:
  supported_steps:
    place:
      sub_steps: [global_place, detail_place]
      invoke:
        - "innovus -init $edp(script)"
    cts:
      sub_steps: [cts_init]
      invoke: []
""")

        builder = self._builder(overlay=overlay)

        self.assertTrue(builder.registry.has_step("pnr_innovus", "place"))
        self.assertTrue(builder.registry.has_step("pnr_innovus", "cts"))


# ── LSF Config ──

class TestLsfConfig(TestScriptBuilderBase):

    def test_lsf_config_from_tool_level(self):
        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  lsf:
    lsf_mode: 1
    cpu_num: 8
    queue: normal
""")
        builder = self._builder()
        lsf = builder.get_lsf_config("pnr_innovus", "place")

        self.assertEqual(lsf['lsf_mode'], 1)
        self.assertEqual(lsf['cpu_num'], 8)
        self.assertEqual(lsf['queue'], 'normal')

    def test_lsf_step_overrides_tool(self):
        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  lsf:
    lsf_mode: 1
    cpu_num: 8
    queue: normal
  place:
    lsf:
      cpu_num: 32
      queue: high
""")
        builder = self._builder()
        lsf = builder.get_lsf_config("pnr_innovus", "place")

        self.assertEqual(lsf['cpu_num'], 32)
        self.assertEqual(lsf['queue'], 'high')

    def test_lsf_disabled(self):
        _write(self.flow_base / "cmds" / "pnr_innovus" / "config.yaml", """
pnr_innovus:
  lsf:
    lsf_mode: 0
""")
        builder = self._builder()
        lsf = builder.get_lsf_config("pnr_innovus", "place")

        self.assertEqual(lsf, {'lsf_mode': 0})


# ── Path Format ──

class TestPosixPath(TestScriptBuilderBase):

    def test_source_uses_forward_slashes(self):
        builder = self._builder()
        script = builder.build_step_script("pnr_innovus", "place")

        for line in script.split('\n'):
            if line.strip().startswith('source '):
                self.assertNotIn('\\', line)


# ── 端到端集成测试：YAML 类型编码 → config.tcl 正确性 ──

class TestConfigTclTypeEncoding(TestScriptBuilderBase):
    """端到端验证：config.yaml 中的各 Python 类型最终在 config.tcl 中正确编码。

    这是回归测试，防止 YAML → Tcl 路径上出现静默类型错误。
    """

    def _write_config_and_get_content(self, yaml_content: str) -> str:
        """写入 config.yaml，生成脚本，返回 config.tcl 内容。"""
        _write(
            self.flow_base / "cmds" / "pnr_innovus" / "config.yaml",
            yaml_content,
        )
        builder = self._builder()
        builder.write_step_script("pnr_innovus", "place")
        config_path = (
            self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        )
        return config_path.read_text(encoding="utf-8")

    def test_bool_true_becomes_1(self):
        """YAML true → Tcl 1，而非字符串 True"""
        content = self._write_config_and_get_content(
            "pnr_innovus:\n  lsf:\n    lsf_mode: true\n"
        )
        self.assertIn("set pnr_innovus(lsf,lsf_mode) {1}", content)
        self.assertNotIn("True", content)

    def test_bool_false_becomes_0(self):
        """YAML false → Tcl 0"""
        content = self._write_config_and_get_content(
            "pnr_innovus:\n  lsf:\n    lsf_mode: false\n"
        )
        self.assertIn("set pnr_innovus(lsf,lsf_mode) {0}", content)
        self.assertNotIn("False", content)

    def test_int_preserved(self):
        """整数值正确写出"""
        content = self._write_config_and_get_content(
            "pnr_innovus:\n  lsf:\n    cpu_num: 16\n"
        )
        self.assertIn("set pnr_innovus(lsf,cpu_num) {16}", content)

    def test_list_is_tcl_list_not_literal_string(self):
        """list 值编码为 [list ...] 命令，而非花括号包裹的字面字符串"""
        content = self._write_config_and_get_content(
            "pnr_innovus:\n  extra_args:\n    - -verbose\n    - -turbo\n"
        )
        # [list ...] 必须不在 {...} 内，否则 Tcl 会把它当字符串
        self.assertIn("set pnr_innovus(extra_args) [list", content)
        self.assertNotIn("set pnr_innovus(extra_args) {[list", content)

    def test_string_with_spaces_brace_quoted(self):
        """含空格的字符串用 {...} 保护"""
        content = self._write_config_and_get_content(
            "pnr_innovus:\n  log_msg: hello world\n"
        )
        self.assertIn("set pnr_innovus(log_msg) {hello world}", content)

    def test_overlay_bool_overrides_base(self):
        """overlay 中的 bool 值正确覆盖 base，override 标注也正确"""
        overlay = self.test_dir / "overlay"
        _write(
            overlay / "cmds" / "pnr_innovus" / "config.yaml",
            "pnr_innovus:\n  lsf:\n    lsf_mode: true\n",
        )
        _write(
            self.flow_base / "cmds" / "pnr_innovus" / "config.yaml",
            "pnr_innovus:\n  lsf:\n    lsf_mode: false\n",
        )
        builder = self._builder(overlay=overlay)
        builder.write_step_script("pnr_innovus", "place")
        content = (
            self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        ).read_text(encoding="utf-8")
        # overlay 写入 1，且标注 override
        self.assertIn("set pnr_innovus(lsf,lsf_mode) {1}", content)
        self.assertIn("[override]", content)

    def test_var_ref_expanded_across_files(self):
        """overlay 中引用 base 定义的 $var，写出时已展开"""
        overlay = self.test_dir / "overlay"
        _write(
            self.flow_base / "cmds" / "pnr_innovus" / "config.yaml",
            "base_path: /work/proj\n",
        )
        _write(
            overlay / "cmds" / "pnr_innovus" / "config.yaml",
            "report_dir: $base_path/reports\n",
        )
        builder = self._builder(overlay=overlay)
        builder.write_step_script("pnr_innovus", "place")
        content = (
            self.workdir / "cmds" / "pnr_innovus" / "place" / "config.tcl"
        ).read_text(encoding="utf-8")
        self.assertIn("set report_dir {/work/proj/reports}", content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
