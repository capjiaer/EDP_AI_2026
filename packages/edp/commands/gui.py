#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.gui - Launch EDP Web UI
"""

import os
import subprocess
import sys
import webbrowser
import threading
from pathlib import Path

import click


def _is_wsl() -> bool:
    """Detect if running under WSL."""
    try:
        return 'microsoft' in Path('/proc/version').read_text().lower()
    except Exception:
        return False


def _open_browser(url: str) -> None:
    """Open URL in browser — works in both native Linux and WSL."""
    if _is_wsl():
        # WSL: use cmd.exe to open Windows default browser
        subprocess.Popen(['cmd.exe', '/c', 'start', url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def _latest_mtime(directory: Path) -> float:
    """Get the latest modification time of all files under a directory."""
    latest = 0.0
    for f in directory.rglob('*'):
        if f.is_file():
            try:
                mtime = f.stat().st_mtime
                if mtime > latest:
                    latest = mtime
            except OSError:
                pass
    return latest


def _ensure_frontend(web_dir: Path) -> None:
    """Check and rebuild frontend if source is newer than dist."""
    static_dir = web_dir / 'frontend' / 'dist'
    frontend_dir = web_dir / 'frontend'
    src_dir = frontend_dir / 'src'

    dist_missing = not static_dir.exists()
    # `edp gui --no-build` can be used to skip the check
    # (auto-rebuild only when dist is missing or src is newer)
    src_newer = (
        static_dir.exists()
        and src_dir.exists()
        and _latest_mtime(src_dir) > _latest_mtime(static_dir)
    )

    if not (dist_missing or src_newer):
        return

    # Check npm install freshness
    pkg_json = frontend_dir / 'package.json'
    node_modules = frontend_dir / 'node_modules'
    if pkg_json.exists() and (not node_modules.exists()
                              or pkg_json.stat().st_mtime > node_modules.stat().st_mtime):
        click.echo("  Running npm install...")
        result = subprocess.run(
            ['npm', 'install'],
            cwd=str(frontend_dir),
            capture_output=True, text=True
        )
        if result.returncode != 0:
            click.echo("  npm install failed:")
            click.echo(result.stderr)
            click.echo()
        else:
            click.echo("  npm install done.")

    click.echo("  Running npm run build...")
    result = subprocess.run(
        ['npm', 'run', 'build'],
        cwd=str(frontend_dir),
        capture_output=True, text=True
    )
    if result.returncode == 0:
        click.echo("  Frontend build complete.")
    else:
        click.echo("  Frontend build failed:")
        click.echo(result.stderr)
        click.echo()
        click.echo("You can still use `npm run dev` on another terminal for hot-reload.")
    click.echo()


@click.command()
@click.option('-p', '--port', default=5000, help='Web server port (default: 5000)')
@click.option('--host', default='127.0.0.1', help='Web server host (default: 127.0.0.1)')
@click.option('--debug/--no-debug', default=False, help='Flask debug mode')
@click.option('--no-build', is_flag=True, default=False, help='Skip frontend rebuild check')
@click.pass_context
def gui(ctx, port, host, debug, no_build):
    """Launch EDP Web UI."""
    edp_center = ctx.obj['edp_center']
    if not edp_center:
        raise click.ClickException(
            "EDP_CENTER is required. Use --edp-center or set EDP_ROOT."
        )

    # Add web/ to sys.path so `from backend.app import ...` works
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    web_dir = project_root / 'web'
    if str(web_dir) not in sys.path:
        sys.path.insert(0, str(web_dir))

    if not no_build:
        _ensure_frontend(web_dir)

    # Detect workspace context from CWD
    workdir = os.getcwd()
    work_path = os.environ.get('WORK_PATH', '')
    foundry_auto = node_auto = project_auto = ''
    try:
        from dirkit.project_finder import ProjectFinder
        finder = ProjectFinder(Path(edp_center) / 'flow' / 'initialize')
        ctx = finder.resolve_context(Path(workdir))
        if ctx:
            foundry_auto = ctx.get('foundry', '')
            node_auto = ctx.get('node', '')
            project_auto = ctx.get('project_name', '')
            # Infer WORK_PATH from context: {work_path}/{project}/{version}
            if not work_path and 'work_path' in ctx:
                work_path = ctx['work_path']
    except Exception:
        pass

    from backend.app import create_app, socketio

    app = create_app(
        edp_center=edp_center,
        workdir=workdir,
        foundry=foundry_auto,
        node=node_auto,
        project=project_auto,
    )
    if work_path:
        app.config['WORK_PATH'] = work_path

    if foundry_auto:
        click.echo(f"Detected workspace: {foundry_auto}/{node_auto}/{project_auto}")
    else:
        click.echo("No EDP workspace detected — use Init Wizard to start a project.")

    url = f'http://{host}:{port}'
    click.echo(f"EDP Web UI starting at {url}")
    click.echo("Press Ctrl+C to stop.")

    threading.Timer(1.5, lambda: _open_browser(url)).start()
    socketio.run(app, host=host, port=port, debug=debug)
