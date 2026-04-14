import pygame
import paho.mqtt.client as mqtt
import json
import time
import traceback

# --- 設定 ---
WSL_IP = "127.0.0.1" 
MQTT_PORT = 1884  # VSCodeのポート転送に合わせる
MQTT_TOPIC = "robot/joystick"

# Pygameの初期化
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("コントローラーが見つかりません。")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"使用デバイス: {joystick.get_name()}")

# MQTTの初期化と接続
try:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    print(f"接続を試みています: {WSL_IP}:{MQTT_PORT}...")
    client.connect(WSL_IP, MQTT_PORT, keepalive=5)
    print("接続に成功しました！")
except Exception as e:
    print(f"MQTTの準備中にエラーが発生しました: {e}")
    traceback.print_exc()
    exit()

print("送信開始... (10Hz / QoS 0) [Ctrl+Cで終了]")

try:
    while True:
        pygame.event.pump()
        
        # データの整理
        data = {
           "axes": [round(joystick.get_axis(i), 3) for i in range(joystick.get_numaxes())],
           "buttons": [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
        }
        
        payload = json.dumps(data)
        client.publish(MQTT_TOPIC, payload, qos=0)
        
        print(f"Sent: {payload}")
        time.sleep(0.1) # 10Hz
        
except KeyboardInterrupt:
    print("\nユーザーにより終了されました。")
finally:
    pygame.quit()