import pygame
import paho.mqtt.client as mqtt
import json
import time

# --- 設定 ---
WSL_IP = "127.0.0.1" 
MQTT_PORT = 1884  # VSCodeポート転送に合わせて1884
MQTT_TOPIC = "robot/joystick"

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("Error: No joystick connected.")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Joystick detected: {joystick.get_name()}")

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
try:
    client.connect(WSL_IP, MQTT_PORT, 60)
    print(f"Connected to MQTT at {WSL_IP}:{MQTT_PORT}")
except Exception as e:
    print(f"Connect failed: {e}")
    exit()

print("Geometry Publishing Started (10Hz) [Ctrl+C to Stop]")

try:
    while True:
        pygame.event.pump()
        
        # ジオメトリ制御用にアナログスティックの値を送信
        data = {
           "x": round(joystick.get_axis(0), 3),
           "y": round(joystick.get_axis(1), 3)
        }
        
        payload = json.dumps(data)
        client.publish(MQTT_TOPIC, payload, qos=0)
        
        print(f"Sent: X={data['x']}, Y={data['y']}")
        time.sleep(0.1) 
        
except KeyboardInterrupt:
    print("Stopped.")
finally:
    pygame.quit()