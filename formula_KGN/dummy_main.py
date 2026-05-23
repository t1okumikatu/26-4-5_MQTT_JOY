# -*- coding: utf-8 -*-
import sys
import os
import math
import threading
import requests
import yaml
from time import sleep, time
import tkinter as tk
import json

# --- 追加ライブラリ (MQTT & ROS 2) ---
import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy
import websocket
from enum import Enum, auto

# ==========================================
# 実機がない環境用のダミーロボットクラス
# ==========================================
class MockRobot:
    def __init__(self):
        print("!!!! Mock Mode: Robot Initialized (No Hardware) !!!!")
    def enable(self): pass
    def disable(self): pass
    def run_straight(self, rpm): print(f"Mock: Straight {rpm:.1f} RPM")
    def run_pivot_turn(self, rpm): print(f"Mock: Turn {rpm:.1f} RPM")
    def run_stop(self): print("Mock: Stop")
    def run(self, l, r): print(f"Mock: Dual Motor Left:{l:.1f}, Right:{r:.1f}")

class RobotCmd(Enum):
    DISABLE = auto()
    RUN_FORWARD = auto()
    RUN_BACKWARD = auto()
    RUN_FORWARD_LEFT = auto()
    RUN_FORWARD_RIGHT = auto()
    RUN_BACKWARD_LEFT = auto()
    RUN_BACKWARD_RIGHT = auto()
    RUN_TURN_LEFT = auto()
    RUN_TURN_RIGHT = auto()
    RUN_RPM = auto()
    RUN_STOP = auto()

