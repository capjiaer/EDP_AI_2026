#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.core.executor - 执行驱动器

Executor 是唯一的驱动者，采用事件驱动（级联触发）模式：
  执行 step → 通知下游 → 依赖满足则触发 → 级联直到无新触发
不生产决策，只传递决策。
"""

import click
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .step import Step, StepStatus, StepResult
from .runner import Runner, LocalRunner, LSFRunner
from .state_store import StateStore


@dataclass
class ExecutionReport:
    """执行报告"""

    success: bool
    step_results: Dict[str, StepResult]
    total_time: float
    failed_steps: List[str] = field(default_factory=list)
    skipped_steps: List[str] = field(default_factory=list)


def default_judge(result: StepResult) -> StepStatus:
    """默认判定规则：exit 0 → FINISHED，否则 → FAILED"""
    return StepStatus.FINISHED if result.success else StepStatus.FAILED


class Executor:
    """执行驱动器

    事件驱动：step 完成后级联触发下游，依赖满足即执行。
    失败的 step 不级联，但其他分支继续执行。
    Runner 由 config.yaml 中的 LSF 配置动态决定，每步可不同。

    Args:
        workflow: 可执行工作流（ExecutableWorkflow），单步模式可为 None
        script_builder: 脚本生成器（ScriptBuilder）
        judge: 判定函数，默认 default_judge
        state_store: 状态持久化，默认 None（不持久化）
        dry_run: 预览模式，不实际执行
        skip_steps: 跳过的 step 列表（标记为 FINISHED）
        force: 强制重跑，忽略已有状态
    """

    def __init__(self, workflow, script_builder,
                 judge: Optional[Callable[[StepResult], StepStatus]] = None,
                 state_store: Optional[StateStore] = None,
                 dry_run: bool = False,
                 skip_steps: Optional[List[str]] = None,
                 force: bool = False,
                 debug: bool = False,
                 verbose: bool = False):
        self.workflow = workflow
        self.script_builder = script_builder
        self.judge = judge or default_judge
        self.state_store = state_store
        self.dry_run = dry_run
        self.skip_steps = set(skip_steps or [])
        self.force = force
        self.debug = debug
        self.verbose = verbose
        self._step_results: Dict[str, StepResult] = {}
        self._default_runner = LocalRunner()

    def _print_debug_launch(self, step_id: str, runner: Runner, script_path) -> None:
        """debug 模式下打印执行入口信息"""
        if not self.debug:
            return
        click.echo(f"[DEBUG] launching {step_id} via {type(runner).__name__}")
        click.echo(f"[DEBUG] script: {script_path}")

    def _print_failure_hint(self, step_id: str, result: StepResult) -> None:
        """失败时打印简短诊断信息"""
        if result.success:
            return
        click.echo(click.style(f"[FAIL] {step_id} execution failed.", fg='red'))
        if result.error:
            lines = result.error.strip().splitlines()
            if self.verbose:
                click.echo("       details:")
                for line in lines:
                    click.echo(f"         {line}")
            else:
                click.echo(f"       reason: {lines[0]}")

    def _get_runner(self, tool_name: str, step_name: str) -> Runner:
        """根据 config 动态选择 runner"""
        lsf_config = self.script_builder.get_lsf_config(tool_name, step_name)
        if lsf_config.get('lsf_mode', 0) == 1:
            return LSFRunner(
                queue=lsf_config.get('queue', 'normal'),
                cpu_num=lsf_config.get('cpu_num', 1),
                debug=self.debug,
            )
        return self._default_runner

    def run(self, resume: bool = False) -> ExecutionReport:
        """驱动执行（全图或子图）

        Args:
            resume: 是否从上次中断处恢复

        Returns:
            ExecutionReport
        """
        start = time.time()
        self._step_results = {}

        # force: 清空所有状态
        if self.force:
            for step in self.workflow.steps.values():
                step.reset()
            if self.state_store:
                self.state_store.clear()
            resume = False

        # 恢复已有状态
        if resume and self.state_store:
            saved = self.state_store.load()
            for sid, status in saved.items():
                if sid in self.workflow.steps:
                    self.workflow.steps[sid].update_status(status)

        # skip: 标记跳过的 step 为 FINISHED
        for step_id in self.skip_steps:
            if step_id in self.workflow.steps:
                self.workflow.steps[step_id].update_status(StepStatus.FINISHED)
            if self.state_store:
                self.state_store.save(step_id, StepStatus.SKIPPED)

        # 找初始可运行的 step
        current_state = {
            sid: step.status for sid, step in self.workflow.steps.items()
        }
        runnable = self.workflow.graph.get_runnable_steps(current_state)

        for step_id in runnable:
            self._execute_and_cascade(step_id)

        elapsed = time.time() - start
        return self._build_report(elapsed)

    def run_single(self, tool_name: str, step_name: str) -> ExecutionReport:
        """执行单个 step（脱离图）

        Args:
            tool_name: 工具名
            step_name: step 名

        Returns:
            ExecutionReport
        """
        start = time.time()
        self._step_results = {}

        sh_path = self.script_builder.write_step_script(
            tool_name, step_name, debug=self.debug
        )

        if self.dry_run:
            runner = self._get_runner(tool_name, step_name)
            runner_type = type(runner).__name__
            click.echo(f"[DRY-RUN] {tool_name}.{step_name} via {runner_type}")
            click.echo(f"          script: {sh_path}")
            elapsed = time.time() - start
            return ExecutionReport(
                success=True, step_results={}, total_time=elapsed,
                failed_steps=[], skipped_steps=[],
            )

        runner = self._get_runner(tool_name, step_name)
        self._print_debug_launch(step_name, runner, sh_path)
        result = runner.run(step_name, sh_path, self.script_builder.workdir_path)
        self._step_results[step_name] = result
        self._print_failure_hint(step_name, result)

        verdict = self.judge(result)
        if self.state_store:
            self.state_store.save(
                step_name, verdict,
                execution_time=result.execution_time,
                error=result.error,
            )

        elapsed = time.time() - start
        return ExecutionReport(
            success=result.success,
            step_results={step_name: result},
            total_time=elapsed,
            failed_steps=[] if result.success else [step_name],
            skipped_steps=[],
        )

    def _execute_and_cascade(self, step_id: str) -> None:
        """执行一个 step 并级联触发下游"""
        # step 没有 tool 配置 → 标记 FAILED
        if step_id not in self.workflow.steps:
            tool = self.workflow.tool_selection.get(step_id, '')
            msg = (f"Step '{step_id}' has no tool implementation. "
                   f"Flow owner needs to provide it.") if not tool else \
                  f"Tool '{tool}' does not support step '{step_id}'. Check step.yaml."
            if self.state_store:
                self.state_store.save(step_id, StepStatus.FAILED, error=msg)
            self._step_results[step_id] = StepResult(
                step_id=step_id, success=False,
                execution_time=0.0, error=msg,
            )
            return

        step = self.workflow.steps[step_id]
        if not step.can_execute():
            return
        if not self._is_ready(step_id):
            return  # 依赖未满足，等上游级联过来

        # 1. 生成脚本
        sh_path = self.script_builder.write_step_script(
            step.tool_name, step_id, debug=self.debug
        )

        # 2. 标记运行中
        step.update_status(StepStatus.RUNNING)

        # 3. 执行
        if self.dry_run:
            runner = self._get_runner(step.tool_name, step_id)
            runner_type = type(runner).__name__
            click.echo(f"  [DRY-RUN] {step_id}: {step.tool_name} via {runner_type}")
            result = StepResult(
                step_id=step_id, success=True, execution_time=0.0
            )
        else:
            runner = self._get_runner(step.tool_name, step_id)
            self._print_debug_launch(step_id, runner, sh_path)
            result = runner.run(
                step_id, sh_path, self.script_builder.workdir_path
            )
        self._step_results[step_id] = result
        self._print_failure_hint(step_id, result)

        # 4. 判定
        verdict = self.judge(result)

        # 5. 更新状态机
        step.update_status(verdict)

        # 6. 持久化终态
        if self.state_store and not self.dry_run:
            self.state_store.save(
                step_id, verdict,
                execution_time=result.execution_time,
                error=result.error,
            )

        # 7. 失败不级联，但其他分支不受影响
        if verdict in (StepStatus.FAILED, StepStatus.CANCELLED):
            return

        # 8. 级联触发下游
        for dep_id in self.workflow.graph.get_dependencies(step_id):
            self._execute_and_cascade(dep_id)

    def _is_ready(self, step_id: str) -> bool:
        """检查 step 的所有强依赖是否已满足"""
        for dep in self.workflow.graph.dependencies:
            if dep.to_step == step_id:
                source_step = self.workflow.steps.get(dep.from_step)
                if source_step is None:
                    if dep.weak:
                        continue
                    return False
                source_status = source_step.status
                if dep.weak:
                    continue  # 弱依赖不阻塞
                if source_status not in (StepStatus.FINISHED, StepStatus.SKIPPED):
                    return False
        return True

    def _build_report(self, elapsed: float) -> ExecutionReport:
        """构建执行报告"""
        failed = [sid for sid, s in self.workflow.steps.items()
                  if s.status == StepStatus.FAILED]
        skipped = [sid for sid, s in self.workflow.steps.items()
                   if s.status in (StepStatus.SKIPPED, StepStatus.CANCELLED)]

        return ExecutionReport(
            success=len(failed) == 0,
            step_results=dict(self._step_results),
            total_time=elapsed,
            failed_steps=failed,
            skipped_steps=skipped,
        )
