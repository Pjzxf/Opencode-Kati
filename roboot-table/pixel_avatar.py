import time
from ui_canvas import Canvas, W, B

ROBOT_AVATAR = [
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,1,1,1,0,0,0,0,0,1,1,1,0,0,1],
    [1,0,1,1,1,0,0,0,0,0,1,1,1,0,0,1],
    [1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,1],
    [1,0,0,1,1,1,1,1,1,1,1,1,1,0,0,1],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
]

AVATAR_POS_X = 125
AVATAR_POS_Y = 10
TEXT_AREA_X = 5
TEXT_AREA_Y = 15
LEFT_W = 120
VIEW_H = 96
WAVE_START = 5
WAVE_END = 115
WAVE_STEP = 4
WAVE_Y_BASE = 80

class AIChatInterface:
    def __init__(self, canvas):
        self.canvas = canvas
        self.current_state = "IDLE"
        self.display_text = "Hi! 唤醒我说说话吧..."

    def draw_avatar(self):
        self.canvas.bitmap(ROBOT_AVATAR, AVATAR_POS_X, AVATAR_POS_Y, 16, 8, color=1)

    def draw_text_stream(self):
        self.canvas.draw_logical_text(self.display_text, TEXT_AREA_X, TEXT_AREA_Y, color=1, size=8)

    def draw_listening_wave(self, mic_level):
        for i in range(WAVE_START, WAVE_END, WAVE_STEP):
            h = (i % (mic_level + 1)) * 2
            self.canvas.rect(i, WAVE_Y_BASE - h // 2, 2, h, color=1)

    def update_ui(self, mic_level=0, full_refresh=True):
        if full_refresh:
            self.canvas.clear()
            self.draw_avatar()
        else:
            self.canvas.fill_region(0, 0, LEFT_W, VIEW_H, color=0)

        s = self.current_state
        if s == "IDLE" or s == "SPEAKING":
            self.draw_text_stream()
        elif s == "LISTENING":
            self.canvas.text("正在听...", TEXT_AREA_X, 10, color=1, size=8)
            self.draw_listening_wave(mic_level)
        elif s == "THINKING":
            self.canvas.text("思考中...", TEXT_AREA_X, 10, color=1, size=8)
            dots = int(time.time() * 2) % 4
            self.canvas.text("." * dots, 50, 10, color=1, size=8)

        self.canvas.show()

    def set_state(self, state, text=""):
        self.current_state = state
        if text:
            self.display_text = text
        self.update_ui(full_refresh=True)

    def type_text(self, text, char_interval=0.1):
        self.current_state = "SPEAKING"
        for i in range(1, len(text) + 1):
            self.display_text = text[:i]
            self.update_ui(full_refresh=False)
            time.sleep(char_interval)
        self.current_state = "IDLE"
