from flask import Blueprint

bp = Blueprint('api', __name__, url_prefix='/api')


def init_app(app):
    """Register all API blueprints."""
    from .graph import graph_bp
    from .status import status_bp
    from .run import run_bp
    from .projects import projects_bp
    from .step_detail import step_detail_bp

    for sub_bp in [graph_bp, status_bp, run_bp, projects_bp, step_detail_bp]:
        app.register_blueprint(sub_bp, url_prefix='/api')
