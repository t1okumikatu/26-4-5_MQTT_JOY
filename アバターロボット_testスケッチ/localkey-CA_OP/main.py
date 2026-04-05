import threading
import json
import asyncio
import websockets
from pykeigan import usbcontroller
from rplidar import RPLidar  # RPLiDAR用ライブラリ

# --- 設定項目 ---
OFFICIAL_WS_URL = "wss://avatarchallenge.ca-platform.org/ws"
ROBOT_ID = "keigan1-ca001"
TOKEN = "YOUR_TOKEN_HERE"
LOCAL_WS_PORT = 8080

# LiDARの接続ポート (Windowsなら 'COM3', Linuxなら '/dev/ttyUSB1' など)
LIDAR_PORT = '/dev/ttyUSB1' 

# 安全距離 (mm単位)
STOP_DISTANCE = 300 

# --- グローバル変数 ---
obstacle_detected = False

# --- KeiganMotor設定 ---
dev = usbcontroller.USBController('/dev/ttyUSB0')
dev.enable()

def move_robot(v, a):
    global obstacle_detected
    
    # 安全装置：前方に障害物があり、かつ前進(v > 0)しようとしている場合は停止
    if obstacle_detected and v > 0:
        print("⚠️ Obstacle Detected! Safety Stop.")
        v = 0
        a = 0
        
    speed_l = v + a
    speed_r = -(v - a)
    dev.set_speed(speed_l, 0)
    dev.set_speed(speed_r, 1)
    dev.run_forward(0)
    dev.run_forward(1)

# --- LiDAR スキャン用スレッド ---
def lidar_monitor_thread():
    global obstacle_detected
    lidar = RPLidar(LIDAR_PORT)
    print(f"LiDAR started on {LIDAR_PORT}")
    
    try:
        for scan in lidar.iter_scans():
            found_near = False
            for (_, angle, distance) in scan:
                # 前方方向（例：330度〜30度）かつ一定距離以内を監視
                if (angle < 30 or angle > 330) and (0 < distance < STOP_DISTANCE):
                    found_near = True
                    break
            
            obstacle_detected = found_near
            
    except Exception as e:
        print(f"LiDAR Error: {e}")
    finally:
        lidar.stop()
        lidar.disconnect()

# --- A. 公式サーバー接続 (映像・音声維持用) ---
async def official_server_loop():
    async with websockets.connect(OFFICIAL_WS_URL) as ws:
        auth_msg = {"type": "login", "id": ROBOT_ID, "token": TOKEN}
        await ws.send(json.dumps(auth_msg))
        print("Connected to Official Server (Video Active)")
        while True:
            await ws.recv() # 受信維持

# --- B. ローカル操作パネル (OPスケッチ) との通信 ---
async def local_op_handler(websocket, path):
    async for message in websocket:
        try:
            data = json.loads(message)
            v = data.get("v", 0)
            a = data.get("a", 0)
            move_robot(v, a)
        except Exception as e:
            print(f"Command Error: {e}")

def start_local_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(local_op_handler, "0.0.0.0", LOCAL_WS_PORT)
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == "__main__":
    # 1. LiDAR監視をバックグラウンドで開始
    t_lidar = threading.Thread(target=lidar_monitor_thread, daemon=True)
    t_lidar.start()

    # 2. ローカルサーバーを別スレッドで開始
    t_local = threading.Thread(target=start_local_server, daemon=True)
    t_local.start()

    # 3. メインスレッドで公式接続を維持
    try:
        asyncio.run(official_server_loop())
    except KeyboardInterrupt:
        dev.stop_motors()
        print("Safety Shutdown.")