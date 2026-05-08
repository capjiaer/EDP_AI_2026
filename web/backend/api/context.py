"""API endpoint: GET /api/context — return workspace context from CWD."""

from flask import Blueprint, jsonify, current_app
from pathlib import Path

from dirkit.project_finder import ProjectFinder

context_bp = Blueprint('context', __name__)


@context_bp.route('/context')
def get_context():
    """Return workspace context detected from the CWD where `edp gui` was launched.

    Returns:
        {
            'workdir': '/path/to/workdir' or '',
            'foundry': 'SAMSUNG' or '',
            'node': 'S4' or '',
            'project': 'dongting' or '',
            'project_node': 'P85' or '',
            'has_context': bool,
        }
    """
    result = {
        'workdir': '',
        'foundry': '',
        'node': '',
        'project': '',
        'project_node': '',
        'has_context': False,
    }

    workdir = current_app.config.get('EDP_WORKDIR', '')
    if not workdir:
        return jsonify(result)

    result['workdir'] = workdir

    edp_center = current_app.config.get('EDP_CENTER', '')
    if not edp_center:
        return jsonify(result)

    from dirkit.project_finder import ProjectFinder
    finder = ProjectFinder(Path(edp_center) / 'flow' / 'initialize')
    ctx = finder.resolve_context(Path(workdir))
    if not ctx:
        # Fallback: use values passed from CLI (when no .edp_version exists)
        foundry = current_app.config.get('EDP_FOUNDRY', '')
        node = current_app.config.get('EDP_NODE', '')
        project = current_app.config.get('EDP_PROJECT', '')
        if foundry and node and project:
            result.update(has_context=True, foundry=foundry, node=node, project=project)
            return jsonify(result)
        return jsonify(result)

    result.update(
        has_context=True,
        foundry=ctx.get('foundry', ''),
        node=ctx.get('node', ''),
        project=ctx.get('project_name', ''),
        project_node=ctx.get('project_node', ''),
    )
    return jsonify(result)
