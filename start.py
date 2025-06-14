import eventlet
eventlet.monkey_patch()

from flask_socketio import  emit
from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=9500)
