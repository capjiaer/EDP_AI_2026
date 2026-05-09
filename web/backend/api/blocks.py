"""API endpoint: GET /api/blocks — list existing blocks for a project/version."""

from flask import Blueprint, jsonify, request, current_app
from pathlib import Path

import yaml

blocks_bp = Blueprint('blocks', __name__)


@blocks_bp.route('/blocks', methods=['GET'])
def get_blocks():
    """Return existing blocks for a project/version.

    Reads from {WORK_PATH}/{project}/{version}/.edp_version.

    Query params:
        project: required
        version: required

    Returns:
        {'blocks': [{'name': str, 'created_at': str, 'created_by': str,
                      'user_count': int, 'users': [str]}]}
    """
    project = request.args.get('project', '')
    version = request.args.get('version', '')
    if not project or not version:
        return jsonify({'error': 'project and version are required'}), 400

    work_path = current_app.config.get('WORK_PATH')
    if not work_path:
        work_path = current_app.config.get('EDP_WORKDIR', '')
    if not work_path:
        import os
        work_path = os.environ.get('WORK_PATH', '')
    if not work_path:
        return jsonify({'blocks': []})

    project_ver_dir = Path(work_path) / project / version
    if not project_ver_dir.exists():
        return jsonify({'blocks': []})

    # Read .edp_version for extra metadata
    version_file = project_ver_dir / '.edp_version'
    info = {}
    if version_file.exists():
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                info = yaml.safe_load(f) or {}
        except Exception:
            pass

    block_users = info.get('block_users', {})

    # Scan filesystem for block/user directories
    result = []
    seen_blocks = set()
    for block_dir in sorted(project_ver_dir.iterdir()):
        if not block_dir.is_dir() or block_dir.name.startswith('.'):
            continue
        name = block_dir.name
        seen_blocks.add(name)

        # Scan user subdirectories
        users = list(block_users.get(name, []))
        user_count = len(users)
        for user_dir in sorted(block_dir.iterdir()):
            if user_dir.is_dir() and not user_dir.name.startswith('.'):
                if user_dir.name not in users:
                    users.append(user_dir.name)

        result.append({
            'name': name,
            'created_at': '',
            'created_by': '',
            'users': users,
            'user_count': user_count if user_count > 0 else len(users),
        })

    return jsonify({'blocks': sorted(result, key=lambda b: b['name'])})
