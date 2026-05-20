from media.sensor import *
from libs.PipeLine import PipeLine
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import nncase_runtime as nn
import ulab.numpy as np
import time
import gc
import os
import aidemo
import utime
from machine import Pin
from machine import FPIOA


class FaceDetectionApp(AIBase):
    def __init__(
        self,
        kmodel_path,
        model_input_size,
        anchors,
        confidence_threshold=0.5,
        nms_threshold=0.2,
        rgb888p_size=(1920, 1080),
        display_size=(800, 480),
        debug_mode=0,
    ):
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
        self.ai2d.set_ai2d_dtype(
            nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8
        )

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
            self.confidence_threshold,
            self.nms_threshold,
            self.model_input_size[1],
            self.anchors,
            self.rgb888p_size,
            results,
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
                pl.osd_img.draw_rectangle(
                    x, y, w, h, color=(255, 255, 0, 255), thickness=2
                )
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


def _display_config(display):
    if display == "hdmi":
        return "hdmi", (1920, 1080), (1920, 1080)
    if display == "lcd3_5":
        return "st7701", (800, 480), (1920, 1080)
    if display == "lcd2_4":
        return "st7701", (640, 480), (1280, 960)
    raise ValueError("display must be one of: hdmi, lcd3_5, lcd2_4")


def _load_anchors(path):
    anchors = np.fromfile(path, dtype=np.float)
    anchors = anchors.reshape((4200, 4))
    return anchors


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _ensure_dir(path):
    if _exists(path):
        return
    os.mkdir(path)


def _timestamp_yyyymmddhhmm():
    t = utime.localtime()
    return (
        "{:04d}{:02d}{:02d}{:02d}{:02d}".format(t[0], t[1], t[2], t[3], t[4])
    )


def _take_photo(sensor, filename):
    photo = sensor.snapshot()
    photo.save(filename)


def main():
    display = "lcd3_5"
    display_mode, display_size, rgb888p_size = _display_config(display)

    kmodel_path = "/sdcard/examples/kmodel/face_detection_320.kmodel"
    anchors_path = "/sdcard/examples/utils/prior_data_320.bin"
    picture_dir = "/sdcard/picture"

    _ensure_dir(picture_dir)

    if not _exists(kmodel_path):
        raise OSError("kmodel not found: " + kmodel_path)
    if not _exists(anchors_path):
        raise OSError("anchors not found: " + anchors_path)

    anchors = _load_anchors(anchors_path)

    fpioa = FPIOA()
    fpioa.set_function(21, FPIOA.GPIO21)
    key = Pin(21, Pin.IN, Pin.PULL_UP)

    sensor = Sensor(width=rgb888p_size[0], height=rgb888p_size[1])
    pl = PipeLine(
        rgb888p_size=list(rgb888p_size),
        display_size=list(display_size),
        display_mode=display_mode,
    )
    pl.create(sensor)

    face_det = FaceDetectionApp(
        kmodel_path,
        model_input_size=[320, 320],
        anchors=anchors,
        confidence_threshold=0.5,
        nms_threshold=0.2,
        rgb888p_size=rgb888p_size,
        display_size=display_size,
        debug_mode=0,
    )
    face_det.config_preprocess()

    clock = time.clock()
    while True:
        clock.tick()
        img = pl.get_frame()
        res = face_det.run(img)
        if key.value() == 0:
            time.sleep_ms(10)
            if key.value() == 0:
                filename = picture_dir + "/" + _timestamp_yyyymmddhhmm() + ".jpg"
                _take_photo(sensor, filename)
                while not key.value():
                    pass
        if res:
            print(res)
        face_det.draw_result(pl, res)
        pl.show_image()
        gc.collect()
        print(clock.fps())


main()
