"""
Main Flask Application
Handles web server, WebSocket communication, and system orchestration
"""

from flask import Flask, render_template_string, Response
from flask_socketio import SocketIO
import threading
import time
import sys

# Import custom modules
try:
    from traffic_controller import TrafficController
    from camera_stream import CameraStream
except ImportError:
    print("ERROR: Required modules not found!")
    print("Make sure traffic_controller.py and camera_stream.py are in the same directory")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'traffic_system_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize system components
print("🚀 Initializing Smart Traffic Management System...")
traffic_controller = TrafficController()
camera_stream = CameraStream()
