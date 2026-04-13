
import pygame
import paho.mqtt.client as mqtt
import json
import time

# --- 設定 ---
# WSL2のIPアドレス (先ほどのエラーに出ていたIP、または 'localhost' で試行)
WSL_IP = "127.0.0.1" 
MQTT_TOPIC = "robot/joystick"

# Pygameの初期化
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("コントローラーが見つかりません。接続を確認してください。")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"使用デバイス: {joystick.get_name()}")

# MQTTの初期化
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

try:
     client.connect(WSL_IP, 1883, 60)
except Exception as e:
    print(f"WSL2のMQTTブローカーに接続できません: {e}")
    exit()

print("送信開始... (Ctrl+Cで終了)")

try:
    while True:
        pygame.event.pump()
        
        # 主要なデータを辞書形式でまとめる
        data = {
           "axes": [round(joystick.get_axis(i), 3) for i in range(joystick.get_numaxes())],
           "buttons": [joystick.get_button(i) for i in range(joystick.get_numbuttons())],
            "hats": joystick.get_hat(0) if joystick.get_numhats() > 0 else (0, 0)
        }
        
        # JSONとして送信
        payload = json.dumps(data)
        client.publish(MQTT_TOPIC, payload)
        
        # --- ここを追加 ---
        print(f"Sent: {payload}") 
        # ------------------
        
        # 送信頻度 (20Hz = 0.05秒)
        time.sleep(0.05)
        
except KeyboardInterrupt:
    print("\n終了します。")
finally:
    pygame.quit()