import time
import threading
from collections import deque
import statistics

class VL53L0XSensor:
    """VL53L0X Time-of-Flight Distance Sensor Wrapper"""
    
    def __init__(self, address=0x29, lane_width_cm=4, name="Sensor"):
        self.address = address
        self.lane_width_cm = lane_width_cm
        self.name = name
        self.baseline_distance = None
        self.threshold_cm = 15
        self.sensor = None
        
        try:
            import board
            import busio
            import adafruit_vl53l0x
            
            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_vl53l0x.VL53L0X(i2c, address=address)
            self.sensor.measurement_timing_budget = 20000  # 20ms for speed
            
            self.calibrate()
            print(f"✅ {self.name} (0x{address:02X}) initialized")
            print(f"   Baseline: {self.baseline_distance:.1f} cm")
            
        except Exception as e:
            print(f"❌ {self.name} (0x{address:02X}) failed: {e}")
            print(f"   Running in simulation mode")
            self.sensor = None
            self.baseline_distance = 100
    
    def calibrate(self, samples=10):
        """Calibrate baseline distance (no vehicle present)"""
        if not self.sensor:
            self.baseline_distance = 100
            return
        
        print(f"🔧 Calibrating {self.name}... (keep lane clear)")
        distances = []
        
        for i in range(samples):
            try:
                dist_cm = self.sensor.range / 10.0
                distances.append(dist_cm)
                time.sleep(0.05)
            except:
                pass
        
        if distances:
            self.baseline_distance = statistics.mean(distances)
            print(f"✅ {self.name} calibrated: {self.baseline_distance:.1f} cm")
        else:
            self.baseline_distance = 100
            print(f"⚠️  {self.name} calibration failed, using default")
    
    def get_distance(self):
        """Get current distance in cm"""
        if not self.sensor:
            return self.baseline_distance
        
        try:
            return self.sensor.range / 10.0
        except:
            return self.baseline_distance
    
    def is_vehicle_present(self):
        """Detect if vehicle is present"""
        distance = self.get_distance()
        if distance is None:
            return False
        
        distance_drop = self.baseline_distance - distance
        return distance_drop > self.threshold_cm


class LaneMonitor:
    """Monitor single traffic lane"""
    
    def __init__(self, name, sensor):
        self.name = name
        self.sensor = sensor
        self.vehicle_count = 0
        self.speed_readings = deque(maxlen=20)
        self.last_vehicle_time = 0
        self.vehicle_present = False
        self.entry_time = None
    
    def update(self):
        """Update lane state - call continuously"""
        current_time = time.time()
        is_present = self.sensor.is_vehicle_present()
        
        # Rising edge: vehicle entered
        if is_present and not self.vehicle_present:
            self.entry_time = current_time
            self.vehicle_present = True
            self.vehicle_count += 1
            self.last_vehicle_time = current_time
            print(f"🚗 {self.name}: Vehicle #{self.vehicle_count} detected")
        
        # Falling edge: vehicle left
        elif not is_present and self.vehicle_present:
            if self.entry_time:
                blocking_time = current_time - self.entry_time
                
                if blocking_time > 0:
                    speed_cms = self.sensor.lane_width_cm / blocking_time
                    speed_kmh = speed_cms * 0.036  # Convert to km/h
                    
                    if 10 <= speed_kmh <= 60:
                        self.speed_readings.append(speed_kmh)
                        print(f"📊 {self.name}: Speed = {speed_kmh:.1f} km/h")
            
            self.vehicle_present = False
            self.entry_time = None
    
    def get_average_speed(self):
        """Get average speed from recent readings"""
        if not self.speed_readings:
            return 0.0
        return statistics.mean(self.speed_readings)
    
    def get_state(self):
        """Get current lane state"""
        return {
            'count': self.vehicle_count,
            'speed': self.get_average_speed()
        }
    
    def reset_count(self):
        """Reset vehicle count"""
        self.vehicle_count = 0


