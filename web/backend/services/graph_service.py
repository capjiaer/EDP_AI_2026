from pathlib import Path
from typing import Dict, List, Optional, Any

from flowkit.loader.dependency_loader import DependencyLoader
from flowkit.core.step import StepStatus


def _load_step_config(flow_base: Path, flow_overlay: Optional[Path]) -> Dict[str, str]:
    """Load step_config.yaml -> {step: tool} dict."""
    import yaml

    config_path = None
    if flow_overlay and flow_overlay.exists():
        p = flow_overlay / 'step_config.yaml'
        if p.exists():
            config_path = p
    if not config_path:
        p = flow_base / 'step_config.yaml'
        if p.exists():
            config_path = p
    if not config_path:
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or 'steps' not in data:
        return {}

    tool_selection = {}
    for entry in data['steps']:
        if '.' in str(entry):
            tool, step = str(entry).rsplit('.', 1)
            tool_selection[step] = tool
        else:
            tool_selection[str(entry)] = str(entry)
    return tool_selection


def _find_graph_configs(flow_base: Path, flow_overlay: Optional[Path]) -> List[Path]:
    """Find all graph_config*.yaml files."""
    files = {}
    if flow_base.exists():
        for f in sorted(flow_base.glob('graph_config*.yaml')):
            files[f.name] = f
    if flow_overlay and flow_overlay.exists():
        for f in sorted(flow_overlay.glob('graph_config*.yaml')):
            files[f.name] = f
    return sorted(files.values())


def load_graph_data(edp_center: Path, foundry: str, node: str,
                    project: str, graph_config: str = '') -> Dict[str, Any]:
    """Load graph for a specific foundry/node/project.

    Args:
        graph_config: if specified, load only this config file.
                      Otherwise load the first one found.

    Returns:
        {
            'nodes': [{'id': str, 'label': str, 'tool': str}],
            'edges': [{'source': str, 'target': str, 'weak': bool}],
            'graph_configs': [{'name': str, 'path': str}],
            'tool_selection': {step: tool},
        }
    """
    init_path = edp_center / 'flow' / 'initialize'
    flow_base = init_path / foundry / node / 'common_prj'
    flow_overlay = init_path / foundry / node / project

    tool_selection = _load_step_config(flow_base, flow_overlay)
    all_configs = _find_graph_configs(flow_base, flow_overlay)

    # Pick the requested config, or default to the first one
    if graph_config:
        selected = [c for c in all_configs if c.name == graph_config]
        configs_to_load = selected if selected else all_configs[:1]
    else:
        configs_to_load = all_configs[:1] if all_configs else []

    loader = DependencyLoader()
    if configs_to_load:
        graph = loader.load_from_multiple_files(configs_to_load)
    else:
        graph = loader.load_from_multiple_files([])

    nodes = []
    for step_id, step in graph.steps.items():
        nodes.append({
            'id': step_id,
            'label': step_id,
            'tool': tool_selection.get(step_id, ''),
        })

    edges = []
    for dep in graph.dependencies:
        edges.append({
            'source': dep.from_step,
            'target': dep.to_step,
            'weak': dep.weak,
        })

    return {
        'nodes': nodes,
        'edges': edges,
        'graph_configs': [{'name': gc.name, 'path': str(gc)}
                          for gc in all_configs],
        'tool_selection': tool_selection,
    }


def list_projects(edp_center: Path) -> List[Dict[str, Any]]:
    """Scan foundry/node/project hierarchy from resources/flow/initialize/.

    Returns:
        [{
            'foundry': str,
            'nodes': [{
                'node': str,
                'projects': [str, ...]
            }]
        }]
    """
    init_path = edp_center / 'flow' / 'initialize'
    if not init_path.exists():
        return []

    result = []
    for foundry_dir in sorted(init_path.iterdir()):
        if not foundry_dir.is_dir():
            continue
        foundry_name = foundry_dir.name
        nodes = []
        for node_dir in sorted(foundry_dir.iterdir()):
            if not node_dir.is_dir():
                continue
            node_name = node_dir.name
            projects = []
            for child in sorted(node_dir.iterdir()):
                if child.is_dir() and child.name != 'common_prj':
                    projects.append(child.name)
            nodes.append({'node': node_name, 'projects': projects})
        result.append({
            'foundry': foundry_name,
            'nodes': nodes,
        })
    return result
