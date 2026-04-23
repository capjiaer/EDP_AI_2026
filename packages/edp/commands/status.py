#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.status - Show execution status
"""

import click

from flowkit import StateStore, StepStatus
from flowkit.loader.dependency_loader import DependencyLoader
from edp.context import _resolve_context, _pick_graph_config


@click.command()
@click.pass_context
def status(ctx):
    """Show step execution status of current branch.

    Displays each step's status (INIT / RUNNING / FINISHED / FAILED / SKIPPED)
    based on the persisted state file under your branch directory.

    \b
    Must be run inside a branch directory:
      .../WORK_PATH/{project}/{version}/{block}/{user}/{branch}
    """
    edp_center = ctx.obj['edp_center']
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_context(ctx)

    # 加载图获取所有 step 名
    graph_config = _pick_graph_config(context['graph_configs'], context['branch_path'])
    loader = DependencyLoader()
    graph = loader.load_from_multiple_files([graph_config])
    all_steps = sorted(graph.steps.keys())

    # 加载已持久化的状态
    state_file = context['branch_path'] / 'state.yaml'
    state_store = StateStore(state_file)

    if not state_store.exists():
        click.echo("No execution history yet.")
        click.echo("")
        click.echo("  Quick start:")
        click.echo("    edp run                Run all steps")
        click.echo("    edp run drc            Run a single step")
        click.echo("    edp run -fr syn -to drc   Run a sub-graph")
        return

    # 检测图是否匹配
    saved_graph = state_store.load_graph_config()
    if saved_graph and saved_graph != graph_config.name:
        click.echo(click.style(
            f"Warning: state was created with {saved_graph}, "
            f"but current graph is {graph_config.name}.",
            fg='yellow'
        ))

    saved = state_store.load()

    # 打印状态表
    click.echo(f"{'Step':<20} {'Status':<12}")
    click.echo("-" * 32)
    for step_id in all_steps:
        step_status = saved.get(step_id, StepStatus.INIT)
        color = {
            StepStatus.FINISHED: 'green',
            StepStatus.FAILED: 'red',
            StepStatus.SKIPPED: 'yellow',
            StepStatus.INIT: 'white',
        }.get(step_status, 'white')
        click.echo(click.style(
            f"{step_id:<20} {step_status.value:<12}", fg=color
        ))
