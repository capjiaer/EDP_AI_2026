#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.doctor - Environment and workspace diagnostics
"""

import importlib
import json
import os
import shutil
from pathlib import Path

import click
import yaml

from flowkit import StateStore
from edp.context import _resolve_context, _find_graph_configs, _load_graph_config_choice


def _record(results, level: str, check: str, message: str) -> None:
    results.append({
        "level": level,
        "check": check,
        "message": message,
    })


def _emit_human(results) -> None:
    for item in results:
        level = item["level"]
        message = item["message"]
        if level == "OK":
            click.echo(click.style(f"[OK]   {message}", fg="green"))
        elif level == "WARN":
            click.echo(click.style(f"[WARN] {message}", fg="yellow"))
        else:
            click.echo(click.style(f"[ERR]  {message}", fg="red"))


@click.command("doctor")
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as failures (exit non-zero).",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    default=False,
    help="Output machine-readable JSON report.",
)
@click.pass_context
def doctor(ctx, strict, json_mode):
    """Check environment, context and graph/state consistency."""
    results = []

    # ── Python 依赖 ──
    for pkg in ["yaml", "configkit", "flowkit", "cmdkit", "dirkit"]:
        try:
            importlib.import_module(pkg)
            _record(results, "OK", f"pkg_{pkg}", f"Python package '{pkg}' importable")
        except ImportError:
            _record(results, "ERR", f"pkg_{pkg}", f"Python package '{pkg}' not found")

    # ── Tcl 运行时 ──
    try:
        from tkinter import Tcl as _Tcl
        _Tcl()
        _record(results, "OK", "tcl_runtime", "Tcl runtime available (tkinter.Tcl)")
    except Exception as exc:
        _record(
            results, "ERR", "tcl_runtime",
            f"Tcl runtime not available: {exc}. "
            "Install tkinter (e.g. python3-tk) — configkit requires it.",
        )

    # ── edp_center ──
    edp_center = ctx.obj.get("edp_center")
    if not edp_center:
        _record(
            results,
            "ERR",
            "edp_center",
            "edp_center is not set. Use --edp-center or set EDP_CENTER.",
        )
        return _finish(results, strict, json_mode)

    edp_center = Path(edp_center).resolve()
    if not edp_center.exists():
        _record(
            results,
            "ERR",
            "edp_center",
            f"edp_center path does not exist: {edp_center}",
        )
    else:
        _record(results, "OK", "edp_center", f"edp_center: {edp_center}")

    init_path = edp_center / "flow" / "initialize"
    if not init_path.exists():
        _record(results, "ERR", "initialize_path", f"Missing initialize path: {init_path}")
    else:
        _record(results, "OK", "initialize_path", f"initialize path: {init_path}")

    legacy_common_packages = edp_center / "common_packages"
    if legacy_common_packages.exists():
        _record(
            results,
            "ERR",
            "legacy_common_packages",
            (
                f"Legacy directory is not allowed: {legacy_common_packages}. "
                "Use flow/common_packages only."
            ),
        )
    else:
        _record(results, "OK", "legacy_common_packages", "legacy common_packages directory not found")

    # ── flow/common_packages 结构 ──
    common_packages = edp_center / "flow" / "common_packages"
    if not common_packages.exists():
        _record(
            results, "ERR", "common_packages",
            f"Missing flow/common_packages: {common_packages}. "
            "Script generation and debug mode will fail.",
        )
    else:
        _record(results, "OK", "common_packages", f"flow/common_packages: {common_packages}")
        edp_debug_tcl = common_packages / "tcl_packages" / "default" / "edp_debug.tcl"
        if edp_debug_tcl.exists():
            _record(results, "OK", "edp_debug_tcl", "edp_debug.tcl found")
        else:
            _record(
                results, "WARN", "edp_debug_tcl",
                f"edp_debug.tcl not found at {edp_debug_tcl}. "
                "Debug mode (edp debug) will be unavailable.",
            )

    shell_hint = os.environ.get("SHELL", "")
    if shell_hint:
        _record(results, "OK", "shell_env", f"SHELL={shell_hint}")
    else:
        _record(
            results,
            "WARN",
            "shell_env",
            "SHELL env var is not set; shell detection will fallback to bash.",
        )

    has_bash = shutil.which("bash") is not None
    has_csh = shutil.which("csh") is not None
    if has_bash:
        _record(results, "OK", "launcher_bash", "bash launcher is available")
    else:
        _record(results, "WARN", "launcher_bash", "bash launcher not found in PATH")
    if has_csh:
        _record(results, "OK", "launcher_csh", "csh launcher is available")
    else:
        _record(results, "WARN", "launcher_csh", "csh launcher not found in PATH (csh mode may fail)")

    # Project context checks
    context = None
    try:
        context = _resolve_context(ctx)
        _record(
            results,
            "OK",
            "project_context",
            f"project context detected at: {context['branch_path']}",
        )
    except click.ClickException as e:
        _record(results, "WARN", "project_context", str(e))

    if context:
        flow_base = context["flow_base_path"]
        flow_overlay = context["flow_overlay_path"]
        graph_configs = _find_graph_configs(flow_base, flow_overlay)
        selected_graph = None

        if not graph_configs:
            _record(
                results,
                "ERR",
                "graph_config",
                "No graph_config*.yaml found in detected flow paths",
            )
        elif len(graph_configs) == 1:
            _record(results, "OK", "graph_config", f"single graph config: {graph_configs[0].name}")
            selected_graph = graph_configs[0]
        else:
            selected_graph = _load_graph_config_choice(context["branch_path"], graph_configs)
            if selected_graph:
                _record(results, "OK", "graph_selection", f"selected graph: {selected_graph.name}")
            else:
                _record(
                    results,
                    "WARN",
                    "graph_selection",
                    "multiple graph configs found but .graph_config is not selected",
                )

        # ── flow 结构有效性 ──
        _check_flow_structure(results, flow_base, "base")
        if flow_overlay:
            _check_flow_structure(results, flow_overlay, "overlay")

        state_store = StateStore(context["branch_path"] / "state.yaml")
        if state_store.exists():
            _record(results, "OK", "state_file", "state.yaml exists")
            saved_graph = state_store.load_graph_config()
            if saved_graph:
                _record(results, "OK", "state_graph", f"state graph marker: {saved_graph}")
                if len(graph_configs) > 1 and selected_graph and saved_graph != selected_graph.name:
                    _record(
                        results,
                        "WARN",
                        "state_graph",
                        f"state graph ({saved_graph}) mismatches selected graph ({selected_graph.name})",
                    )
            else:
                _record(results, "WARN", "state_graph", "state.yaml has no graph marker (_graph_config)")
        else:
            _record(results, "WARN", "state_file", "state.yaml not found (no execution history yet)")

    return _finish(results, strict, json_mode)


def _check_flow_structure(results, flow_path: Path, label: str) -> None:
    """检查 flow 目录下的 step.yaml 是否存在且可解析。"""
    cmds_dir = flow_path / "cmds"
    if not cmds_dir.exists():
        _record(results, "WARN", f"flow_{label}_cmds",
                f"No cmds/ directory in {label} flow: {flow_path}")
        return

    step_yamls = sorted(cmds_dir.glob("*/step.yaml"))
    if not step_yamls:
        _record(results, "WARN", f"flow_{label}_step_yaml",
                f"No tool step.yaml found under {cmds_dir}")
        return

    _record(results, "OK", f"flow_{label}_step_yaml",
            f"{label} flow: {len(step_yamls)} tool(s) with step.yaml")

    parse_errors = []
    for step_yaml in step_yamls:
        try:
            yaml.safe_load(step_yaml.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            parse_errors.append(f"{step_yaml.parent.name}/step.yaml: {exc}")

    if parse_errors:
        for err in parse_errors:
            _record(results, "ERR", f"flow_{label}_parse", f"YAML parse error: {err}")
    else:
        _record(results, "OK", f"flow_{label}_parse",
                f"{label} flow: all step.yaml files parse cleanly")


def _finish(results, strict: bool, json_mode: bool) -> None:
    errors = sum(1 for i in results if i["level"] == "ERR")
    warns = sum(1 for i in results if i["level"] == "WARN")

    if json_mode:
        payload = {
            "summary": {
                "errors": errors,
                "warnings": warns,
                "strict": strict,
            },
            "checks": results,
        }
        click.echo(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        _emit_human(results)
        click.echo("")
        click.echo(f"Doctor summary: {errors} error(s), {warns} warning(s)")

    if errors or (strict and warns):
        raise click.ClickException("Doctor found blocking issues.")
