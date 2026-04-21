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

#import robot_4wd
import robot_2wd_new
import websocket

from enum import Enum, auto

# ---------------------------------------------------------
# Robot command enum
# ---------------------------------------------------------
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
    RUN_RPM = auto() # ジョイスティック用
    RUN_STOP = auto()

# ---------------------------------------------------------
# Globals
# ---------------------------------------------------------
ROBOT_SPEED_RPM_HIGH = 2000
ROBOT_SPEED_RPM_MIDDLE = 500
ROBOT_SPEED_RPM_LOW = 250
last_ws_data_time = 0
command_parts = []
is_ws_connected = False
ws = None
wst = None

root = tk.Tk()
root.title("アプリの再起動と終了")
root.geometry("400x400")

zones_frame = tk.Frame(root)
zones_frame.pack(pady=10)

# Use grid layout for side-by-side labels
zone1_label = tk.Label(zones_frame, text="Zone 1: ", font=("Arial", 18, "bold"), fg="black")
zone1_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
zone1_status = tk.Label(zones_frame, text="Clear", font=("Arial", 18, "bold"), fg="green")
zone1_status.grid(row=0, column=1, padx=5, pady=5, sticky="w")

zone2_label = tk.Label(zones_frame, text="Zone 2: ", font=("Arial", 18, "bold"), fg="black")
zone2_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
zone2_status = tk.Label(zones_frame, text="Clear", font=("Arial", 18, "bold"), fg="green")
zone2_status.grid(row=1, column=1, padx=5, pady=5, sticky="w")

zone3_label = tk.Label(zones_frame, text="Zone 3: ", font=("Arial", 18, "bold"), fg="black")
zone3_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
zone3_status = tk.Label(zones_frame, text="Clear", font=("Arial", 18, "bold"), fg="green")
zone3_status.grid(row=2, column=1, padx=5, pady=5, sticky="w")

closest_label = tk.Label(root, text="Closest obstacle: N/A", font=("Arial", 14, "bold"))
closest_label.pack(pady=5)

# Label for WebSocket connection
ws_label = tk.Label(root, text="Websocket Connection", font=("Arial", 14, "bold"))
ws_label.pack(side="top", pady=10)

# Lamp at the bottom center
lamp_canvas = tk.Canvas(root, width=80, height=80, bg="white", highlightthickness=0)
lamp_id = lamp_canvas.create_oval(20, 15, 60, 55, fill="gray")
lamp_text = lamp_canvas.create_text(
    40, 70,
    text="No data",
    anchor="center",
    fill="black",
    font=("Arial", 10, "bold")
)
lamp_canvas.pack(side="top", pady=10)

joystick_label = tk.Label(root, text="Joystick: STOP", font=("Arial", 14, "bold"))
joystick_label.pack(side="top", pady=10)

def update_joystick_label(command_parts):
    # command_parts is something like: ["cmd", "robot", "run", "forward"]
    if command_parts:
        if len(command_parts) > 3 and command_parts[0] == "cmd" and command_parts[1] == "robot" and command_parts[2] == "run":
            cmd_type = command_parts[3]
            if cmd_type == "forward":
                joystick_label.config(text="Joystick: FORWARD")
            elif cmd_type == "backward":
                joystick_label.config(text="Joystick: BACKWARD")
            elif cmd_type == "forward-left":
                joystick_label.config(text="Joystick: FRONT-LEFT")
            elif cmd_type == "forward-right":
                joystick_label.config(text="Joystick: FRONT-RIGHT")
            elif cmd_type == "backward-left":
                joystick_label.config(text="Joystick: BACK-LEFT")
            elif cmd_type == "backward-right":
                joystick_label.config(text="Joystick: BACK-RIGHT")
            elif cmd_type == "left":
                joystick_label.config(text="Joystick: LEFT")
            elif cmd_type == "right":
                joystick_label.config(text="Joystick: RIGHT")
            else:
                joystick_label.config(text="Joystick: STOP")
        else:
            joystick_label.config(text="Joystick: STOP")

