from flask_socketio import emit


def register_handlers(socketio):
    """Register WebSocket event handlers."""

    @socketio.on('connect')
    def handle_connect():
        emit('connected', {'message': 'EDP WebSocket connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        pass

    @socketio.on('request_status')
    def handle_request_status(data):
        """Client requests current status of all steps."""
        emit('status_response', {'steps': {}})
