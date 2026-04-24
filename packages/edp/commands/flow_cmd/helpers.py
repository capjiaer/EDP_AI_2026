#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Helper functions for the flowcreate command."""

from pathlib import Path
from typing import Dict, List

import click
import yaml


def parse_sub_steps(raw: str) -> List[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def prompt_select_or_input_tool(context: dict, flow_root: Path) -> str:
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


def collect_invoke_items(tool_name: str, step_name: str, invoke_cmd: str = None) -> List[str]:
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


def print_existing_steps(context: dict, flow_root: Path, tool_name: str) -> None:
    """Show provided/activated steps for the selected tool."""
    supported = _load_supported_steps(context, flow_root, tool_name)
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


def write_flow_scaffold(flow_root: Path, tool_name: str, step_name: str,
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
            sub_file.write_text(_step_template(sub), encoding="utf-8")
            created.append(sub_file)

    return created


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
        return "pt_shell -file $edp(script)"

    return f"{tool_name} -init $edp(script)"


def _print_invoke_preview(items: List[str]) -> None:
    click.echo(f"  Current invoke ({len(items)} segment(s)):")
    for idx, item in enumerate(items, 1):
        click.echo(f"    [{idx}] {item}")
    click.echo(f"  Joined command: {' '.join(items)}")
    click.echo("")


def _load_supported_steps(context: dict, flow_root: Path, tool_name: str) -> List[str]:
    """Load provided steps from overlay/base with overlay taking priority."""
    candidates: List[Path] = []
    seen = set()

    for root in [flow_root, context.get("flow_overlay_path"), context.get("flow_base_path")]:
        if not root:
            continue
        root = Path(root)
        step_yaml = root / "cmds" / tool_name / "step.yaml"
        if step_yaml in seen:
            continue
        seen.add(step_yaml)
        candidates.append(step_yaml)

    merged = {}
    for step_yaml in reversed(candidates):
        if not step_yaml.exists():
            continue
        data = yaml.safe_load(step_yaml.read_text(encoding="utf-8")) or {}
        tool_block = data.get(tool_name, {})
        supported = tool_block.get("supported_steps", {}) if isinstance(tool_block, dict) else {}
        if isinstance(supported, dict):
            merged.update(supported)
    return sorted(merged.keys())


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
