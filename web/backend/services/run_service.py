import threading
import uuid
from pathlib import Path
from typing import Optional

from flowkit.core.executor import Executor
from flowkit.core.state_store import StateStore
from flowkit.loader.workflow_builder import WorkflowBuilder
from cmdkit import ScriptBuilder

# Shared state for tracking running jobs
_jobs = {}
_socketio = None


def init(socketio_instance):
    """Called at app startup to get the socketio reference."""
    global _socketio
    _socketio = socketio_instance


def start_step(edp_center, step, foundry, node, project, workdir=''):
    """Start running a step in a background thread.

    Returns:
        job_id (str)
    """
    if not all([foundry, node, project]):
        raise ValueError("foundry, node, project are required")

    job_id = str(uuid.uuid4())[:8]
    flow_base, flow_overlay, branch_path = _resolve_flow_paths(
        edp_center, foundry, node, project, workdir
    )

    _jobs[job_id] = {
        'step': step,
        'status': 'running',
    }

    thread = threading.Thread(
        target=_run_in_thread,
        args=(job_id, edp_center, step, flow_base, flow_overlay, branch_path),
        daemon=True,
    )
    thread.start()
    return job_id


def _resolve_flow_paths(edp_center, foundry, node, project, workdir):
    """Resolve flow base/overlay paths from project info."""
    init_path = edp_center / 'flow' / 'initialize'
    flow_base = init_path / foundry / node / 'common_prj'
    flow_overlay = init_path / foundry / node / project

    if workdir:
        branch_path = Path(workdir)
    else:
        branch_path = Path.cwd()

    return flow_base, flow_overlay, branch_path


def _run_in_thread(job_id, edp_center, step_name, flow_base, flow_overlay,
                   branch_path):
    """Execute a single step and emit status updates via WebSocket."""
    try:
        _emit_status(step_name, 'running', 'Step started')

        from .graph_service import _load_step_config
        tool_selection = _load_step_config(flow_base, flow_overlay)

        if step_name not in tool_selection:
            _emit_status(step_name, 'failed', f'Step {step_name} not in step_config')
            _jobs[job_id]['status'] = 'failed'
            return

        tool_name = tool_selection[step_name]

        sb = ScriptBuilder(flow_base, branch_path, flow_overlay)
        state_file = branch_path / 'state.yaml'
        state_store = StateStore(state_file)

        executor = Executor(
            workflow=None,
            script_builder=sb,
            state_store=state_store,
        )
        report = executor.run_single(tool_name, step_name)

        if report.success:
            _emit_status(step_name, 'success', 'Step completed')
            _jobs[job_id]['status'] = 'success'
        else:
            error_msg = ''
            if step_name in report.step_results:
                error_msg = report.step_results[step_name].error[:200]
            _emit_status(step_name, 'failed', error_msg or 'Step failed')
            _jobs[job_id]['status'] = 'failed'

    except Exception as e:
        _emit_status(step_name, 'failed', str(e))
        _jobs[job_id]['status'] = 'failed'


def _emit_status(step, status, message=''):
    """Push step status to all connected clients."""
    if _socketio:
        _socketio.emit('step_status', {
            'step': step,
            'status': status,
            'message': message,
        })


def get_job_status(job_id):
    """Get status of a background job."""
    return _jobs.get(job_id)
