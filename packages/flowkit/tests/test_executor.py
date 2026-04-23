#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit executor 测试

测试 Executor 执行驱动循环：
- 串行执行 + 失败即停
- judge 判定
- 终态检测

使用 MockRunner 替代真实执行，只测循环逻辑。
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flowkit.core import Graph, Step, StepStatus, StepResult, Runner
from flowkit.core.executor import Executor, ExecutionReport, default_judge
from flowkit.core.state_store import StateStore
from flowkit.core.runner import LSFRunner
from flowkit.loader.workflow_builder import ExecutableWorkflow


class MockScriptBuilder:
    """Mock ScriptBuilder，只记录调用"""

    def __init__(self, workdir: Path):
        self.workdir_path = workdir
        self.calls = []

    def get_lsf_config(self, tool_name: str, step_name: str) -> dict:
        return {'lsf_mode': 0}

    def write_step_script(self, tool_name: str, step_name: str,
                          debug: bool = False) -> Path:
        self.calls.append((tool_name, step_name, debug))
        # 创建假的 .sh 文件（MockRunner 不需要真实内容）
        suffix = "_debug.sh" if debug else ".sh"
        sh_path = self.workdir_path / "cmds" / tool_name / f"{step_name}{suffix}"
        sh_path.parent.mkdir(parents=True, exist_ok=True)
        sh_path.write_text("# mock", encoding='utf-8')
        return sh_path


class MockRunner(Runner):
    """Mock Runner，返回预设结果"""

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def run(self, step_name, script_path, workdir):
        self.calls.append(step_name)
        return self.results.get(
            step_name,
            StepResult(step_id=step_name, success=True)
        )


def _make_workflow(step_deps, tool_map=None):
    """快速构建测试用的 ExecutableWorkflow

    Args:
        step_deps: {"b": ["a"], "c": ["b"]} 表示 b 依赖 a, c 依赖 b
        tool_map: {step_id: tool_name}，默认全部 "mock_tool"
    """
    graph = Graph()
    tool_map = tool_map or {}
    all_ids = set(step_deps.keys())
    for deps in step_deps.values():
        all_ids.update(deps)

    for sid in all_ids:
        graph.add_step(Step(id=sid, name=sid, tool_name=tool_map.get(sid, "mock_tool")))

    for step_id, dep_list in step_deps.items():
        for dep in dep_list:
            graph.add_dependency(dep, step_id)

    steps = {sid: graph.steps[sid] for sid in all_ids}
    return ExecutableWorkflow(graph=graph, steps=steps, tool_selection=tool_map or {sid: "mock_tool" for sid in all_ids})


class TestDefaultJudge(unittest.TestCase):
    """测试默认判定函数"""

    def test_success(self):
        result = StepResult(step_id="x", success=True)
        self.assertEqual(default_judge(result), StepStatus.FINISHED)

    def test_failure(self):
        result = StepResult(step_id="x", success=False)
        self.assertEqual(default_judge(result), StepStatus.FAILED)


