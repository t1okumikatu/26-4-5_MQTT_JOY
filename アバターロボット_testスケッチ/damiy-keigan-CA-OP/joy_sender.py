import pygame
import requests
import websocket
import threading
import time
import json

# --- 設定 ---
LOGIN_URL = 'https://api.avatarchallenge.ca-platform.org/clientLogin/?name=keigan1-op001&password=ooWe6gee&code=keigan1'
WS_BASE_URL = 'wss://ws.avatarchallenge.ca-platform.org?token='

class JoySender:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        self.joy = pygame.joystick.Joystick(0)
        self.joy.init()
        self.ws = None
        self.connected = False

    def login_and_connect(self):
        print("Logging in...")
        resp = requests.post(LOGIN_URL)
        info = resp.json()
        token = info['authorisation']['token']
        
        self.ws = websocket.WebSocketApp(
            f"{WS_BASE_URL}{token}",
            on_open=self.on_open,
            on_error=self.on_error
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def on_open(self, ws):
        print("Connected to Server!")
        self.connected = True

    def on_error(self, ws, error):
        print(f"WS Error: {error}")

    def send_cmd(self, action):
        if self.connected:
            # サーバーの仕様に合わせた、より厳密なフォーマットです
            # 1. 宛先指定 2. コマンド 3. アクション 4. 末尾の ;
            msg = f"to;keigan1-ca001;cmd;robot;0;{action};" 
            try:
                # 念のため、メッセージを文字列(UTF-8)として確実に送信
                self.ws.send(msg)
                print(f"🚀 Sent to Robot: {msg}")
            except Exception as e:
                print(f"❌ Send Error: {e}")
    def run(self):
        self.login_and_connect()
        print("Ready! Use Stick to move. Press Button 0 to Stop.")
        
        last_cmd = ""
        
        try:
            while True:
                pygame.event.pump()
                
                # スティックの入力取得
                x = self.joy.get_axis(0) # 左右
                y = self.joy.get_axis(1) # 上下
                
                # 簡易的な方向判定（しきい値0.5）
                current_cmd = "stop"
                if y < -0.5: current_cmd = "forward"
                elif y > 0.5: current_cmd = "backward"
                elif x < -0.5: current_cmd = "left"
                elif x > 0.5: current_cmd = "right"
                
                # ボタン0で強制停止
                if self.joy.get_button(0): current_cmd = "stop"

                # 状態が変わった時だけ送信
                if current_cmd != last_cmd:
                    print(f"Sending: {current_cmd}")
                    self.send_cmd(current_cmd)
                    last_cmd = current_cmd
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.send_cmd("stop")
            pygame.quit()

if __name__ == "__main__":
    sender = JoySender()
    sender.run()