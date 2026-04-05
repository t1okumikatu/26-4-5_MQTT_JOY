# -*- coding: utf-8 -*-
import sys
import os
import math
import threading
import requests
import yaml
from time import sleep, time
import tkinter as tk

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
    def enable(self):
        print("Mock: Motors Enabled")
    def disable(self):
        print("Mock: Motors Disabled")
    def run_straight(self, rpm):
        print(f"Mock: Moving Straight at {rpm} RPM")
    def run_pivot_turn(self, rpm):
        print(f"Mock: Pivot Turning at {rpm} RPM")
    def run_stop(self):
        print("Mock: Stop Command Sent")
    def run(self, l, r):
        print(f"Mock: Manual RPM -> Left:{l}, Right:{r}")

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
        self.WATCHDOG_COUNT_MAX = 10
        self.ws = None
        self.info = None
        self.gui_enabled = False 

        self.in_zone_1 = False
        self.in_zone_2 = False
        self.in_zone_3 = False
        self.closest_distance = None

        # --- ロボットハードウェア初期化 (実機を無視してダミーを強制適用) ---
        print("Starting Hardware Initialization...")
        self.robot = MockRobot()
        self.robot.enable()

        # GUIセットアップ (SSH接続時は自動的にSkip)
        self.setup_gui()

        # --- ROS 2 通信設定 ---
        qos_profile = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=10)
        self.subscription = self.create_subscription(LaserScan, '/scan', self.lidar_callback, qos_profile)
        
        self.create_timer(0.05, self.robot_loop)
        self.create_timer(0.2, self.ui_update_loop)
        # --- 150行目あたりにこれを追加 ---
        WS_BASE_URL = 'wss://ws.avatarchallenge.ca-platform.org?token='
    def load_config(self):
        try:
            with open('config.yaml', 'r') as file:
                config = yaml.safe_load(file)
            frontal_angle = config['lidar'].get('frontal_angle_degrees', 90)
            self.half_frontal_angle_rad = math.radians(frontal_angle) / 2
        except:
            print("Config load failed. Using default 90deg.")
            self.half_frontal_angle_rad = math.radians(90) / 2

    def setup_gui(self):
        try:
            self.root = tk.Tk()
            self.root.title("ロボット制御システム")
            self.gui_enabled = True
            print("GUI Mode: On")
        except Exception:
            print("GUI Skip: Running in Headless Mode")
            self.root = None
            self.gui_enabled = False

    def lidar_callback(self, msg):
        self.in_zone_1 = self.in_zone_2 = self.in_zone_3 = False
        valid_ranges = []
        angle = msg.angle_min
        for r in msg.ranges:
            if 0.05 < r < 10.0:
                if -self.half_frontal_angle_rad <= angle <= self.half_frontal_angle_rad:
                    valid_ranges.append(r)
                x = r * math.cos(angle); y = r * math.sin(angle)
                if x > 0:
                    if x <= 0.22 and abs(y) <= 0.25: self.in_zone_3 = True
                    if x <= 0.55 and abs(y) <= 0.25: self.in_zone_2 = True
                    if x <= 1.05 and abs(y) <= 0.5:  self.in_zone_1 = True
            angle += msg.angle_increment
        self.closest_distance = min(valid_ranges) if valid_ranges else None

    def robot_loop(self):
        if self.watchdog_count > self.WATCHDOG_COUNT_MAX:
            if self.robot_cmd != RobotCmd.DISABLE:
                self.robot.run_stop(); self.robot.disable()
                self.robot_cmd = RobotCmd.DISABLE
            return
        is_forward = self.robot_cmd in [RobotCmd.RUN_FORWARD, RobotCmd.RUN_TURN_LEFT, RobotCmd.RUN_TURN_RIGHT]
        if is_forward and self.in_zone_3:
            self.robot.run_stop(); self.robot_cmd = RobotCmd.RUN_STOP
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
        elif self.robot_cmd == RobotCmd.RUN_STOP:
            self.robot.run_stop(); self.robot.disable()
        elif self.robot_cmd == RobotCmd.RUN_RPM: self.robot.run(self.rpm_left, self.rpm_right)

    def ui_update_loop(self):
        pass

    def login_and_connect(self):
        def task():
            try:
                url = 'https://api.avatarchallenge.ca-platform.org/clientLogin/?name=keigan1-ca001&password=eiCa7too&code=keigan1'
                resp = requests.post(url, timeout=5)
                self.info = resp.json()
                self.connect_ws()
            except Exception as e:
                print(f"Login failed: {e}. Retry in 5s...")
                sleep(5); self.login_and_connect()
        threading.Thread(target=task, daemon=True).start()

    def connect_ws(self):
        token = self.info['authorisation']['token']
        self.ws = websocket.WebSocketApp(
            f'wss://ws.avatarchallenge.ca-platform.org?token={token}', # URLを直接記述
            on_message=self.on_ws_message,
            on_open=lambda ws: setattr(self, 'is_ws_connected', True),
            on_close=lambda ws, s, m: setattr(self, 'is_ws_connected', False)
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def on_ws_message(self, ws, message):
        # サーバーから届いた全メッセージを表示（デバッグ用）
        print(f"📩 Received RAW: {message}")
        
        # 届いたメッセージにコマンドが含まれているかチェック
        # OPからの転送の場合、メッセージの中に 'forward' などが含まれているか探す
        if "forward" in message: action = "forward"
        elif "backward" in message: action = "backward"
        elif "left" in message: action = "left"
        elif "right" in message: action = "right"
        elif "stop" in message: action = "stop"
        else: return # 関係ないメッセージは無視

        print(f"✅ Command recognized: {action}")
        
        # ロボットの動作コマンドに反映
        if action == "forward": self.robot_cmd = RobotCmd.RUN_STRAIGHT
        elif action == "backward": self.robot_cmd = RobotCmd.RUN_BACK
        elif action == "left": self.robot_cmd = RobotCmd.RUN_TURN_LEFT
        elif action == "right": self.robot_cmd = RobotCmd.RUN_TURN_RIGHT
        elif action == "stop": self.robot_cmd = RobotCmd.RUN_STOP

    def quit_app(self):
        self.robot.run_stop(); self.robot.disable()
        if self.gui_enabled: self.root.destroy()
        rclpy.shutdown()
        sys.exit()

if __name__ == "__main__":
    rclpy.init()
    controller = RobotController()
    controller.login_and_connect()

    if controller.gui_enabled:
        ros_thread = threading.Thread(target=lambda: rclpy.spin(controller), daemon=True)
        ros_thread.start()
        controller.root.mainloop()
    else:
        print("Headless mode: Listening for WebSocket commands...")
        try:
            rclpy.spin(controller)
        except KeyboardInterrupt:
            pass
        finally:
            controller.quit_app()