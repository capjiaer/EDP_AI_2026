#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
edp.commands.init - Init Wizard API endpoints

Delegates to dirkit.WorkPathInitializer for all business logic.
"""

from pathlib import Path
from datetime import date

from flask import Blueprint, jsonify, request, current_app

from dirkit import WorkPathInitializer, get_current_user
from edp.context import _find_graph_configs

init_bp = Blueprint('init', __name__)


def _get_work_path():
    """Get WORK_PATH from config or env."""
    wp = current_app.config.get('WORK_PATH')
    if wp:
        return str(wp)
    import os
    return os.environ.get('WORK_PATH', '')


@init_bp.route('/init/work-path', methods=['GET'])
def get_work_path():
    return jsonify({'work_path': _get_work_path()})


@init_bp.route('/init/work-path', methods=['POST'])
def set_work_path():
    data = request.get_json(silent=True) or {}
    wp = data.get('work_path', '').strip()
    if not wp:
        return jsonify({'error': 'work_path is required'}), 400
    p = Path(wp)
    if not p.is_absolute():
        return jsonify({'error': 'work_path must be an absolute path'}), 400
    current_app.config['WORK_PATH'] = str(p.resolve())
    return jsonify({'status': 'ok', 'work_path': str(p.resolve())})


@init_bp.route('/init/user-info', methods=['GET'])
def user_info():
    d = date.today()
    branch = f"{d.year}_{d.month}_{d.day}_main"
    return jsonify({'user_name': get_current_user(), 'default_branch': branch})


@init_bp.route('/init/graph-configs', methods=['GET'])
def graph_configs():
    foundry = request.args.get('foundry', '')
    node = request.args.get('node', '')
    project = request.args.get('project', '')
    if not all([foundry, node, project]):
        return jsonify({'error': 'foundry, node, project are required'}), 400

    edp_center = current_app.config.get('EDP_CENTER')
    if not edp_center:
        return jsonify({'error': 'EDP_CENTER not configured'}), 500

    init_path = Path(edp_center) / 'flow' / 'initialize'
    flow_base = init_path / foundry / node / 'common_prj'
    flow_overlay = init_path / foundry / node / project

    configs = _find_graph_configs(flow_base, flow_overlay)
    return jsonify({
        'graph_configs': [{'name': f.name, 'path': str(f)} for f in configs]
    })


@init_bp.route('/init/project', methods=['POST'])
def init_project():
    """PM mode: create project skeleton."""
    data = request.get_json(silent=True) or {}
    work_path = data.get('work_path', '')
    project_name = data.get('project_name', '')
    version = data.get('version', '')
    foundry = data.get('foundry', '')
    node = data.get('node', '')
    graph_config = data.get('graph_config', '')

    errors = []
    if not work_path:
        errors.append('work_path is required')
    if not project_name:
        errors.append('project_name is required')
    if not version:
        errors.append('version is required')
    if not foundry:
        errors.append('foundry is required')
    if not node:
        errors.append('node is required')
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    edp_center = current_app.config.get('EDP_CENTER')
    if not edp_center:
        return jsonify({'error': 'EDP_CENTER not configured'}), 500

    try:
        wpi = WorkPathInitializer(edp_center)
        result = wpi.init_project(
            work_path=work_path,
            project_name=project_name,
            project_node=version,
            blocks=[],
            foundry=foundry,
            node=node,
            graph_config=graph_config or None,
        )
        return jsonify({
            'status': 'ok',
            'work_path': str(result['work_path']),
            'project': result['project'],
            'project_path': str(result['project_node']),
            'foundry': result['foundry'],
            'node': result['node'],
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@init_bp.route('/init/block', methods=['POST'])
def init_block():
    """User mode: create block workspace."""
    data = request.get_json(silent=True) or {}
    work_path = data.get('work_path', '')
    project_name = data.get('project_name', '')
    version = data.get('version', '')
    foundry = data.get('foundry', '')
    node = data.get('node', '')
    block_name = data.get('block_name', '')
    user_name = data.get('user_name', '')
    branch_name = data.get('branch_name', '')
    link_mode = data.get('link_mode', True)

    errors = []
    if not work_path:
        errors.append('work_path is required')
    if not project_name:
        errors.append('project_name is required')
    if not version:
        errors.append('version is required')
    if not foundry:
        errors.append('foundry is required')
    if not node:
        errors.append('node is required')
    if not block_name:
        errors.append('block_name is required')
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    edp_center = current_app.config.get('EDP_CENTER')
    if not edp_center:
        return jsonify({'error': 'EDP_CENTER not configured'}), 500

    if not user_name:
        user_name = get_current_user()
    if not branch_name:
        d = date.today()
        branch_name = f"{d.year}_{d.month}_{d.day}_main"

    try:
        wpi = WorkPathInitializer(edp_center)

        # Step 1: init project with block
        wpi.init_project(
            work_path=work_path,
            project_name=project_name,
            project_node=version,
            blocks=[block_name],
            foundry=foundry,
            node=node,
        )

        # Step 2: init user workspace
        ws_result = wpi.init_user_workspace(
            work_path=work_path,
            project_name=project_name,
            project_node=version,
            block_name=block_name,
            user_name=user_name,
            branch_name=branch_name,
            link_mode=link_mode,
        )

        return jsonify({
            'status': 'ok',
            'branch_path': str(ws_result.get('branch_path', '')),
            'user_name': user_name,
            'branch_name': branch_name,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
