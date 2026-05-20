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

# --- 追加ライブラリ ---
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
    def run_straight(self, rpm): print(f"Mock: Straight {rpm} RPM")
    def run_pivot_turn(self, rpm): print(f"Mock: Turn {rpm} RPM")
    def run_stop(self): print("Mock: Stop")
    def run(self, l, r): print(f"Mock: Left:{l}, Right:{r}")

class RobotCmd(Enum):
    DISABLE = auto()
    RUN_FORWARD = auto()
    RUN_BACKWARD = auto()
    RUN_TURN_LEFT = auto()
    RUN_TURN_RIGHT = auto()
    RUN_RPM = auto()
    RUN_STOP = auto()

class RobotController(Node):
    def __init__(self):
        super().__init__('robot_controller')
        self.load_config()
        
        self.robot_cmd = RobotCmd.DISABLE
        self.robot_speed_rpm = 1500
        self.rpm_left = 0
        self.rpm_right = 0
        self.last_ws_data_time = 0
        self.is_ws_connected = False
        self.watchdog_count = 0
        self.WATCHDOG_COUNT_MAX = 20 # 通信途絶判定(秒換算で調整)
        
        self.in_zone_1 = self.in_zone_2 = self.in_zone_3 = False
        self.closest_distance = None

        # ロボット初期化
        self.robot = MockRobot()
        self.robot.enable()

        # GUI
        self.setup_gui()

        # --- MQTT受信設定 (ジョイスティック用) ---
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_message = self.on_mqtt_message
        try:
            # 自分自身のPCのブローカーに接続
            self.mqtt_client.connect("localhost", 1883, 60)
            self.mqtt_client.subscribe("robot/joystick")
            # 映像・ROS2を止めないよう別スレッドで待機
            threading.Thread(target=self.mqtt_client.loop_forever, daemon=True).start()
            print(">>> MQTT Joystick Receiver: Started (Listening on localhost:1883)")
        except Exception as e:
            print(f"MQTT Connection failed: {e}")

        # --- ROS 2 通信設定 ---
        qos_profile = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=10)
        self.subscription = self.create_subscription(LaserScan, '/scan', self.lidar_callback, qos_profile)
        
        self.create_timer(0.05, self.robot_loop)

    def on_mqtt_message(self, client, userdata, msg):
        """MQTT経由でジョイスティックデータが届いた時の処理"""
        try:
            payload = json.loads(msg.payload.decode())
            axes = payload.get("axes", [])
            
            if len(axes) > 1:
                ly = axes[1] # 前後
                lx = axes[0] # 左右
                
                # スティック入力でロボットコマンドを直接上書き
                if ly < -0.5: self.robot_cmd = RobotCmd.RUN_FORWARD
                elif ly > 0.5: self.robot_cmd = RobotCmd.RUN_BACKWARD
                elif lx < -0.5: self.robot_cmd = RobotCmd.RUN_TURN_LEFT
                elif lx > 0.5: self.robot_cmd = RobotCmd.RUN_TURN_RIGHT
                else: self.robot_cmd = RobotCmd.RUN_STOP
                
                # 入力があったのでウォッチドッグをリセット
                self.watchdog_count = 0
        except Exception as e:
            print(f"MQTT Error: {e}")

    def lidar_callback(self, msg):
        self.in_zone_1 = self.in_zone_2 = self.in_zone_3 = False
        angle = msg.angle_min
        for r in msg.ranges:
            if 0.05 < r < 10.0:
                x = r * math.cos(angle); y = r * math.sin(angle)
                if x > 0:
                    if x <= 0.22 and abs(y) <= 0.25: self.in_zone_3 = True
                    if x <= 0.55 and abs(y) <= 0.25: self.in_zone_2 = True
                    if x <= 1.05 and abs(y) <= 0.5:  self.in_zone_1 = True
            angle += msg.angle_increment

    def robot_loop(self):
        # 安全装置: 一定時間コマンドが来なければ停止
        if self.watchdog_count > self.WATCHDOG_COUNT_MAX:
            if self.robot_cmd != RobotCmd.DISABLE:
                self.robot.run_stop(); self.robot_cmd = RobotCmd.DISABLE
            return

        # 障害物検知時の自動停止
        is_forward = self.robot_cmd in [RobotCmd.RUN_FORWARD, RobotCmd.RUN_TURN_LEFT, RobotCmd.RUN_TURN_RIGHT]
        if is_forward and self.in_zone_3:
            self.robot.run_stop()
        else:
            self.execute_robot_command()
        
        self.watchdog_count += 1

    def execute_robot_command(self):
        speed = self.robot_speed_rpm
        if self.in_zone_2: speed *= 0.25
        elif self.in_zone_1: speed *= 0.5
        
        if self.robot_cmd == RobotCmd.DISABLE: return
        self.robot.enable()
        if self.robot_cmd == RobotCmd.RUN_FORWARD: self.robot.run_straight(speed)
        elif self.robot_cmd == RobotCmd.RUN_BACKWARD: self.robot.run_straight(-speed / 2)
        elif self.robot_cmd == RobotCmd.RUN_TURN_LEFT: self.robot.run_pivot_turn(-speed / 2)
        elif self.robot_cmd == RobotCmd.RUN_TURN_RIGHT: self.robot.run_pivot_turn(speed / 2)
        elif self.robot_cmd == RobotCmd.RUN_STOP: self.robot.run_stop(); self.robot.disable()
        elif self.robot_cmd == RobotCmd.RUN_RPM: self.robot.run(self.rpm_left, self.rpm_right)

    def load_config(self):
        self.half_frontal_angle_rad = math.radians(90) / 2

    def setup_gui(self):
        try:
            self.root = tk.Tk(); self.root.title("Control")
            self.gui_enabled = True
        except:
            self.root = None; self.gui_enabled = False

    def login_and_connect(self):
        """既存のWebSocket映像通信用ログイン"""
        def task():
            try:
                url = 'https://api.avatarchallenge.ca-platform.org/clientLogin/?name=keigan1-ca001&password=eiCa7too&code=keigan1'
                resp = requests.post(url, timeout=5)
                self.info = resp.json()
                self.connect_ws()
            except Exception as e:
                sleep(5); self.login_and_connect()
        threading.Thread(target=task, daemon=True).start()

    def connect_ws(self):
        token = self.info['authorisation']['token']
        self.ws = websocket.WebSocketApp(
            f'wss://ws.avatarchallenge.ca-platform.org?token={token}',
            on_message=self.on_ws_message,
            on_open=lambda ws: setattr(self, 'is_ws_connected', True),
            on_close=lambda ws, s, m: setattr(self, 'is_ws_connected', False)
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def on_ws_message(self, ws, message):
        """サーバー(WebSocket)からの命令受信"""
        ret = message.split(';')
        if len(ret) > 3 and ret[0] == "cmd" and ret[1] == "robot":
            action = ret[3]
            # 手元のコントローラーを動かしていない時だけ、サーバー命令に従う
            if action == "forward": self.robot_cmd = RobotCmd.RUN_FORWARD
            elif action == "stop": self.robot_cmd = RobotCmd.RUN_STOP
            # ...必要に応じて他の命令も追加...
            self.watchdog_count = 0

    def quit_app(self):
        self.robot.run_stop(); self.robot.disable()
        if self.gui_enabled: self.root.destroy()
        rclpy.shutdown(); sys.exit()

if __name__ == "__main__":
    rclpy.init()
    controller = RobotController()
    controller.login_and_connect()

    if controller.gui_enabled:
        ros_thread = threading.Thread(target=lambda: rclpy.spin(controller), daemon=True)
        ros_thread.start()
        controller.root.mainloop()
    else:
        try:
            rclpy.spin(controller)
        except KeyboardInterrupt:
            pass
        finally:
            controller.quit_app()