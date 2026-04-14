import paho.mqtt.client as mqtt
import json
import time

# --- 設定 ---
# ロボット側スクリプトが動いているPCのIP（同じPC内なら localhost）
ROBOT_IP = "localhost" 

def send_to_robot(command_type, action):
    """
    ここでロボット制御側に命令を飛ばします。
    ※今回は最も確実な「MQTT経由でロボット側スクリプトに直接書き込ませる」
    方法を想定しています。
    """
    print(f"[Bridge] 命令送信: {action}")

def on_message(client, userdata, msg):
    try:
        # Windowsから届いたJSONを解析
        data = json.loads(msg.payload.decode())
        axes = data.get("axes", [])
        buttons = data.get("buttons", [])

        # スティックの倒し具合で判定 (F710: axes[1]が前後, axes[0]が左右)
        if len(axes) > 1:
            ly = axes[1]
            lx = axes[0]
            
            if ly < -0.5:
                send_to_robot("cmd", "forward")
            elif ly > 0.5:
                send_to_robot("cmd", "backward")
            elif lx < -0.5:
                send_to_robot("cmd", "left")
            elif lx > 0.5:
                send_to_robot("cmd", "right")
            else:
                send_to_robot("cmd", "stop")

    except Exception as e:
        print(f"データ解析エラー: {e}")

# --- MQTT Setup ---
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

print("=== Joystick Bridge Node 起動中 ===")
try:
    client.connect("localhost", 1884, 60)
    client.subscribe("robot/joystick")
    print("MQTTブローカーに接続完了。ジョイスティック信号を待機しています...")
    client.loop_forever()
except Exception as e:
    print(f"接続失敗: {e}")