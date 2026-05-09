"""API endpoint: GET /api/workspace/projects — list all initialized projects from WORK_PATH."""

from flask import Blueprint, jsonify, request, current_app
from pathlib import Path

import yaml

workspace_bp = Blueprint('workspace', __name__)


def _get_work_path():
    wp = current_app.config.get('WORK_PATH')
    if wp:
        return str(wp)
    wp = current_app.config.get('EDP_WORKDIR', '')
    if wp:
        return str(wp)
    import os
    return os.environ.get('WORK_PATH', '')


@workspace_bp.route('/workspace/projects', methods=['GET'])
def list_workspace_projects():
    """Scan WORK_PATH for all initialized project/version directories.

    Reads each {project}/{version}/.edp_version and aggregates metadata.

    Returns:
        {
            'work_path': str,
            'projects': [{
                'name': str,
                'versions': [{
                    'version': str,
                    'foundry': str,
                    'node': str,
                    'created_at': str,
                    'created_by': str,
                    'block_count': int,
                    'block_names': [str],
                    'graph_config': str or '',
                    'block_users': {str: [str]},
                }]
            }]
        }
    """
    work_path = _get_work_path()
    if not work_path:
        return jsonify({'work_path': '', 'projects': []})

    wp = Path(work_path)
    if not wp.exists():
        return jsonify({'work_path': work_path, 'projects': []})

    projects = []
    for project_dir in sorted(wp.iterdir()):
        if not project_dir.is_dir() or project_dir.name.startswith('.'):
            continue

        versions = []
        for ver_dir in sorted(project_dir.iterdir()):
            if not ver_dir.is_dir() or ver_dir.name.startswith('.'):
                continue

            version_file = ver_dir / '.edp_version'
            if not version_file.exists():
                continue

            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    info = yaml.safe_load(f) or {}
            except Exception:
                continue

            if 'project' not in info:
                continue

            blocks = info.get('blocks', {})
            block_names = sorted(blocks.keys())
            versions.append({
                'version': info.get('version', ver_dir.name),
                'foundry': info.get('foundry', ''),
                'node': info.get('node', ''),
                'created_at': info.get('created_at', ''),
                'created_by': info.get('created_by', ''),
                'block_count': len(block_names),
                'block_names': block_names,
                'graph_config': info.get('graph_config', ''),
                'block_users': info.get('block_users', {}),
            })

        if versions:
            projects.append({
                'name': project_dir.name,
                'versions': versions,
            })

    return jsonify({'work_path': work_path, 'projects': projects})


@workspace_bp.route('/workspace/block-users', methods=['PUT'])
def update_block_users():
    """Update block_users in an existing project's .edp_version."""
    data = request.get_json(silent=True) or {}
    project = data.get('project', '')
    version = data.get('version', '')
    block_users = data.get('block_users', {})

    if not project or not version:
        return jsonify({'error': 'project and version are required'}), 400
    if not isinstance(block_users, dict):
        return jsonify({'error': 'block_users must be an object'}), 400

    work_path = _get_work_path()
    if not work_path:
        return jsonify({'error': 'WORK_PATH not configured'}), 500

    version_file = Path(work_path) / project / version / '.edp_version'
    if not version_file.exists():
        return jsonify({'error': '.edp_version not found'}), 404

    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            info = yaml.safe_load(f) or {}
    except Exception as e:
        return jsonify({'error': f'Failed to read .edp_version: {e}'}), 500

    # Validate and create block/user directories
    project_dir = Path(work_path) / project / version
    for block_name, users in block_users.items():
        if not isinstance(users, list):
            return jsonify({'error': f'block_users.{block_name} must be a list'}), 400
        for user_name in users:
            user_dir = project_dir / block_name / user_name
            user_dir.mkdir(parents=True, exist_ok=True)

    info['block_users'] = block_users

    try:
        with open(version_file, 'w', encoding='utf-8') as f:
            yaml.dump(info, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        return jsonify({'error': f'Failed to write .edp_version: {e}'}), 500

    return jsonify({'status': 'ok', 'project': project, 'version': version})
