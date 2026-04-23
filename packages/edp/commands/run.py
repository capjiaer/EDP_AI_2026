#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.run - Execute workflow

三种模式：
  edp run drc                        单步执行
  edp run -fr postroute -to drc      子图执行
  edp run                            全图执行

通用选项：--dry-run / --force / -skip
"""

import click

from flowkit import (
    Executor,
    StateStore,
    WorkflowBuilder,
)
from flowkit.core.graph import Graph
from flowkit.loader.dependency_loader import DependencyLoader
from flowkit.loader.workflow_builder import ExecutableWorkflow
from edp.context import _resolve_context, _pick_graph_config


def _resolve_step_spec(spec: str, tool_selection: dict) -> tuple:
    """解析 step 规格

    'pv_calibre.drc' → ('pv_calibre', 'drc')
    'drc'            → (tool_selection['drc'], 'drc')
    """
    if '.' in spec:
        tool, step = spec.rsplit('.', 1)
        return tool, step
    if spec in tool_selection:
        return tool_selection[spec], spec
    raise click.ClickException(
        f"Step '{spec}' not found in step_config.yaml. "
        f"Use format: <tool>.<step> (e.g., pv_calibre.drc)"
    )


def _resolve_graph_step(spec: str, graph: Graph) -> str:
    """验证 step 在图中存在"""
    if spec in graph.steps:
        return spec
    raise click.ClickException(
        f"Step '{spec}' not found in graph. "
        f"Available: {sorted(graph.steps.keys())}"
    )


def _build_subgraph_from_set(graph: Graph, step_ids: set) -> Graph:
    """从 step 集合构建子图"""
    sub = Graph()
    for sid in step_ids:
        sub.add_step(graph.steps[sid])
    for dep in graph.dependencies:
        if dep.from_step in step_ids and dep.to_step in step_ids:
            sub.add_dependency(dep.from_step, dep.to_step, dep.weak)
    return sub


def _create_sub_workflow(workflow: ExecutableWorkflow,
                          sub_graph: Graph) -> ExecutableWorkflow:
    """从子图创建 ExecutableWorkflow"""
    steps = {sid: workflow.steps[sid]
             for sid in sub_graph.steps if sid in workflow.steps}
    tool_sel = {sid: workflow.tool_selection[sid]
                for sid in sub_graph.steps if sid in workflow.tool_selection}
    return ExecutableWorkflow(graph=sub_graph, steps=steps,
                               tool_selection=tool_sel)


def _print_plan(workflow, dry_run: bool = False) -> None:
    """打印执行计划"""
    prefix = "[DRY-RUN] " if dry_run else ""
    plan = workflow.get_execution_plan()
    click.echo(f"{prefix}Execution plan: {len(plan)} levels, "
               f"{len(workflow.steps)} steps")
    for i, level in enumerate(plan):
        tools = []
        for sid in level:
            tool = workflow.get_step_tool(sid) if hasattr(workflow, 'get_step_tool') else ''
            tools.append(f"{sid}" + (f"({tool})" if tool else ""))
        click.echo(f"{prefix}  Level {i}: {', '.join(tools)}")


def _print_report(report) -> None:
    """打印执行报告"""
    click.echo("")
    if report.success:
        click.echo(click.style("All steps completed successfully!", fg='green'))
    else:
        click.echo(click.style(
            f"Execution failed. Failed steps: {report.failed_steps}", fg='red'
        ))
    if report.skipped_steps:
        click.echo(f"Skipped steps: {report.skipped_steps}")
    click.echo(f"Total time: {report.total_time:.1f}s")


@click.command()
@click.argument('step', required=False, default=None)
@click.option('-fr', '--from', 'from_step', default=None,
              help='Sub-graph start step')
@click.option('-to', '--to', 'to_step', default=None,
              help='Sub-graph end step')
@click.option('-skip', '--skip', 'skip_steps', multiple=True,
              help='Steps to skip (treat as finished)')
@click.option('-dr', '--dry-run', is_flag=True, default=False,
              help='Preview mode, no actual execution')
@click.option('--force', is_flag=True, default=False,
              help='Force rerun, ignore existing state')
@click.option('-debug', '--debug', is_flag=True, default=False,
              help='Run in debug mode (execute *_debug.sh / LSF -Ip)')
@click.option('-info', '--info', 'info_mode', is_flag=True, default=False,
              help='Show full error details on step failure')
@click.pass_context
def run(ctx, step, from_step, to_step, skip_steps, dry_run, force, debug, info_mode):
    """Execute workflow."""
    edp_center = ctx.obj['edp_center']
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_context(ctx)
    graph_config = _pick_graph_config(context['graph_configs'],
                                       context['branch_path'])

    # 公共组件
    from cmdkit import ScriptBuilder
    sb = ScriptBuilder(
        context['flow_base_path'],
        context['branch_path'],
        context['flow_overlay_path'],
    )
    click.echo(f"Shell mode: {sb.preferred_shell}")
    state_file = context['branch_path'] / 'state.yaml'
    state_store = StateStore(state_file)

    # --- 模式 1：单步执行 ---
    if step and not from_step and not to_step:
        tool_name, step_name = _resolve_step_spec(step,
                                                    context['tool_selection'])

        executor = Executor(
            workflow=None,
            script_builder=sb,
            state_store=state_store,
            dry_run=dry_run,
            force=force,
            debug=debug,
            verbose=info_mode,
        )
        report = executor.run_single(tool_name, step_name)
        _print_report(report)
        return

    # --- 模式 2：子图执行 ---
    if from_step or to_step:
        builder = WorkflowBuilder()
        builder.register_from_flow_path(
            context['flow_base_path'], context['flow_overlay_path']
        )
        workflow = builder.create_workflow(
            [graph_config], context['tool_selection']
        )
        graph = workflow.graph

        # 提取子图
        if from_step and to_step:
            fr = _resolve_graph_step(from_step, graph)
            to = _resolve_graph_step(to_step, graph)
            sub_graph = graph.extract_subgraph(fr, to)
        elif from_step:
            fr = _resolve_graph_step(from_step, graph)
            step_ids = graph.get_downstream_steps(fr)
            sub_graph = _build_subgraph_from_set(graph, step_ids)
        else:  # only to_step
            to = _resolve_graph_step(to_step, graph)
            step_ids = graph.get_upstream_steps(to)
            step_ids.add(to)
            sub_graph = _build_subgraph_from_set(graph, step_ids)

        sub_workflow = _create_sub_workflow(workflow, sub_graph)

        click.echo(f"Sub-graph: {len(sub_graph.steps)} steps "
                   f"({from_step or 'start'} -> {to_step or 'end'})")
        _print_plan(sub_workflow, dry_run)
        if dry_run:
            return

        do_resume = state_store.exists() and not force
        state_store.save_graph_config(graph_config.name)

        executor = Executor(
            workflow=sub_workflow,
            script_builder=sb,
            state_store=state_store,
            dry_run=dry_run,
            skip_steps=list(skip_steps),
            force=force,
            debug=debug,
            verbose=info_mode,
        )
        report = executor.run(resume=do_resume)
        _print_report(report)
        return

    # --- 模式 3：全图执行（默认） ---
    builder = WorkflowBuilder()
    builder.register_from_flow_path(
        context['flow_base_path'], context['flow_overlay_path']
    )
    workflow = builder.create_workflow(
        [graph_config], context['tool_selection']
    )

    # Ready 检查
    loader = DependencyLoader()
    graph = loader.load_from_multiple_files([graph_config])
    readiness = builder.check_step_readiness(graph, context['tool_selection'])
    ready_steps = [s for s, r in readiness.items() if r['ready']]
    not_ready_steps = [s for s, r in readiness.items() if not r['ready']]

    click.echo(f"Workflow: {len(graph.steps)} steps ({len(ready_steps)} ready, "
               f"{len(not_ready_steps)} not ready)")
    if not_ready_steps:
        click.echo("")
        click.echo("Not ready:")
        for s in not_ready_steps:
            info = readiness[s]
            if info['tool']:
                click.echo(f"  {s:<16} -> {info['tool']} (no .tcl found)")
            else:
                click.echo(f"  {s:<16} -> not configured in step_config.yaml")
        click.echo("")

    _print_plan(workflow, dry_run)
    if dry_run:
        return

    do_resume = state_store.exists() and not force
    if do_resume:
        saved_graph = state_store.load_graph_config()
        if saved_graph and saved_graph != graph_config.name:
            click.echo(click.style(
                f"Warning: state was created with {saved_graph}, "
                f"but current graph is {graph_config.name}.", fg='yellow'
            ))
            if not click.confirm(
                    "Resume with different graph? State will be cleared"):
                raise click.ClickException(
                    "Aborted. Switch graph with 'edp graph' first.")
            state_store.clear()
            do_resume = False
        else:
            click.echo("Resuming from checkpoint...")

    state_store.save_graph_config(graph_config.name)

    executor = Executor(
        workflow=workflow,
        script_builder=sb,
        state_store=state_store,
        dry_run=dry_run,
        skip_steps=list(skip_steps),
        force=force,
        debug=debug,
        verbose=info_mode,
    )
    report = executor.run(resume=do_resume)
    _print_report(report)
