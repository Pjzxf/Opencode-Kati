from hardware import DisplayHAL, PHYS_W, PHYS_H, LOG_W, LOG_H, ZOOM

W = (255, 255, 255)
B = (0, 0, 0)

CHARS_PER_LINE = 15
LINE_HEIGHT = 10

class Canvas:
    def clear(self):
        DisplayHAL.clear(B)

    def show(self):
        DisplayHAL.show()

    def fill(self, color):
        DisplayHAL.clear(W if color else B)

    def fill_region(self, lx, ly, lw, lh, color=0):
        DisplayHAL.draw_rect(lx * ZOOM, ly * ZOOM, lw * ZOOM, lh * ZOOM,
                             color=W if color else B, fill=True)

    def rect(self, lx, ly, lw, lh, color=1, fill=True):
        DisplayHAL.draw_rect(lx * ZOOM, ly * ZOOM, lw * ZOOM, lh * ZOOM,
                             color=W if color else B, fill=fill)

    def px(self, lx, ly, color=1):
        DisplayHAL.draw_rect(lx * ZOOM, ly * ZOOM, ZOOM, ZOOM,
                             color=W if color else B, fill=True)

    def circle(self, lx, ly, lr, color=1, fill=False):
        DisplayHAL.draw_circle(lx * ZOOM, ly * ZOOM, lr * ZOOM,
                               color=W if color else B, fill=fill)

    def text(self, text, lx, ly, color=1, size=8):
        DisplayHAL.draw_string(text, lx * ZOOM, ly * ZOOM,
                               size=size, color=W if color else B)

    def draw_logical_text(self, text, lx, ly, color=1, size=8):
        lines = []
        while text:
            lines.append(text[:CHARS_PER_LINE])
            text = text[CHARS_PER_LINE:]

        y = ly
        for line in lines:
            self.text(line, lx, y, color=color, size=size)
            y += LINE_HEIGHT
        return y

    def bitmap(self, data, lx, ly, w, h, color=1):
        for r in range(h):
            for c in range(w):
                if r < len(data) and c < len(data[r]) and data[r][c]:
                    self.px(lx + c, ly + r, color)

    def hline(self, lx, ly, lw, color=1):
        self.rect(lx, ly, lw, 1, color=color)

    def vline(self, lx, ly, lh, color=1):
        self.rect(lx, ly, 1, lh, color=color)
