#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.graph_cmd - Visualize dependency graph
"""

from pathlib import Path

import click

from flowkit import GraphVisualizer, get_graph_summary
from flowkit.loader.dependency_loader import DependencyLoader
from edp.context import _resolve_context, _pick_graph_config


@click.command('graph')
@click.option('-f', '--format', 'fmt', type=click.Choice(['ascii', 'dot', 'table']),
               default='ascii', help='Output format')
@click.option('-o', '--output', type=click.Path(), default=None,
               help='Output file (default: stdout)')
@click.pass_context
def graph_cmd(ctx, fmt, output):
    """Visualize dependency graph."""
    edp_center = ctx.obj['edp_center']
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    context = _resolve_context(ctx)

    # 选择图配置
    graph_config = _pick_graph_config(context['graph_configs'], context['branch_path'])
    click.echo(f"Graph config: {graph_config.name} ({graph_config.resolve()})")
    click.echo("")

    loader = DependencyLoader()
    graph = loader.load_from_multiple_files([graph_config])

    viz = GraphVisualizer()

    if fmt == 'ascii':
        content = viz.to_ascii_format(graph)
    elif fmt == 'dot':
        content = viz.to_dot_format(graph)
    else:
        content = viz.to_table_format(graph)

    content += "\n\n" + get_graph_summary(graph)

    if output:
        Path(output).write_text(content, encoding='utf-8')
        click.echo(f"Graph written to {output}")
    else:
        click.echo(content)
