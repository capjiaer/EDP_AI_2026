#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
flowkit.core.runner - 步骤执行器

Runner 只管跑一个 step 的脚本，不关心流程、依赖、重试。
接口：run(step_name, script_path, workdir) -> StepResult
"""

import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from .step import StepResult


def _resolve_shell_executable(script_path: Path) -> str:
    """根据脚本后缀选择执行器"""
    if script_path.suffix.lower() == ".csh":
        return "csh"
    return "bash"


class Runner(ABC):
    """Runner 基类"""

    @abstractmethod
    def run(self, step_name: str, script_path: Path, workdir: Path) -> StepResult:
        """
        跑一个 step 的脚本。

        Args:
            step_name: step 名称（用于日志）
            script_path: 要执行的脚本路径
            workdir: 工作目录

        Returns:
            StepResult
        """
        ...


class LocalRunner(Runner):
    """本地执行 — subprocess.run"""

    def __init__(self, timeout: int = 0):
        """
        Args:
            timeout: 超时秒数，0 表示不限制
        """
        self.timeout = timeout

    def run(self, step_name: str, script_path: Path, workdir: Path) -> StepResult:
        if not script_path.exists():
            return StepResult(
                step_id=step_name,
                success=False,
                error=f"Script not found: {script_path}",
            )

        start = time.time()
        try:
            shell_exec = _resolve_shell_executable(script_path)
            proc = subprocess.run(
                [shell_exec, str(script_path)],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=self.timeout or None,
            )
            elapsed = time.time() - start
            result = StepResult(
                step_id=step_name,
                success=(proc.returncode == 0),
                output=proc.stdout,
                error=proc.stderr,
                execution_time=elapsed,
            )
            if not result.success:
                launcher = _resolve_shell_executable(script_path)
                hint = (f"Launcher: {launcher}\n"
                        f"Script: {script_path}\n"
                        f"Workdir: {workdir}\n")
                result.error = hint + (result.error or "")
            return result
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            return StepResult(
                step_id=step_name,
                success=False,
                error=f"Timeout after {self.timeout}s",
                execution_time=elapsed,
            )


class LSFRunner(Runner):
    """LSF 集群执行 — bsub -K

    通过 bsub -K 提交 job 到集群，阻塞等待完成。
    bsub 参数通过构造函数传入，可全局配置也可按 step 覆盖。
    """

    def __init__(self,
                 queue: str = "normal",
                 cpu_num: int = 1,
                 memory: str = "",
                 wall_time: str = "",
                 extra_opts: str = "",
                 job_name: str = "",
                 hosts: str = "",
                 debug: bool = False):
        """
        Args:
            queue: 队列名称
            cpu_num: CPU 核数
            memory: 内存限制（如 "8G"）
            wall_time: 最大运行时间（如 "4:00"）
            extra_opts: 额外 bsub 参数字符串
            job_name: 自定义 job 名称（默认 step_name）
            hosts: 主机约束，对应 bsub -m（如 "hostA hostB"）
        """
        self.queue = queue
        self.cpu_num = cpu_num
        self.memory = memory
        self.wall_time = wall_time
        self.extra_opts = extra_opts
        self.job_name = job_name
        self.hosts = hosts
        self.debug = debug

    def run(self, step_name: str, script_path: Path, workdir: Path) -> StepResult:
        if not script_path.exists():
            return StepResult(
                step_id=step_name,
                success=False,
                error=f"Script not found: {script_path}",
            )

        cmd = self._build_bsub_cmd(step_name, script_path)
        cmd_str = " ".join(cmd)

        start = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(workdir),
                capture_output=True,
                text=True,
            )
            elapsed = time.time() - start
            result = StepResult(
                step_id=step_name,
                success=(proc.returncode == 0),
                output=proc.stdout,
                error=proc.stderr,
                execution_time=elapsed,
            )
            if not result.success:
                hint = (f"LSF command: {cmd_str}\n"
                        f"Script: {script_path}\n"
                        f"Workdir: {workdir}\n")
                result.error = hint + (result.error or "")
            return result
        except Exception as e:
            elapsed = time.time() - start
            return StepResult(
                step_id=step_name,
                success=False,
                error=str(e),
                execution_time=elapsed,
            )

    def _build_bsub_cmd(self, step_name: str, script_path: Path) -> list:
        """构建 bsub 命令"""
        mode_flag = "-Ip" if self.debug else "-K"
        effective_job_name = self.job_name or step_name
        cmd = ["bsub", mode_flag, "-J", effective_job_name]

        if self.queue:
            cmd.extend(["-q", self.queue])
        if self.cpu_num > 1:
            cmd.extend(["-n", str(self.cpu_num)])
        if self.hosts:
            cmd.extend(["-m", self.hosts])
        if self.memory:
            cmd.extend(["-R", f"span[hosts=1] rusage[mem={self.memory}]"])
        if self.wall_time:
            cmd.extend(["-W", self.wall_time])
        if self.extra_opts:
            cmd.extend(self.extra_opts.split())

        cmd.append(_resolve_shell_executable(script_path))
        cmd.append(str(script_path))
        return cmd
