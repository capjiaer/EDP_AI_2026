from flask import Blueprint, jsonify, request, current_app

run_bp = Blueprint('run', __name__)


@run_bp.route('/run/<step>', methods=['POST'])
def run_step(step):
    """Trigger running a step in a background thread."""
    from ..services.run_service import start_step
    data = request.get_json(silent=True) or {}
    edp_center = current_app.config['EDP_CENTER']

    try:
        job_id = start_step(
            edp_center=edp_center,
            step=step,
            foundry=data.get('foundry', ''),
            node=data.get('node', ''),
            project=data.get('project', ''),
            workdir=data.get('workdir', ''),
        )
        return jsonify({'status': 'started', 'step': step, 'job_id': job_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
