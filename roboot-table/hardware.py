import time
from media.display import Display
from media.media import MediaManager
import image
from machine import TOUCH

PHYS_W = 800
PHYS_H = 480

LOG_W = 160
LOG_H = 96
ZOOM = 5

class DisplayHAL:
    _fb = None

    @classmethod
    def init(cls):
        Display.init(Display.ST7701, to_ide=True)
        MediaManager.init()
        cls._fb = image.Image(PHYS_W, PHYS_H, image.RGB565)

    @classmethod
    def fb(cls):
        return cls._fb

    @classmethod
    def show(cls):
        Display.show_image(cls._fb)

    @classmethod
    def clear(cls, color=(0, 0, 0)):
        cls._fb.draw_rectangle(0, 0, PHYS_W, PHYS_H, color=color, fill=True)

    @classmethod
    def draw_pixel(cls, x, y, color=(255, 255, 255)):
        cls._fb.draw_line(x, y, x, y, color=color, thickness=1)

    @classmethod
    def draw_rect(cls, x, y, w, h, color=(255, 255, 255), fill=True):
        cls._fb.draw_rectangle(x, y, w, h, color=color, fill=fill)

    @classmethod
    def draw_circle(cls, cx, cy, r, color=(255, 255, 255), fill=False, thickness=1):
        cls._fb.draw_circle(cx, cy, r, color=color, fill=fill, thickness=thickness)

    @classmethod
    def draw_ellipse(cls, cx, cy, rx, ry, color=(255, 255, 255), fill=False, thickness=1, rotation=0):
        cls._fb.draw_ellipse(cx, cy, rx, ry, rotation, color=color, fill=fill, thickness=thickness)

    @classmethod
    def draw_string(cls, text, x, y, size=8, color=(255, 255, 255)):
        cls._fb.draw_string_advanced(x, y, size, text, color=color)


class TouchHAL:
    def __init__(self):
        self._tp = TOUCH(0)

    def read(self):
        return self._tp.read()

    def is_pressed(self):
        return self._tp.read() != ()

    def wait_press(self, poll_ms=50):
        while True:
            if self.is_pressed():
                return
            time.sleep_ms(poll_ms)

    def wait_release(self, poll_ms=50):
        while True:
            if not self.is_pressed():
                return
            time.sleep_ms(poll_ms)

    def get_first_point(self):
        p = self._tp.read()
        if p:
            return p[0].x, p[0].y
        return None, None

    def get_logical_point(self):
        x, y = self.get_first_point()
        if x is None:
            return None, None
        return x // ZOOM, y // ZOOM


class AudioHAL:
    @staticmethod
    def beep(freq=1000, duration_ms=200):
        pass

    @staticmethod
    def play_8bit(melody):
        pass