def update_zone_labels(listener):
    if listener.in_zone_1:
        zone1_status.config(text="Obstacle detected", fg="red")
    else:
        zone1_status.config(text="Clear", fg="green")

    if listener.in_zone_2:
        zone2_status.config(text="Obstacle detected", fg="red")
    else:
        zone2_status.config(text="Clear", fg="green")

    if listener.in_zone_3:
        zone3_status.config(text="Obstacle detected", fg="red")
    else:
        zone3_status.config(text="Clear", fg="green")

def update_lamp_state():
    # If recent data was received in the last second => "green", else "gray"
    if time() - last_ws_data_time < 1.0:
        lamp_canvas.itemconfig(lamp_id, fill="green")
        lamp_canvas.itemconfig(lamp_text, text="Receiving")
    else:
        lamp_canvas.itemconfig(lamp_id, fill="gray")
        lamp_canvas.itemconfig(lamp_text, text="No data")

def update_lidar_info(listener):
    update_zone_labels(listener)
    if listener.closest_distance is not None:
        label_text = f"Closest obstacle: {listener.closest_distance:.2f} m"
    else:
        label_text = "Closest obstacle: N/A"

    # Decide label color based on zones
    if listener.in_zone_3:
        # Zone 3 => red
        closest_label.config(text=label_text, fg="red")
    elif listener.in_zone_2:
        # Zone 2 => yellow
        closest_label.config(text=label_text, fg="yellow")
    elif listener.in_zone_1:
        # Zone 1 => green
        closest_label.config(text=label_text, fg="green")
    else:
        # Otherwise => black
        closest_label.config(text=label_text, fg="black")

def ui_update_loop(listener):
    global command_parts
    update_lidar_info(listener)
    update_lamp_state()
    update_joystick_label(command_parts)
    root.after(500, ui_update_loop, listener)

config_file_path = 'config.yaml'
if not os.path.exists(config_file_path):
    raise FileNotFoundError(f"Configuration file '{config_file_path}' not found.")
with open(config_file_path, 'r') as file:
    config = yaml.safe_load(file)

frontal_angle_degrees = config['lidar'].get('frontal_angle_degrees', 90)
half_frontal_angle_radians = math.radians(frontal_angle_degrees) / 2

robot_speed_rpm = ROBOT_SPEED_RPM_HIGH
robot_cmd = RobotCmd.DISABLE
rpm_left = 0
rpm_right = 0

# Robot loop interval
ROBOT_LOOP_INTERVAL = 0.05
watchdog_count = 0
WATCHDOG_COUNT_MAX = 4

robot = None  # Will be initialized later
rbt = None    # Timer object

def reset_watchdog_count():
    global watchdog_count
    watchdog_count = 0

# ---------------------------------------------------------
# Lidar listener
# ---------------------------------------------------------
class LidarListener(Node):
    def __init__(self):
        super().__init__('lidar_listener')
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=10
        )
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.listener_callback,
            qos_profile
        )

        # Track zones
        self.in_zone_1 = False  # 1.0m x 1.0m
        self.in_zone_2 = False  # 0.5m x 0.5m
        self.in_zone_3 = False  # 0.2m x 0.2m
        self.closest_distance = float('inf')

    def listener_callback(self, msg):
        # Reset zone flags
        self.in_zone_1 = False
        self.in_zone_2 = False
        self.in_zone_3 = False
        front_angle_start = -half_frontal_angle_radians
        front_angle_end = half_frontal_angle_radians
        angle_increment = msg.angle_increment
        num_scans = len(msg.ranges)
        start_index = int(max(0, (front_angle_start - msg.angle_min) / angle_increment))
        end_index = int(min(num_scans, (front_angle_end - msg.angle_min) / angle_increment))
        section_ranges = msg.ranges[start_index:end_index]

        # Filter out invalid range values
        section_ranges = [r for r in section_ranges if 0 < r < float('inf')]

        # Find the minimum distance in the specified area
        if not section_ranges:
            self.closest_distance = 5555
        else:
            self.closest_distance = min(section_ranges)
        if self.closest_distance == float('inf'):
            self.closest_distance = None

        angle_increment = msg.angle_increment
        angle = msg.angle_min
        for r in msg.ranges:
            if 0 < r < float('inf'):
                # Convert (r, angle) => (x, y)
                x = r * math.cos(angle)
                y = r * math.sin(angle)

                # Only consider obstacles in front (x > 0)
                if x > 0:
                    # Zone 3: 0.2 x 0.5
                    if x <= 0.2 and abs(y) <= 0.25:
                        self.in_zone_3 = True

                    # Zone 2: 0.5 x 0.5
                    if x <= 0.5 and abs(y) <= 0.25:
                        self.in_zone_2 = True

                    # Zone 1: 1.0 x 1.0
                    if x <= 1.0 and abs(y) <= 0.5:
                        self.in_zone_1 = True

            angle += angle_increment

