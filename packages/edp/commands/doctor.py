#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.doctor - Environment and workspace diagnostics
"""

import json
import os
import shutil
from pathlib import Path

import click

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
