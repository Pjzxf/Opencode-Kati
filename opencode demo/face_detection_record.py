'''
实验名称：人脸检测 + 拍照 + 录像
实验平台：01Studio CanMV K230 (SD卡启动, 3.5寸MIPI屏)
说明：实时人脸检测 + 短按KEY拍照 + 长按2秒录像(录像中再次长按停止)
'''

from media.sensor import Sensor
from media.display import Display
from media.media import MediaManager
from media.mp4format import Mp4Container, Mp4CfgStr
from libs.PipeLine import PipeLine
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import nncase_runtime as nn
import ulab.numpy as np
import time
import utime
import os
import gc
import aidemo
from machine import Pin, FPIOA


def ALIGN_UP(x, align):
    return ((x + align - 1) // align) * align


PICTURE_DIR = "/sdcard/picture"
VIDEO_DIR = "/sdcard/video"
KEY_GPIO = 21
LED_GPIO = 52
LONG_PRESS_MS = 2000

STATE_IDLE = 0
STATE_REC = 1

KMODEL_PATH = "/sdcard/examples/kmodel/face_detection_320.kmodel"
ANCHORS_PATH = "/sdcard/examples/utils/prior_data_320.bin"


class FaceDetectionApp(AIBase):
    def __init__(self, kmodel_path, model_input_size, anchors,
                 confidence_threshold=0.5, nms_threshold=0.2,
                 rgb888p_size=(1920, 1080), display_size=(800, 480),
                 debug_mode=0):
        super().__init__(kmodel_path, model_input_size, list(rgb888p_size), debug_mode)
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.anchors = anchors
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8)

    def config_preprocess(self, input_image_size=None):
        ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
        top, bottom, left, right = self._get_padding_param()
        self.ai2d.pad([0, 0, 0, 0, top, bottom, left, right], 0, [104, 117, 123])
        self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
        self.ai2d.build(
            [1, 3, ai2d_input_size[1], ai2d_input_size[0]],
            [1, 3, self.model_input_size[1], self.model_input_size[0]],
        )

    def postprocess(self, results):
        post_ret = aidemo.face_det_post_process(
            self.confidence_threshold, self.nms_threshold,
            self.model_input_size[1], self.anchors,
            self.rgb888p_size, results,
        )
        if len(post_ret) == 0:
            return post_ret
        return post_ret[0]

    def draw_result(self, pl, dets):
        if dets:
            pl.osd_img.clear()
            for det in dets:
                x, y, w, h = map(lambda v: int(round(v, 0)), det[:4])
                x = x * self.display_size[0] // self.rgb888p_size[0]
                y = y * self.display_size[1] // self.rgb888p_size[1]
                w = w * self.display_size[0] // self.rgb888p_size[0]
                h = h * self.display_size[1] // self.rgb888p_size[1]
                pl.osd_img.draw_rectangle(x, y, w, h, color=(255, 255, 0, 255), thickness=2)
        else:
            pl.osd_img.clear()

    def _get_padding_param(self):
        dst_w = self.model_input_size[0]
        dst_h = self.model_input_size[1]
        ratio_w = dst_w / self.rgb888p_size[0]
        ratio_h = dst_h / self.rgb888p_size[1]
        ratio = min(ratio_w, ratio_h)
        new_w = int(ratio * self.rgb888p_size[0])
        new_h = int(ratio * self.rgb888p_size[1])
        dw = (dst_w - new_w) / 2
        dh = (dst_h - new_h) / 2
        top = int(round(0))
        bottom = int(round(dh * 2 + 0.1))
        left = int(round(0))
        right = int(round(dw * 2 - 0.1))
        return top, bottom, left, right


def _ensure_dir(path):
    try:
        os.stat(path)
    except OSError:
        os.mkdir(path)


def _timestamp():
    t = utime.localtime()
    return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])


def _frame_to_rgb565_bytes(frame_np):
    h, w = frame_np.shape[1], frame_np.shape[2]
    hw = h * w
    r_flat = bytes(frame_np[0].reshape(-1))
    g_flat = bytes(frame_np[1].reshape(-1))
    b_flat = bytes(frame_np[2].reshape(-1))
    data = bytearray(hw * 2)
    for i in range(hw):
        r5 = r_flat[i] >> 3
        g6 = g_flat[i] >> 2
        b5 = b_flat[i] >> 3
        pixel = (r5 << 11) | (g6 << 5) | b5
        data[i * 2] = pixel & 0xFF
        data[i * 2 + 1] = (pixel >> 8) & 0xFF
    return data, w, h


