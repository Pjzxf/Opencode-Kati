import time
import random
from hardware import DisplayHAL, TouchHAL
from ui_canvas import Canvas
from pixel_avatar import AIChatInterface
from pixel_eyes import PixelEyesController

EXPRESSIONS = [
    "LOOK_LEFT", "LOOK_RIGHT", "LOOK_UP", "LOOK_DOWN",
    "SQUINT", "HAPPY", "BLINK",
    "WINK_LEFT", "WINK_RIGHT", "RAISE_LEFT",
    "CROSS_EYED", "DERP", "ASYNC_BLINK",
]

SIMPLE_EXPRESSIONS = [
    "LOOK_LEFT", "LOOK_RIGHT", "BLINK",
    "WINK_LEFT", "WINK_RIGHT", "HAPPY", "SQUINT",
]

class RobootApp:
    SPLIT = 2

    def __init__(self, mode=SPLIT):
        self.mode = mode
        DisplayHAL.init()
        self.canvas = Canvas()
        self.touch = TouchHAL()

        self._boot_wifi()

        self.ui = AIChatInterface(self.canvas)
        self.eyes = PixelEyesController()

        self.current_expr = "DEFAULT"
        self.expr_reset_time = 0
        self.auto_blink_enabled = True

    def _boot_wifi(self):
        try:
            from wifi_manager import setup_wifi
            self.wifi = setup_wifi(self.canvas, self.touch, config_timeout=60)
        except Exception as e:
            print("网络配网捕获到异常:", e)
            self.wifi = None

    def play_expression(self, expr, timeout_ms=3000):
        self.eyes.play_expression(expr)
        self.current_expr = expr
        self.expr_reset_time = time.ticks_ms() + timeout_ms

    def check_expression_timeout(self):
        if self.current_expr != "DEFAULT":
            if time.ticks_ms() > self.expr_reset_time:
                self.current_expr = "DEFAULT"
                self.eyes.play_expression("DEFAULT")

    def auto_blink(self):
        if self.auto_blink_enabled and self.current_expr == "DEFAULT":
            if random.randint(1, 100) <= 3:
                self.eyes.play_expression("BLINK")

    def handle_touch(self):
        if self.touch.is_pressed():
            self.touch.wait_release()
            expr = random.choice(SIMPLE_EXPRESSIONS)
            self.play_expression(expr, 2000)
            time.sleep(0.5)

    def run(self):
        self.ui.set_state("IDLE")
        self.eyes.play_expression("DEFAULT")
        tick = 0
        while True:
            self.check_expression_timeout()
            if tick % 10 == 0:
                self.handle_touch()
            self.auto_blink()
            tick += 1
            time.sleep(0.05)

if __name__ == "__main__":
    app = RobootApp(mode=RobootApp.SPLIT)
    app.run()
