'''
实验名称：触摸水波纹效果
实验平台：01Studio CanMV K230
说明：点击3.5寸MIPI屏幕出现水波纹扩散效果，支持多点触摸
'''

from media.sensor import Sensor
from media.display import Display
from media.media import MediaManager
from machine import TOUCH
import time

DISPLAY_W = 800
DISPLAY_H = 480

RIPPLE_SPEED = 350
RING_COUNT = 6
RING_SPACING = 16

ripples = []

def add_ripple(x, y):
    ripples.append({
        'x': x, 'y': y,
        'start': time.ticks_ms(),
        'lifetime': 1800
    })

def draw_ripples(img):
    now = time.ticks_ms()
    alive = []

    for r in ripples:
        elapsed = time.ticks_diff(now, r['start'])
        if elapsed > r['lifetime']:
            continue
        alive.append(r)

        progress = elapsed / r['lifetime']
        max_radius = 500
        radius = progress * max_radius
        cx, cy = int(r['x']), int(r['y'])

        for ring in range(RING_COUNT):
            r_pos = radius - ring * RING_SPACING
            if r_pos < 3:
                continue

            age_fade = max(0, 1.0 - progress * 0.9)
            dist_fade = max(0, 1.0 - ring / RING_COUNT)
            intensity = int(255 * age_fade * dist_fade)
            color = (int(intensity * 0.4), int(intensity * 0.6), intensity)

            img.draw_circle(cx, cy, int(r_pos), color=color, thickness=2)

    ripples[:] = alive


def main():
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_W, height=DISPLAY_H)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.ST7701, to_ide=True)
    MediaManager.init()
    sensor.run()

    tp = TOUCH(0)

    clock = time.clock()

    while True:
        clock.tick()
        img = sensor.snapshot()

        touch_data = tp.read()
        if touch_data != ():
            for i in range(len(touch_data)):
                add_ripple(touch_data[i].x, touch_data[i].y)

        draw_ripples(img)
        Display.show_image(img)


main()
