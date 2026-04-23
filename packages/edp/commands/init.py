#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.init - Initialize project or block workspace
"""

from datetime import date
from pathlib import Path

import click

from dirkit import WorkPathInitializer, get_current_user
from edp.completions import _complete_projects


@click.command()
@click.option('-prj', '--project', required=False, shell_complete=_complete_projects,
              help='Project name (PM mode, or auto-detected from cwd)')
@click.option('-ver', '--version', 'project_version',
              type=click.Choice(['P85', 'P95', 'P100']),
              default=None,
              help='Project version (default: P85, or auto-detected from cwd)')
@click.option('-blk', '--block', default=None,
              help='Block name (User mode, e.g. top, cpu_core)')
@click.option('-usr', '--user', 'user_name', default=None,
              help='User name (default: current OS user)')
@click.option('-br', '--branch', default=None,
              help='Branch name (default: {YYYY}_{M}_{D}_main)')
@click.option('--link/--no-link', default=True,
              help='Use symbolic links (default: yes)')
@click.pass_context
def init(ctx, project, project_version, block, user_name, branch, link):
    """Initialize project skeleton or block workspace.

    \b
    Two modes — pick one:
      PM:   edp init -prj dongting -ver P95         Create project skeleton
      User: edp init -blk pcie                       Create block + workspace
    """
    edp_center = ctx.obj['edp_center']
    if not edp_center:
        raise click.ClickException(
            "edp_center is required. Use --edp-center or set EDP_CENTER."
        )

    wp_init = WorkPathInitializer(edp_center)

    # ── 互斥检查：-prj 和 -blk 不能同时指定 ──
    if block and project:
        raise click.ClickException(
            "Cannot use -prj and -blk together.\n"
            "  PM mode:   edp init -prj <project> -ver <version>\n"
            "  User mode: edp init -blk <block>"
        )

    # ── User 模式：-blk → 建 block + user workspace ──
    if block:
        cwd_context = wp_init.resolve_context(Path.cwd())

        if cwd_context:
            project = project or cwd_context['project_name']
            project_version = project_version or cwd_context['project_node']
            work_path = cwd_context['work_path']
            user_name = user_name or cwd_context.get('user') or get_current_user()
        else:
            work_path = str(Path.cwd())
            user_name = user_name or get_current_user()

        if not project:
            raise click.ClickException(
                "Cannot detect project from current directory.\n"
                "  Please specify: edp init -blk <block> -prj <project>"
            )

        if branch is None:
            d = date.today()
            branch = f"{d.year}_{d.month}_{d.day}_main"

        if project_version is None:
            project_version = 'P85'

        # 校验项目存在并解析 foundry / node
        matches = wp_init.find_project(project)
        if not matches:
            available = [m['project_name'] for m in wp_init.list_projects()]
            raise click.ClickException(
                f"Project '{project}' not found.\n"
                f"  Available projects: {available}"
            )
        foundry, node = _resolve_foundry_node(wp_init, project, matches)

        wp_init.init_project(
            work_path=work_path,
            project_name=project,
            project_node=project_version,
            blocks=[block],
            foundry=foundry,
            node=node,
        )

        workspace = wp_init.init_user_workspace(
            work_path=work_path,
            project_name=project,
            project_node=project_version,
            block_name=block,
            user_name=user_name,
            branch_name=branch,
            link_mode=link,
        )

        click.echo(f"Block initialized successfully.")
        click.echo(f"  Project: {project} / {project_version} / {block}")
        click.echo(f"  User:    {user_name}")
        click.echo(f"  Branch:  {workspace.get('branch_path', 'N/A')}")
        if workspace.get('directories'):
            for name, path in workspace['directories'].items():
                click.echo(f"  {name}: {path}")
        return

    # ── PM 模式：-prj → 只建项目骨架 ──
    if not project:
        cwd_context = wp_init.resolve_context(Path.cwd())
        if cwd_context:
            prj = cwd_context['project_name']
            ver = cwd_context['project_node']
            raise click.ClickException(
                "Choose a mode:\n"
                f"  User mode: edp init -blk <block>           (create block under {prj}/{ver})\n"
                f"  PM mode:   edp init -prj <project> -ver <version>"
            )
        raise click.ClickException(
            "Choose a mode:\n"
            "  PM mode:   edp init -prj <project> -ver <version>\n"
            "  User mode: edp init -blk <block>"
        )

    if not project_version:
        raise click.ClickException(
            "PM mode requires -ver.\n"
            f"  Example: edp init -prj {project} -ver P95"
        )

    # 校验项目存在并解析 foundry / node
    matches = wp_init.find_project(project)
    if not matches:
        available = [m['project_name'] for m in wp_init.list_projects()]
        raise click.ClickException(
            f"Project '{project}' not found.\n"
            f"  Available projects: {available}"
        )
    foundry, node = _resolve_foundry_node(wp_init, project, matches)

    work_path = str(Path.cwd())

    wp_init.init_project(
        work_path=work_path,
        project_name=project,
        project_node=project_version,
        blocks=[],
        foundry=foundry,
        node=node,
    )

    proj_path = Path(work_path) / project / project_version
    click.echo(f"Project skeleton initialized.")
    click.echo(f"  Project: {project} / {project_version}")
    click.echo(f"  Path:    {proj_path}")


def _resolve_foundry_node(wp_init, project, matches, node=None):
    """从 matches 列表中解析 foundry 和 node。

    Returns:
        (foundry, node) tuple
    """
    if len(matches) == 1:
        return matches[0]['foundry'], matches[0]['node']

    if node:
        for m in matches:
            if m['node'] == node:
                return m['foundry'], node
        nodes = sorted(set(m['node'] for m in matches))
        raise click.ClickException(
            f"Node '{node}' not found for project '{project}'.\n"
            f"  Available nodes: {nodes}"
        )

    nodes = sorted(set(m['node'] for m in matches))
    raise click.ClickException(
        f"Project '{project}' exists in multiple nodes: {nodes}.\n"
        f"  Please specify -n (e.g. -n {nodes[0]})."
    )
