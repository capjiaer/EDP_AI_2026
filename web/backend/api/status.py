from flask import Blueprint, jsonify, request
from pathlib import Path

from flowkit.core.state_store import StateStore

status_bp = Blueprint('status', __name__)


@status_bp.route('/status', methods=['GET'])
def get_status():
    """Return current status of all steps with timing info.

    Query params:
        workdir (required): path to the branch workdir containing state.yaml
    """
    workdir = request.args.get('workdir')
    if not workdir:
        return jsonify({'error': 'workdir is required'}), 400

    store = StateStore(Path(workdir) / 'state.yaml')
    raw = store._load_raw()
    status_map = {}
    for sid, info in raw.items():
        if sid.startswith('_'):
            continue
        entry = {'status': info.get('status', 'idle')}
        if 'execution_time' in info:
            entry['execution_time'] = info['execution_time']
        if 'error' in info:
            entry['error'] = info['error']
        status_map[sid] = entry

    return jsonify({'steps': status_map})
