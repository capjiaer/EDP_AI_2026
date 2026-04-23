#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.flow_cmd - Flow tutor commands
"""

from pathlib import Path
from typing import List

import click
import yaml

from edp.context import _resolve_context


@click.group("flow")
def flow_cmd():
    """Flow authoring helpers (overlay step overrides, new steps append)."""


@flow_cmd.command("create")
@click.option("--tool", "tool_name", default=None, help="Tool name")
@click.option("--step", "step_name", default=None, help="Step name")
@click.option("--sub-steps", "sub_steps", default=None,
              help="Comma separated sub step names")
@click.option("--invoke", "invoke_cmd", default=None,
              help="Invoke command template")
@click.option("--with-hooks/--no-hooks", default=None,
              help="Create hook templates (default: yes)")
@click.pass_context
def flow_create(ctx, tool_name, step_name, sub_steps, invoke_cmd, with_hooks):
    """Interactive tutor: create minimal flow scaffold."""
    edp_center = ctx.obj["edp_center"]
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_context(ctx)
    flow_root = _pick_target_flow_root(context)

    click.echo("Flow Tutor (MVP): press Enter to accept defaults.")
    click.echo("Merge rule: overlay same step = override; new step = append.")
    tool_name = tool_name or click.prompt(
        "Tool name (example: pnr_innovus)",
        type=str,
    ).strip()
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
    parsed_sub_steps = _parse_sub_steps(sub_steps_input)
    if not parsed_sub_steps:
        raise click.ClickException("At least one sub step is required.")

    invoke_default = f"{tool_name} -init $edp(script)"
    invoke_cmd = invoke_cmd or click.prompt(
        "Invoke command template (example: innovus -init $edp(script))",
        default=invoke_default,
        show_default=True,
    )
    if with_hooks is None:
        with_hooks = click.confirm(
            "Create hook templates? (example: step.pre/global_place.pre)",
            default=True,
            show_default=True,
        )

    created = _write_flow_scaffold(
        flow_root=flow_root,
        tool_name=tool_name,
        step_name=step_name,
        sub_steps=parsed_sub_steps,
        invoke_cmd=invoke_cmd,
        with_hooks=with_hooks,
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
    click.echo(f"  1) Review generated files under cmds/{tool_name}/ and hooks/{tool_name}/{step_name}/")
    click.echo(f"  2) Add '{tool_name}.{step_name}' to step_config.yaml if needed")
    click.echo(f"  3) Run: edp run {step_name} --dry-run")


def _pick_target_flow_root(context: dict) -> Path:
    """Prefer overlay flow for authoring; fallback to base flow."""
    overlay = context["flow_overlay_path"]
    if overlay and overlay.exists():
        return overlay
    return context["flow_base_path"]


def _parse_sub_steps(raw: str) -> List[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _write_flow_scaffold(flow_root: Path, tool_name: str, step_name: str,
                         sub_steps: List[str], invoke_cmd: str,
                         with_hooks: bool) -> List[Path]:
    created: List[Path] = []
    cmds_dir = flow_root / "cmds" / tool_name
    steps_dir = cmds_dir / "steps" / step_name
    hooks_dir = flow_root / "hooks" / tool_name / step_name

    cmds_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)

    step_yaml = cmds_dir / "step.yaml"
    _update_step_yaml(step_yaml, tool_name, step_name, sub_steps, invoke_cmd)
    created.append(step_yaml)

    config_yaml = cmds_dir / "config.yaml"
    if not config_yaml.exists():
        config_yaml.write_text(
            yaml.safe_dump(
                {
                    tool_name: {
                        "lsf": {"lsf_mode": 0, "cpu_num": 1, "queue": "normal"}
                    }
                },
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        created.append(config_yaml)

    for sub in sub_steps:
        sub_file = steps_dir / f"{sub}.tcl"
        if not sub_file.exists():
            sub_file.write_text(
                _step_template(sub),
                encoding="utf-8",
            )
            created.append(sub_file)

    if with_hooks:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        globals_str = f"global edp {tool_name}"
        hook_specs = [
            ("step.pre", f"{step_name}_step_pre", f"Step-level pre hook for {tool_name}.{step_name}"),
            ("step.post", f"{step_name}_step_post", f"Step-level post hook for {tool_name}.{step_name}"),
        ]
        for sub in sub_steps:
            hook_specs.extend([
                (f"{sub}.pre", f"{step_name}_{sub}_pre", f"Pre hook for sub_step '{sub}'"),
                (f"{sub}.post", f"{step_name}_{sub}_post", f"Post hook for sub_step '{sub}'"),
                (f"{sub}.replace", f"{step_name}_{sub}_replace", f"Replace hook for sub_step '{sub}'"),
            ])
        for name, proc_name, desc in hook_specs:
            hp = hooks_dir / name
            if not hp.exists():
                hp.write_text(_hook_template(desc, proc_name, globals_str), encoding="utf-8")
                created.append(hp)

    return created


def _update_step_yaml(step_yaml: Path, tool_name: str, step_name: str,
                      sub_steps: List[str], invoke_cmd: str) -> None:
    data = {}
    if step_yaml.exists():
        data = yaml.safe_load(step_yaml.read_text(encoding="utf-8")) or {}
    tool_block = data.setdefault(tool_name, {})
    supported = tool_block.setdefault("supported_steps", {})
    if step_name in supported:
        raise click.ClickException(
            f"Step '{step_name}' already exists in {step_yaml}. "
            "Please edit it manually if you need to change it."
        )

    supported[step_name] = {
        "invoke": [invoke_cmd],
        "sub_steps": sub_steps,
    }
    step_yaml.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _step_template(sub_step: str) -> str:
    return "\n".join([
        f"proc {sub_step} {{}} {{",
        f"    puts \"[{sub_step}] TODO: implement\"",
        "}",
        "",
    ])


def _hook_template(description: str, proc_name: str, globals_str: str) -> str:
    lines = [
        f"# {description}",
        "# Fill in your code inside the proc body, or delete this file if not needed.",
        "",
        f"proc {proc_name} {{}} {{",
    ]
    if globals_str:
        lines.append(f"    {globals_str}")
    lines.extend([
        "",
        "    # Your code here",
        "}",
        "",
    ])
    return "\n".join(lines)
