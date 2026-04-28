"""API endpoint: GET /api/step-detail — return step info for SidePanel."""

from flask import Blueprint, request, jsonify
from pathlib import Path
import yaml

from edp.context import _load_step_config as _load_step_config_shared

step_detail_bp = Blueprint('step_detail', __name__)

_HOOK_TEMPLATE_MARKERS = ['# Your code here', '# Fill in your code']


@step_detail_bp.route('/step-detail')
def step_detail():
    foundry = request.args.get('foundry', '')
    node = request.args.get('node', '')
    project = request.args.get('project', '')
    step = request.args.get('step', '')
    workdir = request.args.get('workdir', '')

    if not all([foundry, node, project, step]):
        return jsonify({'error': 'foundry, node, project, step are required'}), 400

    edp_center = _get_edp_center()
    if not edp_center:
        return jsonify({'error': 'EDP_CENTER not configured'}), 500

    init_path = edp_center / 'flow' / 'initialize'
    flow_base = init_path / foundry / node / 'common_prj'
    flow_overlay = init_path / foundry / node / project

    tool_selection = _load_step_config_shared(flow_base, flow_overlay)
    tool_name = tool_selection.get(step)
    if not tool_name:
        return jsonify({'error': f'Step "{step}" not found in step_config'}), 404

    step_info = _load_step_info(flow_base, flow_overlay, tool_name, step)
    sub_steps = step_info.get('sub_steps', [])

    # File paths
    files = _resolve_step_files(flow_base, flow_overlay, tool_name, step, sub_steps)

    # Hooks (from workspace)
    hooks = []
    if workdir:
        hooks = _load_hooks(Path(workdir), tool_name, step, sub_steps)
        files.update(_resolve_generated_files(Path(workdir), tool_name, step))

    return jsonify({
        'step': step,
        'tool': tool_name,
        'sub_steps': sub_steps,
        'invoke': step_info.get('invoke', []),
        'files': files,
        'hooks': hooks,
    })


@step_detail_bp.route('/file-content')
def file_content():
    path = request.args.get('path', '')
    if not path:
        return jsonify({'error': 'path is required'}), 400
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        return jsonify({'error': f'File not found: {path}'}), 404
    # Security: only allow reading from EDP_CENTER or workdir
    edp_center = _get_edp_center().resolve()
    workdir = request.args.get('workdir', '')
    allowed = [edp_center]
    if workdir:
        allowed.append(Path(workdir).resolve())
    if not any(str(p).startswith(str(base)) for base in allowed if base):
        return jsonify({'error': 'Access denied'}), 403
    try:
        content = p.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'path': str(p), 'content': content})


def _get_edp_center():
    from flask import current_app
    return Path(current_app.config.get('EDP_CENTER', ''))


def _load_step_info(flow_base, flow_overlay, tool_name, step_name):
    for base in [flow_overlay, flow_base]:
        step_yaml = base / 'cmds' / tool_name / 'step.yaml'
        if not step_yaml.exists():
            continue
        with open(step_yaml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        tool_data = data.get(tool_name, {})
        steps = tool_data.get('supported_steps', {})
        if step_name in steps:
            return steps[step_name]
    return {}


def _resolve_step_files(flow_base, flow_overlay, tool_name, step_name, sub_steps):
    """Resolve file paths for step tcl, config, debug, launcher, and sub-step procs."""
    files = {}
    for base in [flow_overlay, flow_base]:
        cmds_dir = base / 'cmds' / tool_name
        # sub-step tcl files are under steps/{step_name}/{sub}.tcl
        sub_files = {}
        for sub in sub_steps:
            sub_tcl = cmds_dir / 'steps' / step_name / f'{sub}.tcl'
            if sub_tcl.exists():
                sub_files[sub] = str(sub_tcl.resolve())
        # also check procs/ dir
        for sub in sub_steps:
            if sub in sub_files:
                continue
            sub_tcl = cmds_dir / 'procs' / f'{sub}.tcl'
            if sub_tcl.exists():
                sub_files[sub] = str(sub_tcl.resolve())
        if sub_files:
            files['sub_step_files'] = sub_files
    return files


def _resolve_generated_files(workdir, tool_name, step_name):
    """Resolve generated cmd files in workspace (cmds/ and runs/)."""
    files = {}
    cmds_dir = workdir / 'cmds' / tool_name
    if cmds_dir.exists():
        for name, label in [
            (f'{step_name}_config.tcl', 'config_tcl'),
            (f'{step_name}.tcl', 'step_tcl'),
            (f'{step_name}_debug.tcl', 'debug_tcl'),
        ]:
            p = cmds_dir / name
            if p.exists():
                files[label] = str(p.resolve())

    runs_dir = workdir / 'runs' / tool_name / step_name
    if runs_dir.exists():
        for ext in ['.sh', '.csh']:
            launcher = runs_dir / f'{step_name}{ext}'
            if launcher.exists():
                files['launcher'] = str(launcher.resolve())
                break

    return files


def _load_hooks(workdir, tool_name, step_name, sub_steps):
    """Load non-default hooks from workspace."""
    hooks_dir = workdir / 'hooks' / tool_name / step_name
    if not hooks_dir.exists():
        return []

    result = []
    # Step-level hooks
    for hook_type in ['step.pre', 'step.post']:
        hook_file = hooks_dir / hook_type
        if hook_file.exists() and not _is_default_hook(hook_file):
            result.append({
                'name': hook_type,
                'type': 'step',
                'path': str(hook_file.resolve()),
                'is_default': False,
            })

    # Sub-step hooks
    for sub in sub_steps:
        for hook_type in [f'{sub}.pre', f'{sub}.post', f'{sub}.replace']:
            hook_file = hooks_dir / hook_type
            if hook_file.exists() and not _is_default_hook(hook_file):
                result.append({
                    'name': hook_type,
                    'type': 'sub_step',
                    'sub_step': sub,
                    'path': str(hook_file.resolve()),
                    'is_default': False,
                })

    return result


def _is_default_hook(path):
    """Check if a hook file is still a default template."""
    try:
        content = path.read_text(encoding='utf-8')
    except Exception:
        return True
    return any(marker in content for marker in _HOOK_TEMPLATE_MARKERS)
