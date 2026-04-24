#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.cli - EDA workflow management CLI

纯编排层：解析参数 → 调 kit → 格式化输出。不含业务逻辑。
"""

import os
from pathlib import Path

import click

from edp.commands import init, run, status, retry, graph_cmd, doctor, flow_create_alias


@click.group(context_settings={
    'help_option_names': ['-h', '--help'],
})
@click.option(
    '--edp-center', envvar='EDP_CENTER',
    type=click.Path(),
    help='Override EDP_CENTER path (default: auto-detect from EDP_ROOT)'
)
@click.pass_context
def cli(ctx, edp_center):
    """EDP workflow management CLI"""
    ctx.ensure_object(dict)
    if edp_center:
        ctx.obj['edp_center'] = Path(edp_center).resolve()
    elif 'EDP_ROOT' in os.environ:
        ctx.obj['edp_center'] = Path(os.environ['EDP_ROOT']) / 'resources'
    else:
        ctx.obj['edp_center'] = None


# 注册命令
cli.add_command(init)
cli.add_command(run)
cli.add_command(status)
cli.add_command(retry)
cli.add_command(graph_cmd)
cli.add_command(doctor)
cli.add_command(flow_create_alias)
