ALPHA_NUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

EXP = [0] * 512
LOG = [0] * 256
_v = 1
for _i in range(255):
    EXP[_i] = _v
    LOG[_v] = _i
    _v <<= 1
    if _v & 0x100:
        _v ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]

LOG[1] = 0

def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]

def _gf_poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i in range(len(p)):
        for j in range(len(q)):
            r[i + j] ^= _gf_mul(p[i], q[j])
    return r

def _rs_generator(nsym):
    g = [1]
    for i in range(nsym):
        g = _gf_poly_mul(g, [1, EXP[i]])
    return g

def _rs_encode(data, nsym):
    gen = _rs_generator(nsym)
    res = data + [0] * nsym
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return data + res[len(data):]

def _encode_alnum(text):
    bits = []
    i = 0
    while i + 1 < len(text):
        v1 = ALPHA_NUM.index(text[i])
        v2 = ALPHA_NUM.index(text[i + 1])
        v = v1 * 45 + v2
        for b in range(10, -1, -1):
            bits.append((v >> b) & 1)
        i += 2
    if i < len(text):
        v = ALPHA_NUM.index(text[i])
        for b in range(5, -1, -1):
            bits.append((v >> b) & 1)
    return bits

class QRCode:
    def __init__(self, version=3, mode="byte"):
        self.version = version
        self.size = 17 + version * 4
        self.capacity_map = {1: 26, 2: 44, 3: 70, 4: 100}
        self.ecc_map = {1: 7, 2: 10, 3: 15, 4: 20}
        self.mode = mode
        self.matrix = [[0] * self.size for _ in range(self.size)]

    def _place_finder(self, x, y):
        for r in range(8):
            for c in range(8):
                if 0 <= x + c < self.size and 0 <= y + r < self.size:
                    if r == 0 or r == 6 or c == 0 or c == 6:
                        self.matrix[y + r][x + c] = 1
                    elif 2 <= r <= 4 and 2 <= c <= 4:
                        self.matrix[y + r][x + c] = 1
                    else:
                        self.matrix[y + r][x + c] = 0

    def _place_align(self, x, y):
        if x + 2 < 0 or y + 2 < 0 or x - 2 >= self.size or y - 2 >= self.size:
            return
        for r in range(5):
            for c in range(5):
                cx, cy = x + c - 2, y + r - 2
                if 0 <= cx < self.size and 0 <= cy < self.size:
                    v = 1 if (r == 0 or r == 4 or c == 0 or c == 4 or (r == 2 and c == 2)) else 0
                    if self.matrix[cy][cx] == 0:
                        self.matrix[cy][cx] = v

    def _fill_reserved(self):
        s = self.size
        for i in range(s):
            self.matrix[i][8] = (i % 2 == 0) * 2
            self.matrix[8][i] = (i % 2 == 0) * 2
        self.matrix[s - 8][8] = 2

    def _place_modules(self, bits):
        s = self.size
        r = s - 1
        c = s - 1
        up = True
        idx = 0
        while c > 0:
            if c == 6:
                c -= 1
            cols = [c, c - 1]
            if up:
                rows = range(s - 1, -1, -1)
            else:
                rows = range(s)
            for row in rows:
                for col in cols:
                    if self.matrix[row][col] & 1 == 0 and self.matrix[row][col] < 2:
                        if idx < len(bits):
                            self.matrix[row][col] = bits[idx] | 2
                        else:
                            self.matrix[row][col] = 2
                        idx += 1
            up = not up
            c -= 2

    def _apply_mask(self, mask_idx):
        s = self.size
        mask_funcs = [
            lambda r, c: (r + c) % 2 == 0,
            lambda r, c: r % 2 == 0,
            lambda r, c: c % 3 == 0,
            lambda r, c: (r + c) % 3 == 0,
            lambda r, c: ((r // 2) + (c // 3)) % 2 == 0,
            lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
            lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
            lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
        ]
        fn = mask_funcs[mask_idx]
        for r in range(s):
            for c in range(s):
                if self.matrix[r][c] & 2 and not self.matrix[r][c] & 4:
                    self.matrix[r][c] = int(fn(r, c))

    def _place_format(self, mask_idx):
        ecl_bits = 0b01
        fmt = (ecl_bits << 3) | mask_idx
        fmt_bits = fmt << 10
        g = 0x537
        for i in range(4, -1, -1):
            if fmt_bits & (1 << (i + 10)):
                fmt_bits ^= g << i
        fmt_full = (fmt << 10) | (fmt_bits & 0x3FF)
        fmt_full ^= 0x5412

        s = self.size
        coords = []
        for i in range(6):
            coords.append((8, i))
        coords.append((8, 7))
        coords.append((8, 8))
        coords.append((7, 8))
        for i in range(5):
            coords.append((5 - i, 8))
        coords.append((s - 1, 8))
        for i in range(7):
            coords.append((8, s - i - 1))
        coords.append((8, s - 8))
        for i in range(8):
            coords.append((s - 8 + i, 8))

        for i, (c, r) in enumerate(coords):
            if 0 <= c < s and 0 <= r < s:
                self.matrix[r][c] = ((fmt_full >> (14 - i)) & 1) | 4

    def generate(self, text):
        caps = self.capacity_map[self.version]
        nsym = self.ecc_map[self.version]

        if self.mode == "byte":
            data_bits = [0, 1, 0, 0]
            cc = len(text)
            for b in range(7, -1, -1):
                data_bits.append((cc >> b) & 1)
            for ch in text:
                v = ord(ch)
                for b in range(7, -1, -1):
                    data_bits.append((v >> b) & 1)
        else:
            data_bits = [0, 0, 1, 0]
            cc = len(text)
            for b in range(8, -1, -1):
                data_bits.append((cc >> b) & 1)
            data_bits += _encode_alnum(text)

        codewords_needed = caps - nsym
        term_len = min(4, codewords_needed * 8 - len(data_bits))
        if term_len > 0:
            data_bits += [0] * term_len
        while len(data_bits) % 8 != 0:
            data_bits.append(0)

        data_bytes = []
        for i in range(0, len(data_bits), 8):
            v = 0
            for j in range(8):
                if i + j < len(data_bits):
                    v = (v << 1) | data_bits[i + j]
            data_bytes.append(v)

        pad = [0xEC, 0x11]
        pi = 0
        while len(data_bytes) < codewords_needed:
            data_bytes.append(pad[pi])
            pi = (pi + 1) % 2

        data_bytes = data_bytes[:codewords_needed]
        ecc_bytes = _rs_encode(data_bytes, nsym)
        final = data_bytes + ecc_bytes[len(data_bytes):]

        total_bits = []
        for b in final:
            for j in range(7, -1, -1):
                total_bits.append((b >> j) & 1)

        s = self.size
        self.matrix = [[0] * s for _ in range(s)]
        self._place_finder(0, 0)
        self._place_finder(s - 7, 0)
        self._place_finder(0, s - 7)
        self._fill_reserved()
        if self.version >= 2:
            for r in [6, s - 7]:
                for c in [6, s - 7]:
                    if not ((r < 9 and c < 9) or
                            (r < 9 and c > s - 9) or
                            (r > s - 9 and c < 9)):
                        self._place_align(c, r)
        self._place_modules(total_bits)
        self._apply_mask(2)
        self._place_format(2)
        for r in range(s):
            for c in range(s):
                self.matrix[r][c] = self.matrix[r][c] & 1
        return self.matrix

    def draw_on_canvas(self, canvas, lx, ly, scale=3):
        s = self.size
        qw = s * scale
        canvas.fill_region(lx, ly, qw, qw, color=1)
        for r in range(s):
            for c in range(s):
                if self.matrix[r][c]:
                    canvas.rect(lx + c * scale, ly + r * scale, scale, scale, color=0, fill=True)