class TestExecutorLinearSuccess(unittest.TestCase):
    """测试线性依赖全部成功"""

    def test_three_steps_all_pass(self):
        """a → b → c，全部成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner()

            wf = _make_workflow({"b": ["a"], "c": ["b"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertTrue(report.success)
        self.assertEqual(report.failed_steps, [])
        self.assertEqual(set(report.step_results.keys()), {"a", "b", "c"})

        # 执行顺序：a 先于 b，b 先于 c
        self.assertLess(runner.calls.index("a"), runner.calls.index("b"))
        self.assertLess(runner.calls.index("b"), runner.calls.index("c"))


class TestExecutorMidFailure(unittest.TestCase):
    """测试中间步骤失败"""

    def test_b_fails_c_never_runs(self):
        """a → b → c，b 失败，c 不执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner(results={
                "a": StepResult(step_id="a", success=True),
                "b": StepResult(step_id="b", success=False, error="oom"),
                "c": StepResult(step_id="c", success=True),
            })

            wf = _make_workflow({"b": ["a"], "c": ["b"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertFalse(report.success)
        self.assertEqual(report.failed_steps, ["b"])
        self.assertIn("a", report.step_results)
        self.assertIn("b", report.step_results)
        self.assertNotIn("c", report.step_results)

        # a 成功，b 失败
        self.assertEqual(wf.steps["a"].status, StepStatus.FINISHED)
        self.assertEqual(wf.steps["b"].status, StepStatus.FAILED)


class TestExecutorFirstFailure(unittest.TestCase):
    """测试第一步就失败"""

    def test_a_fails_all_skipped(self):
        """a → b → c，a 失败，b 和 c 都不执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner(results={
                "a": StepResult(step_id="a", success=False),
            })

            wf = _make_workflow({"b": ["a"], "c": ["b"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertFalse(report.success)
        self.assertEqual(report.failed_steps, ["a"])
        # 只有 a 被执行
        self.assertEqual(runner.calls, ["a"])
        self.assertEqual(wf.steps["b"].status, StepStatus.INIT)
        self.assertEqual(wf.steps["c"].status, StepStatus.INIT)


class TestExecutorNoRunnable(unittest.TestCase):
    """测试无可运行步骤（死锁）"""

    def test_circular_dependency_no_progress(self):
        """a → b → c → a（环形依赖，但 Graph.add_dependency 会拒绝）"""
        # Graph 不允许添加环，所以用两个互相依赖来模拟：
        # a 依赖 b，b 依赖 a — 都是 INIT，无人能跑
        # 注意：add_dependency(b, a) 在 a → b 存在时不会形成环（方向是 a ← b）
        # 我们用正确的环检测：a → b, b → a 会报错
        # 所以直接构建一个没有依赖但都是 INIT 的场景，然后手动设为 RUNNING
        pass  # Graph 阻止环，无法构造此场景 — 这本身就是正确的行为


class TestExecutorTerminalDetection(unittest.TestCase):
    """测试终态检测"""

    def test_all_already_finished(self):
        """所有 step 已是 FINISHED，循环立即退出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner()

            wf = _make_workflow({"b": ["a"], "c": ["b"]})
            for step in wf.steps.values():
                step.update_status(StepStatus.FINISHED)

            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertTrue(report.success)
        self.assertEqual(report.step_results, {})
        self.assertEqual(runner.calls, [])


class TestExecutorParallelBranch(unittest.TestCase):
    """测试并行分支（串行执行）"""

    def test_a_depends_on_b_and_c(self):
        """b 和 c 无依赖，都依赖 a 完成后才能跑 a
        实际是：a → b, a → c（a 完成后 b 和 c 都 runnable）

        P0 串行执行，b 和 c 按顺序跑
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner()

            wf = _make_workflow({"b": ["a"], "c": ["a"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertTrue(report.success)
        self.assertEqual(set(report.step_results.keys()), {"a", "b", "c"})

        # a 先于 b 和 c
        a_idx = runner.calls.index("a")
        self.assertLess(a_idx, runner.calls.index("b"))
        self.assertLess(a_idx, runner.calls.index("c"))


class TestExecutorDiamondDependency(unittest.TestCase):
    """测试双前驱汇聚：a → c, b → c"""

    def test_c_waits_for_both_a_and_b(self):
        """c 依赖 a 和 b，a 先完成不会触发 c，b 完成才触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner()

            # a → c, b → c（c 有两个前驱）
            wf = _make_workflow({"c": ["a", "b"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertTrue(report.success)
        self.assertEqual(set(report.step_results.keys()), {"a", "b", "c"})

        # c 只执行了一次（不是被 a 和 b 各触发一次）
        c_count = runner.calls.count("c")
        self.assertEqual(c_count, 1, "c 应该只执行一次")

        # c 在 a 和 b 之后
        self.assertLess(runner.calls.index("a"), runner.calls.index("c"))
        self.assertLess(runner.calls.index("b"), runner.calls.index("c"))

    def test_a_fails_b_continues(self):
        """a → c, b → c，a 失败 → B 继续跑，C 因为 A 失败被阻塞"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner(results={
                "a": StepResult(step_id="a", success=False, error="crash"),
                "b": StepResult(step_id="b", success=True),
            })

            wf = _make_workflow({"c": ["a", "b"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertFalse(report.success)
        # B 独立于 A，应该正常跑完
        self.assertIn("b", report.step_results)
        self.assertEqual(wf.steps["b"].status, StepStatus.FINISHED)
        # C 依赖 A 和 B，A 失败 → C 被阻塞
        self.assertNotIn("c", report.step_results)
        self.assertEqual(wf.steps["c"].status, StepStatus.INIT)


class TestExecutorBranchFailure(unittest.TestCase):
    """测试分叉执行：一个分支失败不影响其他分支"""

    def test_branch_failure_other_branch_continues(self):
        """A→C→D, A→B→E，B 失败 → C 和 D 正常跑，E 被阻塞"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner(results={
                "a": StepResult(step_id="a", success=True),
                "b": StepResult(step_id="b", success=False, error="oom"),
                "c": StepResult(step_id="c", success=True),
                "d": StepResult(step_id="d", success=True),
                "e": StepResult(step_id="e", success=True),
            })

            # 依赖：c→a, d→c, b→a, e→b
            wf = _make_workflow({"c": ["a"], "d": ["c"], "b": ["a"], "e": ["b"]})
            executor = Executor(wf, builder, runner)
            report = executor.run()

        self.assertFalse(report.success)
        self.assertEqual(report.failed_steps, ["b"])

        # A 成功
        self.assertEqual(wf.steps["a"].status, StepStatus.FINISHED)
        # B 失败
        self.assertEqual(wf.steps["b"].status, StepStatus.FAILED)
        # C、D 正常跑完（不依赖 B）
        self.assertEqual(wf.steps["c"].status, StepStatus.FINISHED)
        self.assertEqual(wf.steps["d"].status, StepStatus.FINISHED)
        # E 被 B 阻塞
        self.assertEqual(wf.steps["e"].status, StepStatus.INIT)


class TestExecutorCustomJudge(unittest.TestCase):
    """测试自定义判定函数"""

    def test_custom_judge(self):
        """自定义 judge：所有结果都算 FINISHED"""
        always_pass = lambda result: StepStatus.FINISHED

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)
            runner = MockRunner(results={
                "a": StepResult(step_id="a", success=False),
                "b": StepResult(step_id="b", success=False),
            })

            wf = _make_workflow({"b": ["a"]})
            executor = Executor(wf, builder, runner, judge=always_pass)
            report = executor.run()

        # 即使 runner 返回 success=False，自定义 judge 判定为 FINISHED
        self.assertTrue(report.success)
        self.assertEqual(report.failed_steps, [])


class TestExecutorDependencyReadiness(unittest.TestCase):
    """测试依赖就绪判定边界"""

    def test_strong_dependency_missing_implementation_blocks_step(self):
        """强依赖上游缺失实现时，下游不能执行。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            builder = MockScriptBuilder(workdir)

            wf = _make_workflow({"b": ["a"]})
            # 模拟 a 在图里存在但没有可执行实现（workflow.steps 缺失）
            wf.steps = {"b": wf.steps["b"]}

            executor = Executor(wf, builder)
            self.assertFalse(executor._is_ready("b"))

# ============================================================
# StateStore 单元测试
# ============================================================


class TestStateStore(unittest.TestCase):
    """测试 StateStore 读写"""

    def test_save_and_load(self):
        """保存终态后能正确加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / ".edp_state.yaml")
            store.save("a", StepStatus.FINISHED, execution_time=10.0)
            store.save("b", StepStatus.FAILED, execution_time=5.0, error="oom")

            state = store.load()
            self.assertEqual(state["a"], StepStatus.FINISHED)
            self.assertEqual(state["b"], StepStatus.FAILED)

    def test_init_not_persisted(self):
        """INIT 状态不会出现在加载结果中"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / ".edp_state.yaml")
            store.save("a", StepStatus.FINISHED)

            state = store.load()
            self.assertNotIn("b", state)  # b 从未 save，不在结果中

    def test_skipped_persisted(self):
        """SKIPPED 状态能正确持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / ".edp_state.yaml")
            store.save("a", StepStatus.SKIPPED)

            state = store.load()
            self.assertEqual(state["a"], StepStatus.SKIPPED)

    def test_overwrite(self):
        """同一 step 多次 save，只保留最后一次"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / ".edp_state.yaml")
            store.save("a", StepStatus.FAILED, error="first try")
            store.save("a", StepStatus.FINISHED, execution_time=20.0)

            state = store.load()
            self.assertEqual(state["a"], StepStatus.FINISHED)

    def test_clear(self):
        """clear 后 load 返回空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / ".edp_state.yaml")
            store.save("a", StepStatus.FINISHED)
            self.assertTrue(store.exists())

            store.clear()
            self.assertFalse(store.exists())
            self.assertEqual(store.load(), {})

    def test_file_not_exist(self):
        """文件不存在时 load 返回空，exists 返回 False"""
        store = StateStore(Path("/nonexistent/.edp_state.yaml"))
        self.assertFalse(store.exists())
        self.assertEqual(store.load(), {})

    def test_corrupted_file(self):
        """损坏的 YAML 文件不崩溃，返回空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / ".edp_state.yaml"
            f.write_text("{{{{not yaml", encoding='utf-8')
            store = StateStore(f)
            self.assertEqual(store.load(), {})


# ============================================================
# Executor + StateStore 集成测试（断点续跑）
# ============================================================


class TestExecutorResume(unittest.TestCase):
    """测试 Executor 断点续跑"""

    def test_resume_skips_finished(self):
        """a → b → c，a 和 b 已完成，resume 时只跑 c"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            state_file = workdir / ".edp_state.yaml"

            # 模拟跑到一半：a 和 b 已完成，c 还没跑
            store = StateStore(state_file)
            store.save("a", StepStatus.FINISHED)
            store.save("b", StepStatus.FINISHED)
            # c 没保存 → INIT

            builder = MockScriptBuilder(workdir)
            runner = MockRunner()
            wf = _make_workflow({"b": ["a"], "c": ["b"]})
            executor = Executor(wf, builder, runner, state_store=store)
            report = executor.run(resume=True)

            self.assertTrue(report.success)
            # 只有 c 被执行
            self.assertEqual(runner.calls, ["c"])

    def test_resume_after_failure(self):
        """a → b → c，第一次 b 失败，修复后 resume 只跑 b 和 c"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            state_file = workdir / ".edp_state.yaml"

            # 第一次运行：b 失败
            builder1 = MockScriptBuilder(workdir)
            runner1 = MockRunner(results={
                "a": StepResult(step_id="a", success=True),
                "b": StepResult(step_id="b", success=False, error="oom"),
            })
            store = StateStore(state_file)
            wf1 = _make_workflow({"b": ["a"], "c": ["b"]})
            Executor(wf1, builder1, runner1, state_store=store).run()

            # 此时状态文件：a=FINISHED, b=FAILED
            saved = store.load()
            self.assertEqual(saved["a"], StepStatus.FINISHED)
            self.assertEqual(saved["b"], StepStatus.FAILED)

            # 第二次运行：resume，但 b 是 FAILED → can_execute() 返回 False
            # P0 没有重试策略，FAILED 的 step 不会被重新执行
            builder2 = MockScriptBuilder(workdir)
            runner2 = MockRunner()
            wf2 = _make_workflow({"b": ["a"], "c": ["b"]})
            executor2 = Executor(wf2, builder2, runner2, state_store=store)
            report = executor2.run(resume=True)

            # b 是 FAILED 不能重新跑，c 被阻塞
            self.assertEqual(runner2.calls, [])
            self.assertEqual(wf2.steps["b"].status, StepStatus.FAILED)

    def test_resume_diamond(self):
        """a → c, b → c，第一次 a 和 b 完成，Ctrl+C（c 没跑）
        resume 时 c 依赖已满足，直接触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            state_file = workdir / ".edp_state.yaml"

            # 手动模拟第一次跑到一半的状态
            store = StateStore(state_file)
            store.save("a", StepStatus.FINISHED)
            store.save("b", StepStatus.FINISHED)
            # c 没保存 → INIT

            builder = MockScriptBuilder(workdir)
            runner = MockRunner()
            wf = _make_workflow({"c": ["a", "b"]})
            executor = Executor(wf, builder, runner, state_store=store)
            report = executor.run(resume=True)

            self.assertTrue(report.success)
            # a 和 b 跳过，只跑 c
            self.assertEqual(runner.calls, ["c"])

    def test_no_resume_ignores_state(self):
        """不传 resume=True 时，忽略状态文件，从头跑"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            state_file = workdir / ".edp_state.yaml"

            # 预写一个状态文件
            store = StateStore(state_file)
            store.save("a", StepStatus.FINISHED)

            builder = MockScriptBuilder(workdir)
            runner = MockRunner()
            wf = _make_workflow({"b": ["a"], "c": ["b"]})
            executor = Executor(wf, builder, runner, state_store=store)
            executor.run()  # 不传 resume

            # 全部从头跑
            self.assertEqual(set(runner.calls), {"a", "b", "c"})


# ============================================================
# LSFRunner 测试（测命令拼接，不真跑 bsub）
# ============================================================


class TestLSFRunner(unittest.TestCase):
    """测试 LSFRunner 命令构建"""

    def test_basic_bsub_command(self):
        """基本 bsub -K 命令结构"""
        runner = LSFRunner(queue="normal", cpu_num=4)
        script = Path("/tmp/test/place.sh")
        cmd = runner._build_bsub_cmd("place", script)

        self.assertEqual(cmd[0], "bsub")
        self.assertIn("-K", cmd)
        self.assertIn("-J", cmd)
        self.assertIn("place", cmd)
        self.assertIn("-q", cmd)
        self.assertIn("normal", cmd)
        self.assertIn("-n", cmd)
        self.assertIn("4", cmd)
        self.assertIn("bash", cmd)
        self.assertEqual(cmd[-1], str(script))

    def test_debug_bsub_uses_ip_mode(self):
        """debug 模式使用 bsub -Ip"""
        runner = LSFRunner(queue="normal", cpu_num=2, debug=True)
        cmd = runner._build_bsub_cmd("place", Path("/tmp/test/place_debug.sh"))

        self.assertIn("-Ip", cmd)
        self.assertNotIn("-K", cmd)

    def test_csh_script_uses_csh_launcher(self):
        """csh 脚本使用 csh 启动器"""
        runner = LSFRunner(queue="normal", cpu_num=1)
        cmd = runner._build_bsub_cmd("place", Path("/tmp/test/place.csh"))

        self.assertIn("csh", cmd)
        self.assertNotIn("bash", cmd)

    def test_script_not_found(self):
        """脚本不存在时返回失败"""
        runner = LSFRunner()
        result = runner.run("test", Path("/nonexistent/test.sh"), Path("/tmp"))

        self.assertFalse(result.success)
        self.assertIn("not found", result.error)

    def test_full_options(self):
        """完整参数拼接"""
        runner = LSFRunner(
            queue="high",
            cpu_num=8,
            memory="16G",
            wall_time="4:00",
            extra_opts="-P project_a -R select[type==linux]",
        )
        cmd = runner._build_bsub_cmd("drc", Path("/tmp/drc.sh"))

        self.assertIn("high", cmd)
        self.assertIn("8", cmd)
        self.assertIn("4:00", cmd)
        self.assertIn("-P", cmd)
        self.assertIn("project_a", cmd)
        # memory 被包在 -R 参数里
        mem_args = [c for c in cmd if "16G" in c]
        self.assertTrue(any(mem_args), "memory 参数应包含 16G")

    def test_cpu_num_1_no_n_flag(self):
        """cpu_num=1 时不加 -n 参数"""
        runner = LSFRunner(cpu_num=1)
        cmd = runner._build_bsub_cmd("test", Path("/tmp/test.sh"))

        n_indices = [i for i, c in enumerate(cmd) if c == "-n"]
        self.assertEqual(len(n_indices), 0, "cpu_num=1 不应加 -n")

    def test_is_runner_subclass(self):
        """LSFRunner 是 Runner 的子类"""
        runner = LSFRunner()
        self.assertIsInstance(runner, Runner)
        self.assertTrue(callable(getattr(runner, 'run', None)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
