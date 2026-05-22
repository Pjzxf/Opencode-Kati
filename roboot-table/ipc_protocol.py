import json

ADUI_VERSION = "1.2"

EXPR_NONE = "DEFAULT"
EXPR_LOOK_LEFT = "LOOK_LEFT"
EXPR_LOOK_RIGHT = "LOOK_RIGHT"
EXPR_LOOK_UP = "LOOK_UP"
EXPR_LOOK_DOWN = "LOOK_DOWN"
EXPR_BLINK = "BLINK"
EXPR_SQUINT = "SQUINT"
EXPR_HAPPY = "HAPPY"
EXPR_WINK_LEFT = "WINK_LEFT"
EXPR_WINK_RIGHT = "WINK_RIGHT"
EXPR_RAISE_LEFT = "RAISE_LEFT"
EXPR_CROSS_EYED = "CROSS_EYED"
EXPR_DERP = "DERP"
EXPR_ASYNC_BLINK = "ASYNC_BLINK"
EXPR_CONFUSED = "CONFUSED"

UI_STATE_IDLE = "IDLE"
UI_STATE_LISTENING = "LISTENING"
UI_STATE_THINKING = "THINKING"
UI_STATE_SPEAKING = "SPEAKING"

WIDGET_NONE = "none"
WIDGET_TIMER = "PixelWidget_WideTimer"
WIDGET_CAMERA = "PixelWidget_Camera"

CMD_PLAY_EXPR = "PLAY_EXPR"
CMD_SET_UI_STATE = "SET_UI_STATE"
CMD_SPAWN_WIDGET = "SPAWN_WIDGET"
CMD_CLEAR_WIDGET = "CLEAR_WIDGET"
CMD_PLAY_AUDIO = "PLAY_AUDIO"
CMD_SET_TEXT = "SET_TEXT"
CMD_TEXT_APPEND = "TEXT_APPEND"

class ADUIMessage:
    def __init__(self, cmd, value=None, timeout=None, params=None):
        self.cmd = cmd
        self.value = value
        self.timeout = timeout
        self.params = params if params else {}

    def encode(self):
        msg = {"cmd": self.cmd, "value": self.value, "timeout": self.timeout}
        if self.params:
            msg["params"] = self.params
        return json.dumps(msg)

    @staticmethod
    def decode(data):
        try:
            obj = json.loads(data)
            return ADUIMessage(
                cmd=obj.get("cmd"),
                value=obj.get("value"),
                timeout=obj.get("timeout"),
                params=obj.get("params", {})
            )
        except Exception:
            return None

    @staticmethod
    def from_cloud(json_str):
        try:
            obj = json.loads(json_str)
            meta = obj.get("meta", {})
            control = obj.get("control", {})
            ui = obj.get("ui", {})
            behavior = obj.get("behavior", {})

            if behavior:
                return ADUIMessage(
                    cmd=CMD_PLAY_EXPR,
                    value=behavior.get("expression", EXPR_NONE),
                    timeout=behavior.get("duration_ms", 3000),
                    params={"sync_tts": behavior.get("sync_with_tts", False)}
                )

            if ui and ui.get("type"):
                return ADUIMessage(
                    cmd=CMD_SPAWN_WIDGET,
                    value=ui["type"],
                    params={
                        "style": ui.get("style", {}),
                        "layout": ui.get("layout", {}),
                        "text": meta.get("tts", ""),
                    }
                )

            if control and control.get("native_action"):
                return ADUIMessage(
                    cmd=control["native_action"],
                    params=control.get("params", {})
                )

            return ADUIMessage(cmd=CMD_SET_TEXT, value=meta.get("tts", ""))
        except Exception:
            return None
