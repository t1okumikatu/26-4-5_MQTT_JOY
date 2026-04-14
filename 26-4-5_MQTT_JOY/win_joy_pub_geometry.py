import pygame, mqtt_client_setup_here, json, time
import paho.mqtt.client as mqtt

WSL_IP, MQTT_PORT, MQTT_TOPIC = "127.0.0.1", 1884, "robot/joystick"
pygame.init()
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.connect(WSL_IP, MQTT_PORT)

while True:
    pygame.event.pump()
    data = {"x": round(joystick.get_axis(0), 3), "y": round(joystick.get_axis(1), 3)}
    client.publish(MQTT_TOPIC, json.dumps(data))
    print(f"Sent: {data}")
    time.sleep(0.1)
