from flask import Blueprint, jsonify, current_app

from ..services.graph_service import list_projects

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/projects', methods=['GET'])
def get_projects():
    """Return foundry/node/project hierarchy."""
    edp_center = current_app.config['EDP_CENTER']
    data = list_projects(edp_center)
    return jsonify(data)