class TrafficController:
    """Main traffic control - Density-based Round-Robin"""
    
    def __init__(self):
        print("\n🔧 Initializing Traffic Controller...")
        
        # Initialize sensors
        sensor_a = VL53L0XSensor(address=0x29, lane_width_cm=4, name="Sensor A")
        sensor_b = VL53L0XSensor(address=0x30, lane_width_cm=4, name="Sensor B")
        
        # Initialize lane monitors
        self.lane_a = LaneMonitor("Lane A", sensor_a)
        self.lane_b = LaneMonitor("Lane B", sensor_b)
        
        # Traffic signal state
        self.current_signal = "RED"
        self.signal_start_time = time.time()
        self.current_lane = 'A'
        
        # Control parameters
        self.min_green_time = 10
        self.max_green_time = 30
        self.idle_timeout = 90
        self.last_activity_time = time.time()
        
        # Threading
        self.running = False
        self.lock = threading.Lock()
        
        print("✅ Traffic Controller initialized")
        print(f"   Green time: {self.min_green_time}-{self.max_green_time}s")
        print(f"   Idle timeout: {self.idle_timeout}s\n")
    
    def calculate_green_time(self, vehicle_count):
        """Calculate green duration: min(10 + 2×count, 30)"""
        green_time = self.min_green_time + (2 * vehicle_count)
        return min(green_time, self.max_green_time)
    
    def update_sensors(self):
        """Update both lane sensors"""
        self.lane_a.update()
        self.lane_b.update()
    
    def control_loop(self):
        """Main traffic control logic"""
        print("🚦 Traffic control loop started\n")
        
        while self.running:
            current_time = time.time()
            
            # Update sensors
            self.update_sensors()
            
            # Track activity
            if (self.lane_a.vehicle_count > 0 or self.lane_b.vehicle_count > 0):
                self.last_activity_time = current_time
            
            # Check idle timeout
            idle_duration = current_time - self.last_activity_time
            if idle_duration > self.idle_timeout:
                if self.current_signal != "RED":
                    print(f"⏸️  Idle timeout - All RED")
                    with self.lock:
                        self.current_signal = "RED"
                time.sleep(0.1)
                continue
            
            # State machine
            if self.current_signal == "RED":
                if self.current_lane == 'A':
                    if self.lane_a.vehicle_count > 0:
                        green_time = self.calculate_green_time(self.lane_a.vehicle_count)
                        with self.lock:
                            self.current_signal = "GREEN_A"
                            self.signal_start_time = current_time
                        print(f"\n🟢 Lane A GREEN for {green_time}s (count: {self.lane_a.vehicle_count})")
                    else:
                        self.current_lane = 'B'
                        print("⏭️  Lane A empty - switching to Lane B")
                
                else:  # Lane B
                    if self.lane_b.vehicle_count > 0:
                        green_time = self.calculate_green_time(self.lane_b.vehicle_count)
                        with self.lock:
                            self.current_signal = "GREEN_B"
                            self.signal_start_time = current_time
                        print(f"\n🟢 Lane B GREEN for {green_time}s (count: {self.lane_b.vehicle_count})")
                    else:
                        self.current_lane = 'A'
                        print("⏭️  Lane B empty - switching to Lane A")
            
            elif self.current_signal == "GREEN_A":
                green_time = self.calculate_green_time(self.lane_a.vehicle_count)
                elapsed = current_time - self.signal_start_time
                
                if elapsed >= green_time:
                    print(f"🔴 Lane A -> RED (served {self.lane_a.vehicle_count} vehicles)")
                    with self.lock:
                        self.current_signal = "RED"
                        self.current_lane = 'B'
                    self.lane_a.reset_count()
            
            elif self.current_signal == "GREEN_B":
                green_time = self.calculate_green_time(self.lane_b.vehicle_count)
                elapsed = current_time - self.signal_start_time
                
                if elapsed >= green_time:
                    print(f"🔴 Lane B -> RED (served {self.lane_b.vehicle_count} vehicles)")
                    with self.lock:
                        self.current_signal = "RED"
                        self.current_lane = 'A'
                    self.lane_b.reset_count()
            
            time.sleep(0.1)
    
    def get_current_state(self):
        """Get system state for dashboard"""
        with self.lock:
            return {
                'laneA': self.lane_a.get_state(),
                'laneB': self.lane_b.get_state(),
                'signal': self.current_signal,
                'timestamp': int(time.time() * 1000)
            }
    
    def start(self):
        """Start traffic controller"""
        self.running = True
        control_thread = threading.Thread(target=self.control_loop, daemon=True)
        control_thread.start()
        print("✅ Traffic controller thread started")
    
    def stop(self):
        """Stop traffic controller"""
        self.running = False
        print("🛑 Traffic controller stopped")


if __name__ == "__main__":
    print("\n🧪 TRAFFIC CONTROLLER TEST MODE\n")
    
    controller = TrafficController()
    controller.start()
    
    print("\n📊 Monitoring traffic (Ctrl+C to stop)...\n")
    
    try:
        while True:
            state = controller.get_current_state()
            
            print(f"\r🚦 Signal: {state['signal']:10s} | " +
                  f"Lane A: {state['laneA']['count']:2d} vehicles, {state['laneA']['speed']:5.1f} km/h | " +
                  f"Lane B: {state['laneB']['count']:2d} vehicles, {state['laneB']['speed']:5.1f} km/h",
                  end='', flush=True)
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Test stopped")
        controller.stop()
        print("✅ Done\n")