# ---------------------------------------------------------
# Spin the Lidar in a separate thread at a fixed interval
# ---------------------------------------------------------
def spin_lidar_listener_interval(listener, interval=0.1):
    while rclpy.ok():
        rclpy.spin_once(listener, timeout_sec=0.0)

# ---------------------------------------------------------
# Robot loop logic
# ---------------------------------------------------------
def robot_loop(lidar_listener):
    global robot_cmd, rbt, watchdog_count

    if watchdog_count > WATCHDOG_COUNT_MAX:
        robot_cmd = RobotCmd.DISABLE
        robot.disable()
    elif robot_cmd == RobotCmd.RUN_FORWARD:
        if lidar_listener.in_zone_3:
            # Zone 3 => Immediate stop, no forward
            robot.run_stop()
            robot.disable()
            robot_cmd = RobotCmd.DISABLE
        elif lidar_listener.in_zone_2:
            # Zone 2 => run at speed/4
            robot.enable()
            robot.run_straight(robot_speed_rpm * 0.2)
        elif lidar_listener.in_zone_1:
            # Zone 1 => run at speed/2
            robot.enable()
            robot.run_straight(robot_speed_rpm * 0.4)
        else:
            robot.enable()
            robot.run_straight(robot_speed_rpm)

    elif robot_cmd == RobotCmd.RUN_BACKWARD:
        # Always allow backward movement
        robot.enable()
        robot.run_straight(-robot_speed_rpm / 2)

    elif robot_cmd == RobotCmd.RUN_FORWARD_LEFT:
        if lidar_listener.in_zone_3:
            robot.run_stop()
            robot.disable()
            robot_cmd = RobotCmd.DISABLE
        elif lidar_listener.in_zone_2:
            robot.enable()
            robot.run(robot_speed_rpm / 4, robot_speed_rpm / 2)
        elif lidar_listener.in_zone_1:
            robot.enable()
            # Example: reduce left motor more to veer left slowly
            robot.run(robot_speed_rpm / 4, robot_speed_rpm / 2)
        else:
            robot.enable()
            robot.run(robot_speed_rpm / 2, robot_speed_rpm)

    elif robot_cmd == RobotCmd.RUN_FORWARD_RIGHT:
        if lidar_listener.in_zone_3:
            robot.run_stop()
            robot.disable()
            robot_cmd = RobotCmd.DISABLE
        elif lidar_listener.in_zone_2:
            robot.enable()
            robot.run(robot_speed_rpm / 2, robot_speed_rpm / 4)
        elif lidar_listener.in_zone_1:
            robot.enable()
            robot.run(robot_speed_rpm / 2, robot_speed_rpm / 4)
        else:
            robot.enable()
            robot.run(robot_speed_rpm, robot_speed_rpm / 2)

    elif robot_cmd == RobotCmd.RUN_BACKWARD_LEFT:
        # Keep simple or add your own zone logic if needed
        robot.enable()
        robot.run(-robot_speed_rpm / 2, -robot_speed_rpm)

    elif robot_cmd == RobotCmd.RUN_BACKWARD_RIGHT:
        # Keep simple or add your own zone logic if needed
        robot.enable()
        robot.run(-robot_speed_rpm, -robot_speed_rpm / 2)

    elif robot_cmd == RobotCmd.RUN_TURN_LEFT:
        if lidar_listener.in_zone_3:
            robot.run_stop()
            robot.disable()
            robot_cmd = RobotCmd.DISABLE
        else:
            robot.enable()
            robot.run_pivot_turn(-robot_speed_rpm / 2)

    elif robot_cmd == RobotCmd.RUN_TURN_RIGHT:
        if lidar_listener.in_zone_3:
            robot.run_stop()
            robot.disable()
            robot_cmd = RobotCmd.DISABLE
        else:
            robot.enable()
            robot.run_pivot_turn(robot_speed_rpm / 2)

    elif robot_cmd == RobotCmd.RUN_STOP:
        robot.run_stop()
        robot.disable()
        robot_cmd = RobotCmd.DISABLE

    elif robot_cmd == RobotCmd.RUN_RPM:
        if rpm_left == 0 and rpm_right == 0:
            robot.run_stop()
        else:
            # Example: run with given RPM
            robot.enable()
            robot.run(rpm_left, rpm_right)

    else:
        robot.disable()

    # Schedule next robot loop
    rbt = threading.Timer(ROBOT_LOOP_INTERVAL, robot_loop, args=[lidar_listener])
    rbt.start()

    watchdog_count += 1

