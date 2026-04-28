#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.gui - Launch EDP Web UI
"""

import sys
import webbrowser
import threading
from pathlib import Path

import click


@click.command()
@click.option('-p', '--port', default=5000, help='Web server port (default: 5000)')
@click.option('--host', default='127.0.0.1', help='Web server host (default: 127.0.0.1)')
@click.option('--debug/--no-debug', default=False, help='Flask debug mode')
@click.pass_context
def gui(ctx, port, host, debug):
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

    # Check if frontend is built
    static_dir = web_dir / 'frontend' / 'dist'
    if not static_dir.exists():
        click.echo("Warning: Frontend not built. Run: cd web/frontend && npm run build")
        click.echo("  (You can still use `npm run dev` on another terminal for hot-reload)")
        click.echo()

    from backend.app import create_app
    from backend import socketio

    app = create_app(edp_center=edp_center)

    url = f'http://{host}:{port}'
    click.echo(f"EDP Web UI starting at {url}")
    click.echo("Press Ctrl+C to stop.")

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    socketio.run(app, host=host, port=port, debug=debug)
