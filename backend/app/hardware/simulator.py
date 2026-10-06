import time
import math
import random
import logging
import argparse
import httpx
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [SIMULATOR] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("hardware_simulator")

class AgriHardwareSimulator:
    def __init__(self, target_url: str = "http://localhost:8000/api/sensors/data", device_id: str = "AGRI-DEV-001", interval: float = 3.0):
        self.target_url = target_url
        self.device_id = device_id
        self.interval = interval
        self.step = 0
        
        # State variables for realistic physics simulation
        self.soil_moisture = 28.5  # Start near borderline for demonstration
        self.water_level = 78.0
        self.is_pumping = False

    def generate_telemetry_batch(self):
        self.step += 1
        t = self.step * 0.1

        # Diurnal temperature cycle: peaks at 34.5°C, drops to 24°C
        temp = 28.0 + 5.5 * math.sin(t * 0.5) + random.uniform(-0.4, 0.4)
        
        # Humidity inversely proportional to temperature
        humidity = 68.0 - 15.0 * math.sin(t * 0.5) + random.uniform(-1.0, 1.0)
        humidity = max(35.0, min(95.0, humidity))

        # Solar Lux
        lux = max(0.0, 750.0 + 400.0 * math.sin(t * 0.5) + random.uniform(-30.0, 30.0))

        # Soil moisture evaporation & occasional watering cycle
        if self.soil_moisture < 23.0:
            self.is_pumping = True
        elif self.soil_moisture > 62.0:
            self.is_pumping = False

        if self.is_pumping:
            self.soil_moisture += 3.2
            self.water_level = max(10.0, self.water_level - 1.5)
        else:
            self.soil_moisture -= random.uniform(0.3, 0.7)

        self.soil_moisture = round(max(15.0, min(85.0, self.soil_moisture)), 1)
        temp = round(temp, 1)
        humidity = round(humidity, 1)
        lux = round(lux, 1)
        water = round(self.water_level, 1)

        now_iso = datetime.now(timezone.utc).isoformat()

        readings = [
            {
                "device_id": self.device_id,
                "sensor_id": f"{self.device_id}-SOIL",
                "sensor_type": "soil_moisture",
                "value": self.soil_moisture,
                "unit": "%",
                "timestamp": now_iso,
                "location": "Greenhouse Sector A - Root Zone",
                "metadata": {"depth_cm": 15, "state": "irrigating" if self.is_pumping else "depleting"}
            },
            {
                "device_id": self.device_id,
                "sensor_id": f"{self.device_id}-TEMP",
                "sensor_type": "temperature",
                "value": temp,
                "unit": "°C",
                "timestamp": now_iso,
                "location": "Canopy Level Sensor",
                "metadata": {"ambient": True}
            },
            {
                "device_id": self.device_id,
                "sensor_id": f"{self.device_id}-HUMID",
                "sensor_type": "humidity",
                "value": humidity,
                "unit": "%",
                "timestamp": now_iso,
                "location": "Canopy Level Sensor",
                "metadata": {}
            },
            {
                "device_id": self.device_id,
                "sensor_id": f"{self.device_id}-LIGHT",
                "sensor_type": "light_lux",
                "value": lux,
                "unit": "lux",
                "timestamp": now_iso,
                "location": "Roof PAR Sensor",
                "metadata": {}
            },
            {
                "device_id": self.device_id,
                "sensor_id": f"{self.device_id}-WATER",
                "sensor_type": "water_level_pct",
                "value": water,
                "unit": "%",
                "timestamp": now_iso,
                "location": "Subsurface Irrigation Tank",
                "metadata": {}
            }
        ]
        return readings

    def run(self):
        logger.info(f"Starting Agrikural IoT Hardware Simulator for Device '{self.device_id}'")
        logger.info(f"Transmitting to: {self.target_url} every {self.interval}s")
        
        with httpx.Client(timeout=5.0) as client:
            while True:
                readings = self.generate_telemetry_batch()
                for reading in readings:
                    try:
                        resp = client.post(self.target_url, json=reading)
                        if resp.status_code == 201:
                            pass
                        else:
                            logger.warning(f"HTTP {resp.status_code}: {resp.text}")
                    except Exception as e:
                        logger.error(f"Failed to transmit telemetry to backend: {e}")
                
                # Log status summary
                logger.info(
                    f"[{self.device_id}] Transmitted: Soil Moisture={self.soil_moisture}% | "
                    f"Temp={readings[1]['value']}°C | Humid={readings[2]['value']}% | Tank={self.water_level}%"
                )
                time.sleep(self.interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agrikural Hardware Sensor Simulator")
    parser.add_argument("--url", default="http://localhost:8000/api/sensors/data", help="Target API endpoint")
    parser.add_argument("--device", default="AGRI-DEV-001", help="Device ID")
    parser.add_argument("--interval", type=float, default=3.0, help="Transmission interval in seconds")
    args = parser.parse_args()

    simulator = AgriHardwareSimulator(target_url=args.url, device_id=args.device, interval=args.interval)
    simulator.run()