# ---------------------------------------------------------
# Handle incoming commands
# ---------------------------------------------------------
def handle_robot_cmd(ret):
    global robot_cmd, rpm_left, rpm_right
    if len(ret) > 3 and ret[0] == "cmd" and ret[1] == "robot":
        if ret[2] == "run":
            if ret[3] == "rpm":
                # Ensure correct conversion from string if needed
                rpm_left = int(ret[4])
                rpm_right = int(ret[5])
                robot_cmd = RobotCmd.RUN_RPM
            elif ret[3] == "forward":
                robot_cmd = RobotCmd.RUN_FORWARD
            elif ret[3] == "backward":
                robot_cmd = RobotCmd.RUN_BACKWARD
            elif ret[3] == "forward-left":
                robot_cmd = RobotCmd.RUN_FORWARD_LEFT
            elif ret[3] == "forward-right":
                robot_cmd = RobotCmd.RUN_FORWARD_RIGHT
            elif ret[3] == "backward-left":
                robot_cmd = RobotCmd.RUN_BACKWARD_LEFT
            elif ret[3] == "backward-right":
                robot_cmd = RobotCmd.RUN_BACKWARD_RIGHT
            elif ret[3] == "left":
                robot_cmd = RobotCmd.RUN_TURN_LEFT
            elif ret[3] == "right":
                robot_cmd = RobotCmd.RUN_TURN_RIGHT
            else:
                if robot_cmd != RobotCmd.DISABLE:
                    robot_cmd = RobotCmd.RUN_STOP
                else:
                    robot_cmd = RobotCmd.DISABLE
        else:
            if robot_cmd != RobotCmd.DISABLE:
                robot_cmd = RobotCmd.RUN_STOP
            else:
                robot_cmd = RobotCmd.DISABLE
    else:
        if robot_cmd != RobotCmd.DISABLE:
            robot_cmd = RobotCmd.RUN_STOP
        else:
            robot_cmd = RobotCmd.DISABLE

def reset_watchdog_count():
    global watchdog_count
    watchdog_count = 0

def on_message(ws, message):
    global last_ws_data_time, command_parts
    last_ws_data_time = time()
    cmd = message.split(';')
    command_parts = cmd
    handle_robot_cmd(cmd)
    reset_watchdog_count()

