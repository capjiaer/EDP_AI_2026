#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.tutor - Interactive learning aids for EDP concepts
"""

from pathlib import Path
from typing import List

import click

from edp.context import _resolve_context, _load_graph_config_choice
from flowkit.loader.dependency_loader import DependencyLoader
from flowkit.loader.step_loader import StepRegistry


@click.group("tutor")
def tutor():
    """Show guided learning content for EDP usage and models."""


@tutor.command("quickstart")
def tutor_quickstart():
    """Print a 5-minute practical quickstart."""
    click.echo("EDP Tutor - Quickstart (5 mins)")
    click.echo("")
    click.echo("1) Load environment")
    click.echo("   source edp.sh   # or source edp.csh")
    click.echo("")
    click.echo("2) Initialize project workspace")
    click.echo("   edp init -prj dongting -ver P85")
    click.echo("   edp init -blk top")
    click.echo("")
    click.echo("3) Create a new flow skeleton")
    click.echo("   edp flowcreate")
    click.echo("")
    click.echo("4) Validate before execution")
    click.echo("   edp doctor")
    click.echo("   edp run <step> --dry-run")
    click.echo("")
    click.echo("5) Execute")
    click.echo("   edp run <step>")
    click.echo("")
    click.echo("Tip: use 'edp tutor model' to understand config/step/graph boundaries.")


@tutor.command("model")
def tutor_model():
    """Explain core EDP data model boundaries."""
    click.echo("EDP Tutor - Model Boundaries")
    click.echo("")
    click.echo("1) step.yaml (supply layer)")
    click.echo("   - Defines what a tool CAN provide: supported_steps / invoke / sub_steps")
    click.echo("")
    click.echo("2) step_config.yaml (activation layer)")
    click.echo("   - Defines what the current flow WILL run: steps list")
    click.echo("")
    click.echo("3) graph_config*.yaml (dependency layer)")
    click.echo("   - Defines execution order and dependencies among activated steps")
    click.echo("")
    click.echo("4) config.yaml + user_config.yaml (parameter layer)")
    click.echo("   - Provides variables and runtime knobs")
    click.echo("   - LSF scheduling is controlled in config lsf blocks, not invoke")
    click.echo("")
    click.echo("Rule of thumb:")
    click.echo("  step.yaml is capability; step_config is policy; graph_config is topology;")
    click.echo("  config is parameterization.")


@tutor.command("diagnose")
@click.pass_context
def tutor_diagnose(ctx):
    """Run lightweight checks for common flow modeling mistakes."""
    edp_center = ctx.obj.get("edp_center")
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_context(ctx)
    flow_base = context["flow_base_path"]
    flow_overlay = context["flow_overlay_path"]
    tool_selection = context["tool_selection"]

    registry = StepRegistry()
    registry.load_with_override(flow_base, flow_overlay)

    issues: List[str] = []
    notes: List[str] = []

    # Check A: activated steps must be supported by selected tool.
    for step, tool in sorted(tool_selection.items()):
        if not registry.has_step(tool, step):
            issues.append(
                f"step_config activates '{tool}.{step}', but step.yaml does not provide it."
            )

    # Check B: find provided but currently inactive steps.
    provided = []
    for tool, steps in registry.get_all_steps().items():
        for step in steps.keys():
            provided.append((tool, step))
    inactive = sorted([f"{t}.{s}" for (t, s) in provided if tool_selection.get(s) != t])
    if inactive:
        notes.append(
            f"{len(inactive)} provided steps are currently inactive in step_config (expected in many cases)."
        )

    # Check C: graph alignment (pick saved graph; fallback first graph file).
    graph_files = context.get("graph_configs", [])
    chosen = None
    if graph_files:
        chosen = _load_graph_config_choice(context["branch_path"], graph_files) or graph_files[0]
        graph = DependencyLoader().load_from_multiple_files([chosen])
        graph_steps = set(graph.steps.keys())
        activated_steps = set(tool_selection.keys())

        missing_in_graph = sorted(list(activated_steps - graph_steps))
        missing_in_step_config = sorted(list(graph_steps - activated_steps))
        if missing_in_graph:
            issues.append(
                f"{len(missing_in_graph)} activated step(s) not found in {chosen.name}: "
                + ", ".join(missing_in_graph[:8])
            )
        if missing_in_step_config:
            notes.append(
                f"{len(missing_in_step_config)} graph step(s) are not activated by step_config."
            )

    # Check D: invoke should not include bsub directly.
    for tool, steps in registry.get_all_steps().items():
        for step, data in steps.items():
            invoke = data.get("invoke", []) if isinstance(data, dict) else []
            text = " ".join([str(x) for x in invoke])
            if "bsub " in text or text.startswith("bsub"):
                issues.append(
                    f"invoke of {tool}.{step} contains bsub; keep scheduling in config.yaml lsf blocks."
                )

    click.echo("EDP Tutor - Diagnose")
    click.echo("")
    click.echo(f"Flow base: {flow_base}")
    click.echo(f"Flow overlay: {flow_overlay}")
    if chosen:
        click.echo(f"Graph checked: {Path(chosen).name}")
    click.echo("")

    if issues:
        for msg in issues:
            click.echo(click.style(f"[WARN] {msg}", fg="yellow"))
    else:
        click.echo(click.style("[OK] No blocking modeling mismatch found.", fg="green"))

    for msg in notes:
        click.echo(click.style(f"[NOTE] {msg}", fg="cyan"))

