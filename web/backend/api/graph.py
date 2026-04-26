from flask import Blueprint, jsonify, request, current_app

from ..services.graph_service import load_graph_data

graph_bp = Blueprint('graph', __name__)


@graph_bp.route('/graph', methods=['GET'])
def get_graph():
    """Return step dependency graph for a project.

    Query params:
        foundry (required)
        node (required)
        project (required)
    """
    foundry = request.args.get('foundry')
    node = request.args.get('node')
    project = request.args.get('project')

    if not all([foundry, node, project]):
        return jsonify({'error': 'foundry, node, project are required'}), 400

    edp_center = current_app.config['EDP_CENTER']
    data = load_graph_data(edp_center, foundry, node, project)
    return jsonify(data)
