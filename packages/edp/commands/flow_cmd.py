#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.flow_cmd - Flow tutor commands
"""

from pathlib import Path
from typing import Dict, List

import click
import yaml

from edp.context import _resolve_context
from dirkit import ProjectFinder


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
        tool_name = _prompt_select_or_input_tool(context, flow_root)
    _print_existing_steps(context, flow_root, tool_name)
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

    invoke_items = _collect_invoke_items(tool_name, step_name, invoke_cmd)

    created = _write_flow_scaffold(
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
    except Exception:
        pass

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


def _parse_sub_steps(raw: str) -> List[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _prompt_select_or_input_tool(context: dict, flow_root: Path) -> str:
    """Prompt tool by index or direct input name."""
    options = _collect_tool_candidates(context, flow_root)
    click.echo("Available tools:")
    if options:
        for idx, item in enumerate(options, 1):
            click.echo(f"  [{idx}] {item}")
    else:
        click.echo("  (none)")

    raw = click.prompt(
        "Select tool (number or new_tool_name)",
        type=str,
    ).strip()
    if not raw:
        raise click.ClickException("Tool name cannot be empty.")
    if raw.isdigit():
        index = int(raw)
        if 1 <= index <= len(options):
            return options[index - 1]
        raise click.ClickException(f"Invalid tool selection index: {index}")
    return raw


def _collect_tool_candidates(context: dict, flow_root: Path) -> List[str]:
    """Collect existing tool names from flow cmds dirs + step_config."""
    tools = set()
    cmds_dir = flow_root / "cmds"
    if cmds_dir.exists():
        for p in cmds_dir.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                tools.add(p.name)

    tool_selection = context.get("tool_selection") or {}
    if not tool_selection:
        tool_selection = _load_tool_selection(
            context.get("flow_base_path"),
            context.get("flow_overlay_path"),
        )
    tools.update(tool_selection.values())
    return sorted(tools)


def _collect_invoke_items(tool_name: str, step_name: str, invoke_cmd: str = None) -> List[str]:
    """Collect invoke segments with live preview."""
    if invoke_cmd:
        items = [invoke_cmd.strip()]
        _print_invoke_preview(items)
        return items

    click.echo("")
    click.echo("Invoke builder:")
    click.echo("  - Enter one segment per line (in order).")
    click.echo("  - Press Enter on empty line to finish.")
    click.echo("  - LSF settings are configured in config.yaml (lsf block), not here.")

    items: List[str] = []
    default_first = _suggest_invoke_default(tool_name, step_name)
    while True:
        prompt = "Invoke segment"
        if not items:
            raw = click.prompt(prompt, default=default_first, show_default=True).strip()
        else:
            raw = click.prompt(prompt, default="", show_default=False).strip()
            if not raw:
                break
        items.append(raw)
        _print_invoke_preview(items)

    if not items:
        raise click.ClickException("At least one invoke segment is required.")
    return items


def _suggest_invoke_default(tool_name: str, step_name: str) -> str:
    """Suggest a practical first invoke segment based on tool/step."""
    t = (tool_name or "").strip().lower()
    s = (step_name or "").strip().lower()

    if t == "pv_calibre":
        if s == "drc":
            return "calibre -drc -hier -turbo {cpu_num}"
        if s == "lvs":
            return "calibre -lvs -hier -turbo {cpu_num}"
        if s == "perc":
            return "calibre -perc -hier -turbo {cpu_num}"
        if s == "ipmerge":
            return "calibre -ipmerge"
        if s == "dummy":
            return "calibre -dummy"
        return "calibre -drc -hier -turbo {cpu_num}"

    if t == "pnr_innovus":
        return "innovus -init $edp(script)"

    if t == "sta_pt":
        return "sta_pt -init $edp(script)"

    return f"{tool_name} -init $edp(script)"


def _print_invoke_preview(items: List[str]) -> None:
    click.echo(f"  Current invoke ({len(items)} segment(s)):")
    for idx, item in enumerate(items, 1):
        click.echo(f"    [{idx}] {item}")
    click.echo(f"  Joined command: {' '.join(items)}")
    click.echo("")


def _print_existing_steps(context: dict, flow_root: Path, tool_name: str) -> None:
    """Show provided/activated steps for the selected tool."""
    supported = _load_supported_steps(flow_root, tool_name)
    activated = _load_activated_steps(context, tool_name)

    click.echo("")
    click.echo(f"Tool '{tool_name}' visibility:")
    click.echo(
        f"  provided steps ({len(supported)}): "
        f"{', '.join(supported) if supported else '(none)'}"
    )
    click.echo(
        f"  activated steps ({len(activated)}): "
        f"{', '.join(activated) if activated else '(none)'}"
    )
    click.echo("")


def _load_supported_steps(flow_root: Path, tool_name: str) -> List[str]:
    step_yaml = flow_root / "cmds" / tool_name / "step.yaml"
    if not step_yaml.exists():
        return []
    data = yaml.safe_load(step_yaml.read_text(encoding="utf-8")) or {}
    tool_block = data.get(tool_name, {})
    supported = tool_block.get("supported_steps", {}) if isinstance(tool_block, dict) else {}
    if not isinstance(supported, dict):
        return []
    return sorted(supported.keys())


def _load_activated_steps(context: dict, tool_name: str) -> List[str]:
    tool_selection = context.get("tool_selection") or {}
    if not tool_selection:
        tool_selection = _load_tool_selection(
            context.get("flow_base_path"),
            context.get("flow_overlay_path"),
        )
    return sorted([step for step, tool in tool_selection.items() if tool == tool_name])


def _load_tool_selection(flow_base: Path, flow_overlay: Path) -> Dict[str, str]:
    config_path = None
    if flow_overlay and flow_overlay.exists():
        p = flow_overlay / "step_config.yaml"
        if p.exists():
            config_path = p
    if not config_path and flow_base and flow_base.exists():
        p = flow_base / "step_config.yaml"
        if p.exists():
            config_path = p
    if not config_path:
        return {}

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    result = {}
    for entry in data.get("steps", []):
        text = str(entry)
        if "." in text:
            tool, step = text.rsplit(".", 1)
            result[step] = tool
    return result


def _write_flow_scaffold(flow_root: Path, tool_name: str, step_name: str,
                         sub_steps: List[str], invoke_items: List[str]) -> List[Path]:
    created: List[Path] = []
    cmds_dir = flow_root / "cmds" / tool_name
    steps_dir = cmds_dir / "steps" / step_name

    cmds_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)

    step_yaml = cmds_dir / "step.yaml"
    _update_step_yaml(step_yaml, tool_name, step_name, sub_steps, invoke_items)
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

    return created


def _update_step_yaml(step_yaml: Path, tool_name: str, step_name: str,
                      sub_steps: List[str], invoke_items: List[str]) -> None:
    data = {}
    existed = step_yaml.exists()
    if existed:
        data = yaml.safe_load(step_yaml.read_text(encoding="utf-8")) or {}
    tool_block = data.setdefault(tool_name, {})
    supported = tool_block.setdefault("supported_steps", {})
    if step_name in supported:
        raise click.ClickException(
            f"Step '{step_name}' already exists in {step_yaml}. "
            "Please edit it manually if you need to change it."
        )

    supported[step_name] = {
        "invoke": invoke_items,
        "sub_steps": sub_steps,
    }
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    if existed:
        step_yaml.write_text(body, encoding="utf-8")
        return

    step_yaml.write_text(_invoke_tutor_header(tool_name) + "\n" + body, encoding="utf-8")


def _invoke_tutor_header(tool_name: str) -> str:
    return "\n".join([
        "# invoke tutor (quick):",
        "# - invoke is a list of command segments; EDP joins them with spaces.",
        "# - $edp(var): framework vars (e.g. $edp(script), $edp(step), $edp(tool)).",
        "# - {var}: optional config var; missing value drops the whole segment.",
        "# - $var: required config var; always substituted (empty if missing).",
        "# - Variable scope precedence: tool(step,var) > tool(var).",
        "# - Config file override order: base config < overlay config < user_config.",
        "#   (user_config can override both tool(var) and tool(step,var))",
        "# Example:",
        "#   invoke:",
        f"#     - \"{tool_name} -init $edp(script)\"",
        "#     - \"-threads {cpu_num}\"",
        "#     - \"{nowin}\"",
        "#     - \"-design $design_name\"",
        "#     - \"{tee} $edp(step).log\"",
        "#   Expanded command shape (when vars exist):",
        f"#     {tool_name} -init <abs_script.tcl> -threads 8 -nowin -design top |& tee <step>.log",
        "",
    ])


def _step_template(sub_step: str) -> str:
    return "\n".join([
        f"proc {sub_step} {{}} {{",
        f"    puts \"[{sub_step}] TODO: implement\"",
        "}",
        "",
    ])