def connect_websocket(token):
    """
    Create and start a new WebSocket connection if not already connected.
    """
    global ws, wst, is_ws_connected

    if not is_ws_connected:
        ws = websocket.WebSocketApp(
            'wss://ws.avatarchallenge.ca-platform.org?token=' + token,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        wst = threading.Thread(target=ws.run_forever, daemon=True)
        wst.start()

def check_ws():
    """
    Check if WebSocket is connected. If not, try to connect.
    Schedule another check in 5 seconds if still offline.
    """
    global is_ws_connected, info
    if not is_ws_connected:
        connect_websocket(info['authorisation']['token'])
        root.after(5000, check_ws)

def on_open(ws):
    global is_ws_connected
    is_ws_connected = True
    print("Opened connection")

def on_close(ws, close_status_code, close_msg):
    global is_ws_connected
    is_ws_connected = False
    print("### Connection closed ###")
    # Schedule a reconnect check
    root.after(5000, check_ws)

def on_error(ws, error):
    global is_ws_connected
    is_ws_connected = False
    print(error)
    # Schedule a reconnect check
    root.after(5000, check_ws)

# ---------------------------------------------------------
# Utility functions and GUI
# ---------------------------------------------------------
def exit_handler(signum, frame):
    sys.exit(0)
    raise KeyboardInterrupt

def restart_app():
    python = sys.executable
    os.execl(python, python, *sys.argv)

def quit_app():
    print("アプリケーションを停止します")
    root.destroy()
    sys.exit()

root = tk.Tk()
root.title("アプリの再起動と終了")
root.geometry("300x300")

root.protocol("WM_DELETE_WINDOW", quit_app)

def create_rounded_button(canvas, x, y, width, height, radius, text, command, color="blue"):
    parts = [
        canvas.create_arc(x, y, x + radius*2, y + radius*2, start=90, extent=90, fill=color, outline=""),
        canvas.create_arc(x + width - radius*2, y, x + width, y + radius*2, start=0, extent=90, fill=color, outline=""),
        canvas.create_arc(x, y + height - radius*2, x + radius*2, y + height, start=180, extent=90, fill=color, outline=""),
        canvas.create_arc(x + width - radius*2, y + height - radius*2, x + width, y + height, start=270, extent=90, fill=color, outline=""),
        canvas.create_rectangle(x + radius, y, x + width - radius, y + height, fill=color, outline=""),
        canvas.create_rectangle(x, y + radius, x + width, y + height - radius, fill=color, outline="")
    ]
    button_text = canvas.create_text(
        x + width / 2,
        y + height / 2,
        text=text,
        fill="white",
        font=("Arial", 18, "bold")
    )
    def on_click(event):
        command()
    for part in parts:
        canvas.tag_bind(part, "<Button-1>", on_click)
    canvas.tag_bind(button_text, "<Button-1>", on_click)

canvas = tk.Canvas(root, width=300, height=300, bg="white", highlightthickness=0)
canvas.pack()

create_rounded_button(canvas, x=50, y=50, width=200, height=70, radius=20, text="再起動", command=restart_app, color="blue")
create_rounded_button(canvas, x=50, y=150, width=200, height=70, radius=20, text="終了", command=quit_app, color="red")

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
if __name__ == "__main__":
    rclpy.init(args=sys.argv)
    try:
        # Initialize robot hardware
        #robot = robot_4wd.Robot4WD("/dev/motor1")
        robot = robot_2wd_new.Robot2WD("/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B0001KJH-if00-port0","/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B003725S-if00-port0") #Avatar 1

        # Authentication
        def account_login():
            response = requests.post('https://api.avatarchallenge.ca-platform.org/clientLogin/?name=keigan1-ca001&password=eiCa7too&code=keigan1')
            print(response.json())
            return response.json()

        info = account_login()

        # WebSocket
        check_ws()

        # Lidar node
        lidar_listener = LidarListener()

        # Robot loop - schedule first call
        rbt = threading.Timer(ROBOT_LOOP_INTERVAL, robot_loop, args=[lidar_listener])
        rbt.start()

        # Spin the Lidar in a separate thread with short interval
        spin_thread = threading.Thread(
            target=spin_lidar_listener_interval,
            args=(lidar_listener, 0.05),
            daemon=True
        )
        spin_thread.start()
        ui_update_loop(lidar_listener)

        # GUI loop
        root.mainloop()

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        if ws:
            ws.close()
        if rbt:
            rbt.cancel()
        robot.disable()
        rclpy.shutdown()

    print("Unreachable")
