import time
import json
import network
import socket
import _thread

WIFI_CFG_PATH = "/sdcard/wifi.json"
AP_SSID = "Roboot-Setup"

CONFIG_DONE = False
CONFIG_SSID = ""
CONFIG_PWD = ""

class WiFiManager:
    def __init__(self):
        self.wlan = None
        self.ap = None

    def _load_creds(self):
        try:
            f = open(WIFI_CFG_PATH, "r")
            data = json.loads(f.read())
            f.close()
            return data.get("ssid", ""), data.get("password", "")
        except Exception:
            return "", ""

    def _save_creds(self, ssid, pwd):
        try:
            f = open(WIFI_CFG_PATH, "w")
            f.write(json.dumps({"ssid": ssid, "password": pwd}))
            f.close()
        except Exception:
            pass

    def connect(self, ssid, pwd, timeout=12):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        if not self.wlan.isconnected():
            self.wlan.connect(ssid, pwd)
            start = time.time()
            while not self.wlan.isconnected():
                if time.time() - start > timeout:
                    return False
                time.sleep_ms(500)
        return True

    def start_ap(self):
        try:
            self.ap = network.WLAN(network.AP_IF)
            if not self.ap.active():
                self.ap.active(True)
                time.sleep_ms(300)
            try:
                self.ap.config(essid=AP_SSID)
            except Exception:
                try:
                    self.ap.config(AP_SSID)
                except Exception:
                    pass
            print("[安全层] AP 热点配置完成:", AP_SSID)
        except Exception as e:
            print("[安全层] AP 启动失败，跳过基带控制:", e)

    def stop_ap(self):
        print("[安全层] 逻辑退出 AP 模式")


def start_ap_server():
    global CONFIG_DONE, CONFIG_SSID, CONFIG_PWD
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('', 8080))
        s.listen(1)
        print("配网 Web 服务已在 8080 端口就绪...")
    except Exception as e:
        print("Socket 绑定失败:", e)
        s.close()
        return

    while not CONFIG_DONE:
        try:
            s.settimeout(1.5)
            try:
                res = s.accept()
            except OSError:
                continue

            client = res[0]
            req = client.recv(1024).decode('utf-8')

            if "ssid=" in req and "pwd=" in req:
                try:
                    params = req.split(' ')[1].split('?')[1].split('&')
                    CONFIG_SSID = params[0].split('=')[1]
                    CONFIG_PWD = params[1].split('=')[1]
                    CONFIG_DONE = True
                    client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<h1>配网成功！设备正在连接...</h1>")
                except Exception:
                    pass
            else:
                html = """<html><head><meta charset='utf-8'></head><body>
                <h2>机器人 AI 配网中心</h2>
                <form method='get'>
                Wi-Fi 名称 (SSID): <input type='text' name='ssid'><br><br>
                Wi-Fi 密码 (Password): <input type='password' name='pwd'><br><br>
                <input type='submit' value='发送给机器人'>
                </form></body></html>"""
                client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html)
            client.close()
        except Exception:
            pass
    s.close()


def draw_bold_text(canvas, text, x, y, size=16):
    if size == 16:
        canvas.text(text, x, y, size=16)
        canvas.text(text, x+1, y, size=16)
        canvas.text(text, x, y+1, size=16)
        canvas.text(text, x+1, y+1, size=16)
    else:
        canvas.text(text, x, y, size=8)
        canvas.text(text, x+1, y, size=8)


def setup_wifi(canvas, touch, config_timeout=60):
    global CONFIG_DONE, CONFIG_SSID, CONFIG_PWD
    CONFIG_DONE = False

    wm = WiFiManager()
    ssid, pwd = wm._load_creds()

    if ssid:
        canvas.clear()
        canvas.rect(0, 0, 160, 96, color=0, fill=True)
        draw_bold_text(canvas, "CONNECTING...", 20, 35, size=16)
        canvas.show()
        if wm.connect(ssid, pwd):
            return wm

    wm.start_ap()
    _thread.start_new_thread(start_ap_server, ())
    start_time = time.time()

    while not CONFIG_DONE:
        canvas.clear()
        canvas.rect(0, 0, 160, 96, color=0, fill=True)
        canvas.rect(0, 0, 160, 20, color=1, fill=True)
        draw_bold_text(canvas, "WIFI SETUP", 35, 2, size=16)
        canvas.text("1. Connect WiFi:", 6, 26, size=8)
        draw_bold_text(canvas, AP_SSID, 12, 38, size=16)
        canvas.text("2. Go URL:", 6, 58, size=8)
        draw_bold_text(canvas, "192.168.1.1:8080", 12, 70, size=16)
        canvas.show()

        if touch and touch.is_pressed():
            touch.wait_release()
            print("用户手动跳过了网络配置")
            break

        if time.time() - start_time > config_timeout:
            print("配网超时，自动退出")
            break

        time.sleep(0.2)

    wm.stop_ap()

    if CONFIG_DONE:
        canvas.clear()
        canvas.rect(0, 0, 160, 96, color=0, fill=True)
        draw_bold_text(canvas, "Connecting...", 20, 35, size=16)
        canvas.show()

        if wm.connect(CONFIG_SSID, CONFIG_PWD):
            wm._save_creds(CONFIG_SSID, CONFIG_PWD)
            canvas.clear()
            canvas.rect(0, 0, 160, 96, color=0, fill=True)
            draw_bold_text(canvas, "SUCCESS!", 35, 35, size=16)
            canvas.show()
            time.sleep(1.5)

    return wm
