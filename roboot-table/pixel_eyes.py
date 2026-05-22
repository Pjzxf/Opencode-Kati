import time
from hardware import DisplayHAL, ZOOM

W = (255, 255, 255)
B = (0, 0, 0)

class PixelEyesController:
    def __init__(self):
        # 逻辑坐标 (160x96, ZOOM=5 => 800x480 物理)
        self.left_cx = 63
        self.left_cy = 29
        self.right_cx = 96
        self.right_cy = 29
        self.eye_r = 15
        self.pupil_r = 7

        self.left_ox = 0
        self.left_oy = 0
        self.left_scale_y = 1.0
        self.left_cy_offset = 0

        self.right_ox = 0
        self.right_oy = 0
        self.right_scale_y = 1.0
        self.right_cy_offset = 0

        self.max_move = self.eye_r - self.pupil_r - 1

    def draw_eyes(self):
        z = ZOOM
        for cx, cy, off in [
            (self.left_cx, self.left_cy, self.left_cy_offset),
            (self.right_cx, self.right_cy, self.right_cy_offset),
        ]:
            px = (cx) * z
            py = (cy + off) * z
            pr = self.eye_r * z
            DisplayHAL.draw_circle(px, py, pr, color=W, fill=True)
            DisplayHAL.draw_circle(px, py, pr, color=B, fill=False, thickness=6)

    def draw_pupils(self):
        z = ZOOM
        clamp = lambda v: max(min(v, self.max_move), -self.max_move)

        for cx, cy, ox, oy, off, s in [
            (self.left_cx, self.left_cy, self.left_ox, self.left_oy,
             self.left_cy_offset, self.left_scale_y),
            (self.right_cx, self.right_cy, self.right_ox, self.right_oy,
             self.right_cy_offset, self.right_scale_y),
        ]:
            lx = clamp(ox)
            ly = clamp(oy)
            r = int(self.pupil_r * s)
            if r > 1:
                DisplayHAL.draw_ellipse(
                    (cx + lx) * z, (cy + ly + off) * z,
                    self.pupil_r * z, r * z,
                    color=B, fill=True, thickness=0, rotation=0
                )

    def render_frame(self):
        self.draw_eyes()
        self.draw_pupils()
        DisplayHAL.show()

    def reset_eyes(self):
        for attr in ["left_ox", "left_oy", "right_ox", "right_oy",
                      "left_cy_offset", "right_cy_offset"]:
            setattr(self, attr, 0)
        for attr in ["left_scale_y", "right_scale_y"]:
            setattr(self, attr, 1.0)

    def play_expression(self, expr):
        anim_exprs = ("ASYNC_BLINK", "BLINK", "WINK_LEFT", "WINK_RIGHT")
        if expr not in anim_exprs:
            self.reset_eyes()

        if expr == "LOOK_LEFT":
            self.left_ox = self.right_ox = -6
        elif expr == "LOOK_RIGHT":
            self.left_ox = self.right_ox = 6
        elif expr == "LOOK_UP":
            self.left_oy = self.right_oy = -6
        elif expr == "LOOK_DOWN":
            self.left_oy = self.right_oy = 5
        elif expr == "SQUINT":
            self.left_scale_y = self.right_scale_y = 0.2
        elif expr == "HAPPY":
            self.left_oy = self.right_oy = -2
            self.left_scale_y = self.right_scale_y = 0.5
        elif expr == "BLINK":
            self.left_scale_y = self.right_scale_y = 0.0
            self.render_frame()
            time.sleep(0.01)
            for s in (0.4, 0.8, 1.0):
                self.left_scale_y = self.right_scale_y = s
                self.render_frame()
            return
        elif expr == "WINK_LEFT":
            self.left_scale_y = 0.0
            self.render_frame()
            time.sleep(0.02)
            for s in (0.4, 0.8, 1.0):
                self.left_scale_y = s
                self.render_frame()
            return
        elif expr == "WINK_RIGHT":
            self.right_scale_y = 0.0
            self.render_frame()
            time.sleep(0.02)
            for s in (0.4, 0.8, 1.0):
                self.right_scale_y = s
                self.render_frame()
            return
        elif expr == "RAISE_LEFT":
            self.left_cy_offset = -4
            self.left_scale_y = 1.1
        elif expr == "CROSS_EYED":
            self.left_ox = 5
            self.right_ox = -5
        elif expr == "DERP":
            self.left_ox = -6
            self.right_ox = 6
        elif expr == "CONFUSED":
            self.left_cy_offset = -3
            self.left_scale_y = 1.1
        elif expr == "ASYNC_BLINK":
            self.left_scale_y = 0.0
            self.render_frame()
            for s in (0.5, 1.0):
                self.left_scale_y = s
                self.render_frame()
            self.right_scale_y = 0.0
            self.render_frame()
            for s in (0.5, 1.0):
                self.right_scale_y = s
                self.render_frame()
            return
        else:
            self.reset_eyes()

        self.render_frame()
