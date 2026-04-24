#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""edp.commands.flow_cmd - Flow tutor commands."""

from pathlib import Path
from typing import List

import click

from dirkit import ProjectFinder
from edp.context import _resolve_context

from .helpers import (
    collect_invoke_items,
    parse_sub_steps,
    print_existing_steps,
    prompt_select_or_input_tool,
    write_flow_scaffold,
)


@click.command("flowcreate")
@click.option("--tool", "tool_name", default=None, help="Tool name")
@click.option("--step", "step_name", default=None, help="Step name")
@click.option("--sub-steps", "sub_steps", default=None,
              help="Comma separated sub step names")
@click.option("--invoke", "invoke_cmd", default=None,
              help="Invoke command template")
@click.pass_context
def flow_create_alias(ctx, tool_name, step_name, sub_steps, invoke_cmd):
    """Create minimal flow scaffold (single entrypoint)."""
    _flow_create_impl(ctx, tool_name, step_name, sub_steps, invoke_cmd)


def _flow_create_impl(ctx, tool_name, step_name, sub_steps, invoke_cmd):
    """Interactive tutor: create minimal flow scaffold."""
    edp_center = ctx.obj["edp_center"]
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_or_prompt_context(ctx)
    flow_root = _pick_target_flow_root(context)

    click.echo("Flow Tutor (MVP): press Enter to accept defaults.")
    click.echo("Merge rule: overlay same step = override; new step = append.")
    if not tool_name:
        tool_name = prompt_select_or_input_tool(context, flow_root)
    print_existing_steps(context, flow_root, tool_name)
    step_name = step_name or click.prompt(
        "Step name (example: place)",
        type=str,
    ).strip()
    if not tool_name or not step_name:
        raise click.ClickException("Tool name and step name cannot be empty.")

    sub_steps_input = sub_steps or click.prompt(
        "Sub steps, comma separated (example: global_place,detail_place)",
        default=step_name,
        show_default=True,
    )
    parsed_sub_steps = parse_sub_steps(sub_steps_input)
    if not parsed_sub_steps:
        raise click.ClickException("At least one sub step is required.")

    invoke_items = collect_invoke_items(tool_name, step_name, invoke_cmd)

    created = write_flow_scaffold(
        flow_root=flow_root,
        tool_name=tool_name,
        step_name=step_name,
        sub_steps=parsed_sub_steps,
        invoke_items=invoke_items,
    )

    click.echo(click.style("Flow scaffold created.", fg="green"))
    click.echo(f"  Root: {flow_root}")
    click.echo(f"  Tool: {tool_name}")
    click.echo(f"  Step: {step_name}")
    click.echo("  Files:")
    for p in created:
        click.echo(f"    - {p}")
    click.echo("")
    click.echo("Next steps:")
    click.echo(f"  1) Review generated files under cmds/{tool_name}/")
    click.echo(f"  2) Add '{tool_name}.{step_name}' to step_config.yaml if needed")
    click.echo(f"  3) Run: edp run {step_name} --dry-run")


def _pick_target_flow_root(context: dict) -> Path:
    """Prefer overlay flow for authoring; fallback to base flow."""
    overlay = context["flow_overlay_path"]
    if overlay:
        return overlay
    return context["flow_base_path"]


def _resolve_or_prompt_context(ctx) -> dict:
    """Resolve context from cwd; fallback to interactive selection anywhere."""
    edp_center = ctx.obj["edp_center"]
    try:
        return _resolve_context(ctx)
    except Exception as exc:
        click.echo(f"[flowcreate] Context auto-detect failed ({exc}); "
                   "switching to interactive project selection.", err=True)

    init_path = Path(edp_center) / "flow" / "initialize"
    finder = ProjectFinder(init_path)
    projects = finder.list_projects()
    if not projects:
        raise click.ClickException(
            f"No projects found under: {init_path}\n"
            "Please check EDP_CENTER and initialize resources."
        )

    foundries = sorted({p["foundry"] for p in projects})
    click.echo("Cannot detect branch context from cwd; switch to interactive project selection.")
    foundry = _prompt_select_or_new("foundry", foundries)

    nodes = sorted({p["node"] for p in projects if p["foundry"] == foundry})
    node = _prompt_select_or_new("node", nodes)

    project_names = sorted({
        p["project"] for p in projects if p["foundry"] == foundry and p["node"] == node
    })
    project_name = _prompt_select_or_new("project", project_names)

    flow_base = init_path / foundry / node / "common_prj"
    flow_overlay = init_path / foundry / node / project_name
    return {
        "flow_base_path": flow_base,
        "flow_overlay_path": flow_overlay,
        "project_info": {
            "foundry": foundry,
            "node": node,
            "project_name": project_name,
        },
    }


def _prompt_select_or_new(label: str, options: List[str]) -> str:
    """Prompt with numbered options; allow creating new value after confirmation."""
    while True:
        click.echo(f"Available {label}s:")
        if options:
            for idx, item in enumerate(options, 1):
                click.echo(f"  [{idx}] {item}")
        else:
            click.echo("  (none)")

        raw = click.prompt(
            f"Select {label} (number or new_{label}_name)",
            type=str,
        ).strip()

        if not raw:
            click.echo(f"{label} cannot be empty.")
            continue

        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1]
            click.echo(f"Invalid selection index: {index}")
            continue

        existing_exact = next((item for item in options if item.lower() == raw.lower()), None)
        if existing_exact:
            click.echo(
                f"'{raw}' is an existing {label}. "
                f"Please use its index number [{options.index(existing_exact) + 1}] to avoid ambiguity."
            )
            continue

        if click.confirm(
            f"'{raw}' is not in existing {label} list. Create new {label}?",
            default=False,
            show_default=True,
        ):
            return raw
