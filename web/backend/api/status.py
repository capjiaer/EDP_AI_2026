from flask import Blueprint, jsonify, request
from pathlib import Path

from flowkit.core.state_store import StateStore

status_bp = Blueprint('status', __name__)


@status_bp.route('/status', methods=['GET'])
def get_status():
    """Return current status of all steps.

    Query params:
        workdir (required): path to the branch workdir containing state.yaml
    """
    workdir = request.args.get('workdir')
    if not workdir:
        return jsonify({'error': 'workdir is required'}), 400

    store = StateStore(Path(workdir) / 'state.yaml')
    saved = store.load()
    status_map = {}
    for sid, status in saved.items():
        status_map[sid] = {'status': status.value}

    return jsonify({'steps': status_map})
