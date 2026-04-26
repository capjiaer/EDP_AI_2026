import os
import sys
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

# Ensure packages/ is importable
_project_root = Path(__file__).resolve().parent.parent.parent
_packages = _project_root / 'packages'
if str(_packages) not in sys.path:
    sys.path.insert(0, str(_packages))

socketio = SocketIO(cors_allowed_origins='*')


def create_app(edp_center=None):
    app = Flask(__name__, static_folder=None)

    if edp_center:
        app.config['EDP_CENTER'] = Path(edp_center).resolve()
    elif 'EDP_CENTER' in os.environ:
        app.config['EDP_CENTER'] = Path(os.environ['EDP_CENTER']).resolve()
    elif 'EDP_ROOT' in os.environ:
        app.config['EDP_CENTER'] = Path(os.environ['EDP_ROOT']) / 'resources'
    else:
        app.config['EDP_CENTER'] = _project_root / 'resources'

    CORS(app)
    socketio.init_app(app)

    from .api import init_app as init_api
    init_api(app)

    from .ws import register_handlers
    register_handlers(socketio)

    # Initialize run service with socketio reference
    from .services.run_service import init as run_service_init
    run_service_init(socketio)

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'})

    # Serve Vue frontend in production
    static_dir = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
    if static_dir.exists():
        app.config['STATIC_DIR'] = static_dir

        @app.route('/')
        @app.route('/<path:path>')
        def serve_frontend(path='index.html'):
            static = app.config.get('STATIC_DIR')
            if not static:
                return jsonify({'error': 'Frontend not built'}), 404
            file_path = static / path
            if file_path.exists() and file_path.is_file():
                return send_from_directory(static, path)
            return send_from_directory(static, 'index.html')

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