class RobotController(Node):
    def __init__(self):
        super().__init__('robot_controller')
        self.load_config()
        
        self.robot_cmd = RobotCmd.DISABLE
        self.robot_speed_rpm = 2000 # ROBOT_SPEED_RPM_HIGH
        self.rpm_left = 0
        self.rpm_right = 0
        self.last_ws_data_time = 0
        self.is_ws_connected = False
        self.watchdog_count = 0
        self.WATCHDOG_COUNT_MAX = 20 # 通信途絶判定(秒換算で調整)
        
        self.in_zone_1 = self.in_zone_2 = self.in_zone_3 = False
        self.closest_distance = None

        # ロボット初期化（モックモード固定）
        self.robot = MockRobot()
        self.robot.enable()

        # GUIのセットアップ (CUI環境時は自動でスキップされる安全設計)
        self.setup_gui()

        # --- MQTT受信設定 (Windowsジョイスティック用) ---
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_message = self.on_mqtt_message
        try:
            self.mqtt_client.connect("localhost", 1883, 60)
            self.mqtt_client.subscribe("robot/joystick")
            threading.Thread(target=self.mqtt_client.loop_forever, daemon=True).start()
            print(">>> MQTT Joystick Receiver: Started (Listening on localhost:1883)")
        except Exception as e:
            print(f"MQTT Connection failed: {e}")

        # --- ROS 2 通信設定 ---
        qos_profile = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=10)
        self.subscription = self.create_subscription(LaserScan, '/scan', self.lidar_callback, qos_profile)
        
        # ロボット用タイマーループ (0.05秒間隔)
        self.create_timer(0.05, self.robot_loop)

    def on_mqtt_message(self, client, userdata, msg):
        """MQTT経由でジョイスティックデータ(axes)を受信した際の処理"""
        try:
            payload = json.loads(msg.payload.decode())
            axes = payload.get("axes", [])
            
            if len(axes) > 1:
                lx = axes[0] # 左右アナログスティック入力
                ly = axes[1] # 前後アナログスティック入力
                
                # デバッグ表示: データを受信したら常に生の値を表示
                print(f"[{time():.2f}] MQTT Recv -> lx: {lx:.4f}, ly: {ly:.4f}")
                
                # 不感帯（Windows側の微小なブレをカットし、小さな入力も拾うしきい値）
                THRESHOLD = 0.002
                
                # オリジナルmain.pyの全コマンドにマッピング（斜め入力対応）
                if ly < -THRESHOLD and abs(lx) <= THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_FORWARD
                elif ly > THRESHOLD and abs(lx) <= THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_BACKWARD
                elif ly < -THRESHOLD and lx < -THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_FORWARD_LEFT
                elif ly < -THRESHOLD and lx > THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_FORWARD_RIGHT
                elif ly > THRESHOLD and lx < -THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_BACKWARD_LEFT
                elif ly > THRESHOLD and lx > THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_BACKWARD_RIGHT
                elif abs(ly) <= THRESHOLD and lx < -THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_TURN_LEFT
                elif abs(ly) <= THRESHOLD and lx > THRESHOLD:
                    self.robot_cmd = RobotCmd.RUN_TURN_RIGHT
                else:
                    self.robot_cmd = RobotCmd.RUN_STOP
                
                # コマンド受信に成功したためウォッチドッグをリセット
                self.watchdog_count = 0
                
        except Exception as e:
            print(f"MQTT Error: {e}")

    def lidar_callback(self, msg):
        self.in_zone_1 = self.in_zone_2 = self.in_zone_3 = False
        angle = msg.angle_min
        for r in msg.ranges:
            if 0.0 < r < float('inf'):
                x = r * math.cos(angle)
                y = r * math.sin(angle)
                if x > 0:
                    if x <= 0.2 and abs(y) <= 0.25:  self.in_zone_3 = True
                    if x <= 0.5 and abs(y) <= 0.25:  self.in_zone_2 = True
                    if x <= 1.0 and abs(y) <= 0.5:   self.in_zone_1 = True
            angle += msg.angle_increment

    def robot_loop(self):
        # 安全装置: 通信が途絶えたら自動停止
        if self.watchdog_count > self.WATCHDOG_COUNT_MAX:
            if self.robot_cmd != RobotCmd.DISABLE:
                print("⚠️ Watchdog timeout: No signal received. Stopping robot.")
                self.robot.run_stop()
                self.robot_cmd = RobotCmd.DISABLE
            return

        # 障害物検知時の自動減速・自動停止ロジック (オリジナルmain.py準拠)
        is_forward_movement = self.robot_cmd in [
            RobotCmd.RUN_FORWARD, RobotCmd.RUN_FORWARD_LEFT, 
            RobotCmd.RUN_FORWARD_RIGHT, RobotCmd.RUN_TURN_LEFT, RobotCmd.RUN_TURN_RIGHT
        ]

        if is_forward_movement and self.in_zone_3:
            print("🛑 Lidar Hazard: Zone 3 Obstacle! Emergency Stop.")
            self.robot.run_stop()
            self.robot_cmd = RobotCmd.DISABLE
        else:
            self.execute_robot_command()
        
        self.watchdog_count += 1

    def execute_robot_command(self):
        # 障害物ゾーンによる速度変調
        speed = self.robot_speed_rpm
        if self.in_zone_2:
            speed *= 0.2
        elif self.in_zone_1:
            speed *= 0.4
        
        if self.robot_cmd == RobotCmd.DISABLE: 
            return

        # 各コマンドのモック動作出力
        if self.robot_cmd == RobotCmd.RUN_FORWARD:
            self.robot.run_straight(speed)
        elif self.robot_cmd == RobotCmd.RUN_BACKWARD:
            self.robot.run_straight(-self.robot_speed_rpm / 2)
        elif self.robot_cmd == RobotCmd.RUN_FORWARD_LEFT:
            self.robot.run(speed / 2, speed)
        elif self.robot_cmd == RobotCmd.RUN_FORWARD_RIGHT:
            self.robot.run(speed, speed / 2)
        elif self.robot_cmd == RobotCmd.RUN_BACKWARD_LEFT:
            self.robot.run(-self.robot_speed_rpm / 2, -self.robot_speed_rpm)
        elif self.robot_cmd == RobotCmd.RUN_BACKWARD_RIGHT:
            self.robot.run(-self.robot_speed_rpm, -self.robot_speed_rpm / 2)
        elif self.robot_cmd == RobotCmd.RUN_TURN_LEFT:
            self.robot.run_pivot_turn(-speed / 2)
        elif self.robot_cmd == RobotCmd.RUN_TURN_RIGHT:
            self.robot.run_pivot_turn(speed / 2)
        elif self.robot_cmd == RobotCmd.RUN_STOP:
            self.robot.run_stop()
            self.robot_cmd = RobotCmd.DISABLE
        elif self.robot_cmd == RobotCmd.RUN_RPM:
            self.robot.run(self.rpm_left, self.rpm_right)

    def load_config(self):
        # 設定ファイル読み込みのフォールバック
        config_file_path = 'config.yaml'
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as file:
                config = yaml.safe_load(file)
            frontal_angle_degrees = config['lidar'].get('frontal_angle_degrees', 90)
        else:
            frontal_angle_degrees = 90
        self.half_frontal_angle_radians = math.radians(frontal_angle_degrees) / 2

    def setup_gui(self):
        try:
            self.root = tk.Tk()
            self.root.title("Control (Mock Mode)")
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
            self.gui_enabled = True
        except Exception as e:
            self.root = None
            self.gui_enabled = False

    def login_and_connect(self):
        def task():
            try:
                url = 'https://api.avatarchallenge.ca-platform.org/clientLogin/?name=keigan1-ca001&password=eiCa7too&code=keigan1'
                resp = requests.post(url, timeout=5)
                self.info = resp.json()
                self.connect_ws()
            except Exception as e:
                sleep(5)
                self.login_and_connect()
        threading.Thread(target=task, daemon=True).start()

    def connect_ws(self):
        token = self.info['authorisation']['token']
        self.ws = websocket.WebSocketApp(
            f'wss://ws.avatarchallenge.ca-platform.org?token={token}',
            on_message=self.on_ws_message,
            on_open=lambda *args: setattr(self, 'is_ws_connected', True),
            on_close=lambda *args: setattr(self, 'is_ws_connected', False)
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def on_ws_message(self, ws, message):
        ret = message.split(';')
        if len(ret) > 3 and ret[0] == "cmd" and ret[1] == "robot":
            if ret[2] == "run":
                if ret[3] == "forward": self.robot_cmd = RobotCmd.RUN_FORWARD
                elif ret[3] == "backward": self.robot_cmd = RobotCmd.RUN_BACKWARD
                elif ret[3] == "left": self.robot_cmd = RobotCmd.RUN_TURN_LEFT
                elif ret[3] == "right": self.robot_cmd = RobotCmd.RUN_TURN_RIGHT
                else: self.robot_cmd = RobotCmd.RUN_STOP
                self.watchdog_count = 0

    def quit_app(self):
        print("\nShutting down safely...")
        self.robot.run_stop()
        
        if hasattr(self, 'ws') and self.ws:
            try: self.ws.close()
            except: pass

        if self.gui_enabled and self.root:
            try: self.root.destroy()
            except: pass

        if rclpy.ok():
            rclpy.shutdown()
            
        sys.exit(0)

if __name__ == "__main__":
    rclpy.init()
    controller = RobotController()
    controller.login_and_connect()

    if controller.gui_enabled:
        ros_thread = threading.Thread(target=lambda: rclpy.spin(controller), daemon=True)
        ros_thread.start()
        try:
            controller.root.mainloop()
        except KeyboardInterrupt:
            controller.quit_app()
    else:
        print(">>> Running in CUI Mode (No Display). Press Ctrl+C to stop.")
        try:
            ros_thread = threading.Thread(target=lambda: rclpy.spin(controller), daemon=True)
            ros_thread.start()
            
            # メインスレッドが即終了しないように維持する
            while rclpy.ok():
                sleep(1)
                
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt detected.")
        finally:
            controller.quit_app()