#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.retry - Retry a failed step
"""

import click

from flowkit import (
    Executor,
    StateStore,
    StepStatus,
    WorkflowBuilder,
)
from edp.context import _resolve_context, _pick_graph_config


@click.command()
@click.argument('step')
@click.option('-dr', '--dry-run', is_flag=True, default=False,
              help='Preview mode, no actual execution')
@click.option('-debug', '--debug', is_flag=True, default=False,
              help='Run in debug mode (execute *_debug.sh / LSF -Ip)')
@click.option('-info', '--info', 'info_mode', is_flag=True, default=False,
              help='Show full error details on step failure')
@click.pass_context
def retry(ctx, step, dry_run, debug, info_mode):
    """Retry a failed step (clear its state and resume)."""
    edp_center = ctx.obj['edp_center']
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_context(ctx)

    state_file = context['branch_path'] / 'state.yaml'
    state_store = StateStore(state_file)

    if not state_store.exists():
        raise click.ClickException("No execution history to retry.")

    # 选择图配置
    graph_config = _pick_graph_config(context['graph_configs'], context['branch_path'])

    # 检测图是否匹配
    saved_graph = state_store.load_graph_config()
    if saved_graph and saved_graph != graph_config.name:
        raise click.ClickException(
            f"State was created with {saved_graph}, "
            f"but current graph is {graph_config.name}.\n"
            f"  Use 'edp graph' to switch back, or 'edp run' to start fresh."
        )

    saved = state_store.load()

    if step not in saved:
        raise click.ClickException(
            f"Step '{step}' not in state store. "
            f"Available: {list(saved.keys())}"
        )

    if saved[step] != StepStatus.FAILED:
        raise click.ClickException(
            f"Step '{step}' is {saved[step].value}, not FAILED. "
            "Retry is only for failed steps."
        )

    # 清除失败状态
    state_store.clear_step(step)
    click.echo(f"Cleared state for '{step}'. Resuming execution...")

    # 构建并执行
    builder = WorkflowBuilder()
    builder.register_from_flow_path(
        context['flow_base_path'], context['flow_overlay_path']
    )
    workflow = builder.create_workflow(
        [graph_config], context['tool_selection']
    )

    from cmdkit import ScriptBuilder
    sb = ScriptBuilder(
        context['flow_base_path'],
        context['branch_path'],
        context['flow_overlay_path'],
    )
    click.echo(f"Shell mode: {sb.preferred_shell}")

    executor = Executor(
        workflow,
        sb,
        state_store=state_store,
        dry_run=dry_run,
        debug=debug,
        verbose=info_mode,
    )
    report = executor.run(resume=True)

    click.echo("")
    if report.success:
        click.echo(click.style("Retry completed successfully!", fg='green'))
    else:
        click.echo(click.style(
            f"Retry failed. Failed steps: {report.failed_steps}", fg='red'
        ))
    click.echo(f"Total time: {report.total_time:.1f}s")
