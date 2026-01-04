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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Traffic Management System</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Header */
        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        h1 {
            font-size: 2.8em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .subtitle {
            font-size: 1.2em;
            color: rgba(255, 255, 255, 0.9);
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 15px;
            padding: 8px 16px;
            background: rgba(0, 255, 0, 0.2);
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff00;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Camera Feed */
        .camera-section {
            margin-bottom: 30px;
        }
        
        .section-title {
            font-size: 1.5em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .camera-feed {
            width: 100%;
            max-width: 1000px;
            margin: 0 auto;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3);
            background: #000;
        }
        
        .camera-feed img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        /* Lanes Grid */
        .lanes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .lane-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
            transition: transform 0.3s ease;
        }
        
        .lane-card:hover {
            transform: translateY(-5px);
        }
        
        .lane-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        }
        
        .lane-name {
            font-size: 2em;
            font-weight: bold;
        }
        
        .lane-subtitle {
            font-size: 0.9em;
            color: rgba(255, 255, 255, 0.7);
        }
        
        /* Traffic Lights */
        .signal-lights {
            display: flex;
            gap: 10px;
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 10px;
        }
        
        .light {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .light.red-on {
            background: #ff0000;
            box-shadow: 0 0 20px #ff0000, inset 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .light.yellow-on {
            background: #ffff00;
            box-shadow: 0 0 20px #ffff00, inset 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .light.green-on {
            background: #00ff00;
            box-shadow: 0 0 20px #00ff00, inset 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        /* Metrics */
        .metrics {
            display: grid;
            gap: 15px;
        }
        
        .metric-box {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metric-label {
            font-size: 0.95em;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric-value {
            font-size: 3em;
            font-weight: bold;
            line-height: 1;
        }
        
        .metric-unit {
            font-size: 0.4em;
            color: rgba(255, 255, 255, 0.6);
            margin-left: 5px;
        }
        
        .density-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.3em;
            margin-top: 5px;
        }
        
        .density-empty {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .density-low {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        
        .density-medium {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .density-high {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            color: #000;
        }
        
        /* System Status */
        .system-status {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .status-item {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .status-value {
            font-size: 1.8em;
            font-weight: bold;
            margin-top: 10px;
        }
        
        /* Footer */
        footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.9em;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .lanes-grid {
                grid-template-columns: 1fr;
            }
            
            h1 {
                font-size: 2em;
            }
            
            .metric-value {
                font-size: 2.5em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <h1>🚦 Smart Traffic Management System</h1>
            <p class="subtitle">Real-time IoT Traffic Monitoring & Control</p>
            <div class="status-badge">
                <span class="status-indicator"></span>
                <span>System Online</span>
            </div>
        </header>

        <!-- Camera Feed -->
        <div class="camera-section">
            <h2 class="section-title">📹 Live Traffic Feed</h2>
            <div class="camera-feed">
                <img src="/video" alt="Live Traffic Feed" id="camera-stream">
            </div>
        </div>

        <!-- Traffic Lanes -->
        <div class="lanes-grid">
            <!-- Lane A -->
            <div class="lane-card">
                <div class="lane-header">
                    <div>
                        <div class="lane-name">🅰️ Lane A</div>
                        <div class="lane-subtitle">North-South Direction</div>
                    </div>
                    <div class="signal-lights">
                        <div class="light" id="light-a-red"></div>
                        <div class="light" id="light-a-yellow"></div>
                        <div class="light" id="light-a-green"></div>
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric-box">
                        <div class="metric-label">Vehicle Count</div>
                        <div class="metric-value">
                            <span id="count-a">0</span>
                            <span class="metric-unit">vehicles</span>
                        </div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Average Speed</div>
                        <div class="metric-value">
                            <span id="speed-a">0.0</span>
                            <span class="metric-unit">km/h</span>
                        </div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Density Status</div>
                        <div>
                            <span class="density-badge density-empty" id="density-a">Empty</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Lane B -->
            <div class="lane-card">
                <div class="lane-header">
                    <div>
                        <div class="lane-name">🅱️ Lane B</div>
                        <div class="lane-subtitle">East-West Direction</div>
                    </div>
                    <div class="signal-lights">
                        <div class="light" id="light-b-red"></div>
                        <div class="light" id="light-b-yellow"></div>
                        <div class="light" id="light-b-green"></div>
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric-box">
                        <div class="metric-label">Vehicle Count</div>
                        <div class="metric-value">
                            <span id="count-b">0</span>
                            <span class="metric-unit">vehicles</span>
                        </div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Average Speed</div>
                        <div class="metric-value">
                            <span id="speed-b">0.0</span>
                            <span class="metric-unit">km/h</span>
                        </div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Density Status</div>
                        <div>
                            <span class="density-badge density-empty" id="density-b">Empty</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Status -->
        <div class="system-status">
            <h2 class="section-title">📊 System Status</h2>
            <div class="status-grid">
                <div class="status-item">
                    <div class="metric-label">Current Signal</div>
                    <div class="status-value" id="current-signal">All RED</div>
                </div>
                
                <div class="status-item">
                    <div class="metric-label">Control Mode</div>
                    <div class="status-value">Round-Robin</div>
                </div>
                
                <div class="status-item">
                    <div class="metric-label">Last Update</div>
                    <div class="status-value" id="last-update">--:--:--</div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer>
            <p>🔧 Powered by Raspberry Pi Zero 2W</p>
            <p>📡 VL53L0X ToF Sensors | 📹 Pi Camera | 🌐 Flask + Socket.IO</p>
            <p>© 2024 Smart Traffic Management System</p>
        </footer>
    </div>

    <script>
        // Initialize Socket.IO connection
        const socket = io();

        // Connection event handlers
        socket.on('connect', () => {
            console.log('✅ Connected to server');
        });

        socket.on('disconnect', () => {
            console.log('❌ Disconnected from server');
        });

        // Traffic data update handler
        socket.on('traffic_update', (data) => {
            // Update Lane A
            document.getElementById('count-a').textContent = data.laneA.count;
            document.getElementById('speed-a').textContent = data.laneA.speed.toFixed(1);
            updateDensity('a', data.laneA.count);

            // Update Lane B
            document.getElementById('count-b').textContent = data.laneB.count;
            document.getElementById('speed-b').textContent = data.laneB.speed.toFixed(1);
            updateDensity('b', data.laneB.count);

            // Update traffic signals
            updateSignals(data.signal);

            // Update current signal text
            let signalText = 'All RED';
            if (data.signal === 'GREEN_A') {
                signalText = 'Lane A - GREEN ✅';
            } else if (data.signal === 'GREEN_B') {
                signalText = 'Lane B - GREEN ✅';
            }
            document.getElementById('current-signal').textContent = signalText;

            // Update timestamp
            const time = new Date(data.timestamp).toLocaleTimeString();
            document.getElementById('last-update').textContent = time;
        });

        // Update density badge
        function updateDensity(lane, count) {
            const element = document.getElementById(`density-${lane}`);
            element.className = 'density-badge ';
            
            if (count === 0) {
                element.className += 'density-empty';
                element.textContent = 'Empty';
            } else if (count < 5) {
                element.className += 'density-low';
                element.textContent = 'Low';
            } else if (count < 10) {
                element.className += 'density-medium';
                element.textContent = 'Medium';
            } else {
                element.className += 'density-high';
                element.textContent = 'High';
            }
        }

        // Update traffic signal lights
        function updateSignals(signal) {
            // Reset all lights
            const lanes = ['a', 'b'];
            const colors = ['red', 'yellow', 'green'];
            
            lanes.forEach(lane => {
                colors.forEach(color => {
                    const element = document.getElementById(`light-${lane}-${color}`);
                    element.classList.remove(`${color}-on`);
                });
            });

            // Set appropriate lights based on current signal
            if (signal === 'RED') {
                document.getElementById('light-a-red').classList.add('red-on');
                document.getElementById('light-b-red').classList.add('red-on');
            } else if (signal === 'GREEN_A') {
                document.getElementById('light-a-green').classList.add('green-on');
                document.getElementById('light-b-red').classList.add('red-on');
            } else if (signal === 'GREEN_B') {
                document.getElementById('light-b-green').classList.add('green-on');
                document.getElementById('light-a-red').classList.add('red-on');
            }
        }

        // Camera error handling
        document.getElementById('camera-stream').onerror = function() {
            this.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.style.cssText = 'padding: 100px; text-align: center; background: #000;';
            placeholder.innerHTML = '<p style="font-size: 1.5em;">📹 Camera feed unavailable</p><p style="color: #888; margin-top: 10px;">Connect Pi Camera to enable live view</p>';
            this.parentElement.appendChild(placeholder);
        };
    </script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Serve main dashboard page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/video')
def video():
    """Stream live camera feed"""
    return Response(
        camera_stream.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# ═══════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════════════════

def broadcast_traffic_updates():
    """Background thread to broadcast traffic data via WebSocket"""
    print("📡 Starting data broadcast thread...")
    
    while True:
        try:
            # Get current traffic state
            data = traffic_controller.get_current_state()
            
            # Broadcast to all connected clients
            socketio.emit('traffic_update', data)
            
            # Update every 500ms for smooth real-time experience
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️  Broadcast error: {e}")
            time.sleep(1)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚦 SMART TRAFFIC MANAGEMENT SYSTEM")
    print("="*70)
    
    # Start traffic controller
    print("🚀 Starting traffic controller...")
    traffic_controller.start()
    
    # Start data broadcast thread
    print("📡 Starting WebSocket broadcast...")
    broadcast_thread = threading.Thread(
        target=broadcast_traffic_updates,
        daemon=True
    )
    broadcast_thread.start()
    
    print("\n✅ System initialization complete!")
    print("="*70)
    print("📱 Access dashboard at:")
    print("   http://localhost:5000")
    print("   http://<raspberry-pi-ip>:5000")
    print("="*70)
    print("💡 Press Ctrl+C to stop the system\n")
    
    # Run Flask app with SocketIO
    try:
        socketio.run(
            app,
            host='0.0.0.0',  # Accept connections from any IP
            port=5000,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down system...")
        print("✅ System stopped successfully!")