def main():
    _ensure_dir(PICTURE_DIR)
    _ensure_dir(VIDEO_DIR)

    fpioa = FPIOA()
    fpioa.set_function(KEY_GPIO, FPIOA.GPIO21)
    fpioa.set_function(LED_GPIO, FPIOA.GPIO52)
    key = Pin(KEY_GPIO, Pin.IN, Pin.PULL_UP)
    led = Pin(LED_GPIO, Pin.OUT)
    led.value(1)

    display_size = (800, 480)
    rgb888p_size = (1920, 1080)

    anchors = np.fromfile(ANCHORS_PATH, dtype=np.float).reshape((4200, 4))

    face_det = FaceDetectionApp(
        KMODEL_PATH, model_input_size=[320, 320], anchors=anchors,
        confidence_threshold=0.5, nms_threshold=0.2,
        rgb888p_size=rgb888p_size, display_size=display_size, debug_mode=0,
    )
    face_det.config_preprocess()

    sensor = Sensor(width=rgb888p_size[0], height=rgb888p_size[1])
    pl = PipeLine(
        rgb888p_size=list(rgb888p_size),
        display_size=list(display_size),
        display_mode="st7701",
    )
    pl.create(sensor)

    clock = time.clock()
    state = STATE_IDLE
    mp4_muxer = None
    mp4_path = None
    key_down = False
    press_time = 0
    long_press_triggered = False
    photo_msg_end = 0
    preview_overlay = None

    while True:
        clock.tick()
        now = time.ticks_ms()
        pressed = key.value() == 0

        if state == STATE_REC:
            mp4_muxer.Process()

            if pressed and not key_down:
                press_time = now
                key_down = True
                long_press_triggered = False

            if not pressed and key_down:
                elapsed = time.ticks_diff(now, press_time)
                if elapsed >= LONG_PRESS_MS:
                    _stop_recording(mp4_muxer)
                    mp4_muxer = None
                    mp4_path = None
                    state = STATE_IDLE
                    led.value(1)
                    print("recording stopped")
                    pl.create(sensor)
                    face_det.config_preprocess()
                key_down = False
            continue

        img = pl.get_frame()
        res = face_det.run(img)

        if pressed and not key_down:
            press_time = now
            key_down = True
            long_press_triggered = False

        if key_down and pressed and not long_press_triggered:
            if time.ticks_diff(now, press_time) >= LONG_PRESS_MS:
                long_press_triggered = True
                pl.destroy()
                led.value(0)
                mp4_muxer, mp4_path = _start_recording()
                state = STATE_REC
                print("recording:", mp4_path)

        if not pressed and key_down:
            key_down = False
            if not long_press_triggered:
                print("photo start")
                t0 = time.ticks_ms()
                data, w, h = _frame_to_rgb565_bytes(img[:, ::3, ::3])
                import image
                preview_img = image.Image(w, h, image.RGB565, data=bytes(data))
                fname = PICTURE_DIR + "/" + _timestamp() + ".jpg"
                preview_img.save(fname)
                t1 = time.ticks_ms()
                print("photo:", fname, "took", time.ticks_diff(t1, t0), "ms")

                down = img[:, ::3, ::3]
                h2, w2 = down.shape[1], down.shape[2]
                ox = (display_size[0] - w2) // 2
                oy = (display_size[1] - h2) // 2
                b_plane = down[2]
                g_plane = down[1]
                r_plane = down[0]
                total_px = display_size[0] * display_size[1]
                buf = bytearray(total_px * 4)
                for i in range(3, total_px * 4, 4):
                    buf[i] = 255
                ov_np = np.frombuffer(buf, dtype=np.uint8).reshape((display_size[1], display_size[0], 4))
                for y in range(h2):
                    ov_np[oy + y, ox:ox + w2, 0] = b_plane[y, :]
                    ov_np[oy + y, ox:ox + w2, 1] = g_plane[y, :]
                    ov_np[oy + y, ox:ox + w2, 2] = r_plane[y, :]
                preview_overlay = image.Image(display_size[0], display_size[1], image.ARGB8888, alloc=image.ALLOC_REF, data=ov_np)
                photo_msg_end = time.ticks_ms() + 5000
                continue

        face_det.draw_result(pl, res)
        if photo_msg_end and time.ticks_ms() < photo_msg_end:
            pl.osd_img.clear()
            pl.osd_img.copy_from(preview_overlay)
        elif photo_msg_end:
            photo_msg_end = 0
            preview_overlay = None
        pl.show_image()
        gc.collect()


def _start_recording():
    path = VIDEO_DIR + "/" + _timestamp() + ".mp4"
    mp4_muxer = Mp4Container()
    mp4_cfg = Mp4CfgStr(mp4_muxer.MP4_CONFIG_TYPE_MUXER)
    mp4_cfg.SetMuxerCfg(path, mp4_muxer.MP4_CODEC_ID_H265, 1280, 720,
                         mp4_muxer.MP4_CODEC_ID_G711U)
    mp4_muxer.Create(mp4_cfg)
    mp4_muxer.Start()
    return mp4_muxer, path


def _stop_recording(mp4_muxer):
    mp4_muxer.Stop()
    mp4_muxer.Destroy()
    print("video saved")


main()
