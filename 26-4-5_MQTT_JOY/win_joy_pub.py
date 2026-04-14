import pygame
import paho.mqtt.client as mqtt
import json
import time

# --- 設定 ---
WSL_IP = "127.0.0.1" 
MQTT_PORT = 1884  # VSCodeのポート転送に合わせた番号
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

# MQTTの初期化
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

try:
    # keepaliveを短くして接続の鮮度を保つ
    client.connect(WSL_IP, MQTT_PORT, keepalive=5)
except Exception as e:
    print(f"接続失敗: {e}")
    exit()

print("送信開始... (10Hz / QoS 0)")

try:
    while True:
        pygame.event.pump()
        
        # データの整理
        data = {
           "axes": [round(joystick.get_axis(i), 3) for i in range(joystick.get_numaxes())],
           "buttons": [joystick.get_button(i) for i in range(joystick.get_numbuttons())],
           "hats": joystick.get_hat(0) if joystick.get_numhats() > 0 else (0, 0)
        }
        
        # payloadを変数に入れて重複処理を回避
        payload = json.dumps(data)
        
        # QoS=0 (送りっぱなし) にして速度優先
        client.publish(MQTT_TOPIC, payload, qos=0)
        
        print(f"Sent: {payload}")
        
        # 送信頻度を 10Hz (0.1秒) に落として渋滞を防止
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n終了します。")
finally:
    pygame.quit()