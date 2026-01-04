
import cv2
import threading
import time
import numpy as np
from datetime import datetime

class CameraStream:
    """
    Camera streaming class with automatic camera detection
    Optimized for low-resource devices like Raspberry Pi Zero 2W
    """
    
    def __init__(self, resolution=(640, 480), fps=15, jpeg_quality=70):
        """
        Initialize camera stream
        
        Args:
            resolution: Tuple (width, height) - Default (640, 480)
            fps: Target frames per second - Default 15
            jpeg_quality: JPEG compression 0-100 - Default 70
        """
        self.resolution = resolution
        self.fps = fps
        self.jpeg_quality = jpeg_quality
        
        # Thread-safe frame storage
        self.frame = None
        self.lock = threading.Lock()
        
        # Camera objects
        self.camera = None
        self.camera_type = None
        self.is_running = True
        
        # Display initialization info
        print("\n" + "="*70)
        print("📹 CAMERA STREAM INITIALIZATION")
        print("="*70)
        print(f"Resolution:    {resolution[0]} x {resolution[1]}")
        print(f"Target FPS:    {fps}")
        print(f"JPEG Quality:  {jpeg_quality}%")
        print("="*70 + "\n")
        
        # Try to initialize camera
        self._initialize_camera()
    
    def _initialize_camera(self):
        """
        Auto-detect and initialize available camera
        Priority: Pi Camera → USB Camera → Simulation
        """
        
        # ═══════════════════════════════════════════════════════════════════
        # OPTION 1: Raspberry Pi Camera Module (Recommended)
        # ═══════════════════════════════════════════════════════════════════
        try:
            from picamera2 import Picamera2
            
            print("🔍 Attempting Pi Camera initialization...")
            
            # Create camera instance
            self.camera = Picamera2()
            
            # Configure camera with our desired settings
            camera_config = self.camera.create_preview_configuration(
                main={
                    "size": self.resolution,
                    "format": "RGB888"  # 24-bit RGB
                }
            )
            
            # Apply configuration
            self.camera.configure(camera_config)
            
            # Start camera
            self.camera.start()
            
            # Wait for camera to stabilize
            print("   Warming up camera...")
            time.sleep(2)
            
            # Set camera type
            self.camera_type = "picamera2"
            
            print("✅ Pi Camera initialized successfully!")
            print(f"   Camera Type: Raspberry Pi Camera Module")
            print(f"   Interface:   CSI (Camera Serial Interface)")
            print("")
            
            # Start capture thread
            capture_thread = threading.Thread(
                target=self._capture_picamera,
                daemon=True,
                name="PiCameraThread"
            )
            capture_thread.start()
            
            return  # Success - exit function
        
        except ImportError:
            print("⚠️  picamera2 library not installed")
            print("   Install: pip3 install picamera2\n")
        
        except Exception as e:
            print(f"⚠️  Pi Camera initialization failed: {e}")
            print("   Check: Camera enabled in raspi-config")
            print("   Check: Camera cable connected properly\n")
        
        # ═══════════════════════════════════════════════════════════════════
        # OPTION 2: USB Webcam (Fallback)
        # ═══════════════════════════════════════════════════════════════════
        try:
            print("🔍 Attempting USB camera initialization...")
            
            # Try to open video device 0
            self.camera = cv2.VideoCapture(0)
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                raise Exception("Unable to open camera device")
            
            # Configure camera settings
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Reduce buffer size for lower latency
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Set camera type
            self.camera_type = "opencv"
            
            print("✅ USB Camera initialized successfully!")
            print(f"   Camera Type: USB Webcam")
            print(f"   Interface:   USB Video Device")
            print("")
            
            # Start capture thread
            capture_thread = threading.Thread(
                target=self._capture_opencv,
                daemon=True,
                name="USBCameraThread"
            )
            capture_thread.start()
            
            return  # Success - exit function
        
        except Exception as e:
            print(f"⚠️  USB camera initialization failed: {e}")
            print("   Check: USB camera connected")
            print("   Check: Camera permissions\n")
        
        # ═══════════════════════════════════════════════════════════════════
        # OPTION 3: Simulation Mode (No Hardware)
        # ═══════════════════════════════════════════════════════════════════
        print("⚠️  NO CAMERA AVAILABLE")
        print("   Running in SIMULATION MODE")
        print("   Dashboard will show placeholder frames\n")
        
        self.camera = None
        self.camera_type = "simulation"
        
        # Start simulation thread
        simulation_thread = threading.Thread(
            target=self._generate_simulation,
            daemon=True,
            name="SimulationThread"
        )
        simulation_thread.start()
    
    def _capture_picamera(self):
        """
        Capture loop for Raspberry Pi Camera
        Runs in separate thread
        """
        print("🎥 Pi Camera capture thread started")
        
        frame_interval = 1.0 / self.fps
        frame_count = 0
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Capture frame from camera
                frame = self.camera.capture_array()
                
                # Add visual overlays
                frame = self._add_overlays(frame)
                
                # Store frame (thread-safe)
                with self.lock:
                    self.frame = frame.copy()
                
                frame_count += 1
                
                # Maintain target FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
            
            except Exception as e:
                print(f"⚠️  Pi Camera capture error: {e}")
                time.sleep(0.5)
        
        print(f"🛑 Pi Camera thread stopped (captured {frame_count} frames)")
    
    def _capture_opencv(self):
        """
        Capture loop for USB camera via OpenCV
        Runs in separate thread
        """
        print("🎥 USB camera capture thread started")
        
        frame_interval = 1.0 / self.fps
        frame_count = 0
        
        while self.is_running and self.camera and self.camera.isOpened():
            try:
                start_time = time.time()
                
                # Read frame from camera
                ret, frame = self.camera.read()
                
                if not ret:
                    print("⚠️  Failed to read frame")
                    time.sleep(0.5)
                    continue
                
                # Resize if needed
                if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
                    frame = cv2.resize(frame, self.resolution)
                
                # Add visual overlays
                frame = self._add_overlays(frame)
                
                # Store frame (thread-safe)
                with self.lock:
                    self.frame = frame.copy()
                
                frame_count += 1
                
                # Maintain target FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
            
            except Exception as e:
                print(f"⚠️  USB camera capture error: {e}")
                time.sleep(0.5)
        
        print(f"🛑 USB camera thread stopped (captured {frame_count} frames)")
    
    def _generate_simulation(self):
        """
        Generate simulation frames when no camera available
        Runs in separate thread
        """
        print("🎨 Simulation mode active - generating placeholder frames")
        
        frame_interval = 1.0 / self.fps
        frame_count = 0
        
        while self.is_running:
            try:
                # Create black background
                frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
                
                # Add simulation text
                cv2.putText(
                    frame,
                    "SIMULATION MODE",
                    (self.resolution[0]//2 - 200, self.resolution[1]//2 - 50),
                    cv2.FONT_HERSHEY_BOLD,
                    1.2,
                    (0, 255, 255),
                    2
                )
                
                cv2.putText(
                    frame,
                    "No Camera Connected",
                    (self.resolution[0]//2 - 150, self.resolution[1]//2 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    1
                )
                
                # Add instructions
                cv2.putText(
                    frame,
                    "Connect Pi Camera or USB Camera",
                    (self.resolution[0]//2 - 180, self.resolution[1]//2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (150, 150, 150),
                    1
                )
                
                # Add timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(
                    frame,
                    timestamp,
                    (10, self.resolution[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1
                )
                
                # Store frame (thread-safe)
                with self.lock:
                    self.frame = frame.copy()
                
                frame_count += 1
                
                time.sleep(frame_interval)
            
            except Exception as e:
                print(f"⚠️  Simulation error: {e}")
                time.sleep(0.5)
        
        print(f"🛑 Simulation thread stopped (generated {frame_count} frames)")
    
    def _add_overlays(self, frame):
        """
        Add text and graphics overlays to frame
        
        Args:
            frame: Input frame (numpy array)
        
        Returns:
            Frame with overlays added
        """
        # Convert BGR to RGB if using OpenCV camera
        if self.camera_type == "opencv":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            timestamp,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        # Add "LIVE" indicator
        cv2.putText(
            frame,
            "LIVE",
            (10, 65),
            cv2.FONT_HERSHEY_BOLD,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )
        
        # Add recording indicator (red circle)
        cv2.circle(
            frame,
            (self.resolution[0] - 30, 30),
            10,
            (0, 0, 255),
            -1
        )
        
        # Add camera type indicator
        camera_label = {
            "picamera2": "Pi Camera",
            "opencv": "USB Camera",
            "simulation": "Simulation"
        }.get(self.camera_type, "Unknown")
        
        cv2.putText(
            frame,
            camera_label,
            (10, self.resolution[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
            cv2.LINE_AA
        )
        
        return frame
    
    def get_frame(self):
        """
        Get current frame (thread-safe)
        
        Returns:
            Current frame as numpy array, or None if unavailable
        """
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return None
    
    def generate_frames(self):
        """
        Generator function for MJPEG streaming
        Used by Flask to stream video to web browsers
        
        Yields:
            Bytes in multipart MJPEG format
        """
        print("📡 MJPEG stream started")
        
        frame_interval = 1.0 / self.fps
        stream_count = 0
        
        while True:
            try:
                # Get current frame
                frame = self.get_frame()
                
                # Generate placeholder if no frame available
                if frame is None:
                    frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
                    cv2.putText(
                        frame,
                        "Waiting for camera...",
                        (self.resolution[0]//2 - 150, self.resolution[1]//2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2
                    )
                
                # Convert RGB to BGR for JPEG encoding (OpenCV requirement)
                if self.camera_type == "picamera2":
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Encode frame as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                if not ret:
                    print("⚠️  Failed to encode frame")
                    time.sleep(0.1)
                    continue
                
                # Convert to bytes
                frame_bytes = buffer.tobytes()
                
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                stream_count += 1
                
                # Control streaming rate
                time.sleep(frame_interval)
            
            except GeneratorExit:
                print(f"📡 MJPEG stream closed (streamed {stream_count} frames)")
                break
            
            except Exception as e:
                print(f"⚠️  Streaming error: {e}")
                time.sleep(0.5)
    
    def release(self):
        """
        Release camera resources and stop threads
        """
        print("\n🛑 Releasing camera resources...")
        
        self.is_running = False
        
        if self.camera:
            if self.camera_type == "opencv":
                self.camera.release()
            elif self.camera_type == "picamera2":
                self.camera.stop()
        
        print("✅ Camera released successfully\n")


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE TEST MODE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Test camera stream independently
    Run: python3 camera_stream.py
    """
    
    print("\n" + "="*70)
    print("🧪 CAMERA STREAM - STANDALONE TEST MODE")
    print("="*70)
    print("This will test camera capture without the full system")
    print("Press Ctrl+C to stop")
    print("="*70 + "\n")
    
    # Create camera stream instance
    camera = CameraStream(
        resolution=(640, 480),
        fps=15,
        jpeg_quality=70
    )
    
    print("\n📸 Capturing frames...\n")
    print("Metrics will be displayed below:")
    print("-" * 70)
    
    try:
        frame_count = 0
        start_time = time.time()
        last_print = start_time
        
        while True:
            # Get frame
            frame = camera.get_frame()
            
            if frame is not None:
                frame_count += 1
                
                # Update metrics every second
                current_time = time.time()
                if current_time - last_print >= 1.0:
                    elapsed = current_time - start_time
                    actual_fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    print(f"\r📊 Frames: {frame_count:6d} | "
                          f"FPS: {actual_fps:5.1f} | "
                          f"Resolution: {frame.shape[1]}x{frame.shape[0]} | "
                          f"Type: {camera.camera_type:12s}",
                          end='', flush=True)
                    
                    last_print = current_time
            
            time.sleep(0.01)  # Small delay to prevent CPU overload
    
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("🛑 Test stopped by user")
        print("="*70)
        
        # Calculate final statistics
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        
        print(f"\n📊 Final Statistics:")
        print(f"   Total Frames:  {frame_count}")
        print(f"   Total Time:    {total_time:.1f} seconds")
        print(f"   Average FPS:   {avg_fps:.2f}")
        print(f"   Camera Type:   {camera.camera_type}")
        
        # Release camera
        camera.release()
        
        print("\n✅ Test completed successfully\n")

