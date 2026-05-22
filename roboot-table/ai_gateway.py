import time
import json

LLM_API_URL = "https://api.your-ai.com/v1/chat/completions"
LLM_API_KEY = "YOUR_KEY"

ADUI_PROMPT = """You are an AI assistant for a pixel-art desktop device.
Respond with JSON only (no markdown). Use this schema:
{
  "meta": { "request_id": "...", "tts": "spoken reply" },
  "behavior": {
    "expression": "DEFAULT|LOOK_LEFT|LOOK_RIGHT|LOOK_UP|LOOK_DOWN|BLINK|SQUINT|HAPPY|WINK_LEFT|WINK_RIGHT|CROSS_EYED|DERP|RAISE_LEFT|CONFUSED",
    "sync_with_tts": true,
    "duration_ms": 3000
  }
}"""

class AIGateway:
    def __init__(self, ipc_queue=None):
        self.ipc_queue = ipc_queue
        self.session_id = 0

    def send_audio_and_get_response(self, audio_data):
        self.session_id += 1
        response = self._call_llm(audio_data)
        msg = self._parse_adui(response)
        if msg:
            self._dispatch(msg)
        return msg

    def _call_llm(self, audio_data):
        return {}

    def _parse_adui(self, response):
        behavior = response.get("behavior", {})
        if behavior:
            from ipc_protocol import CMD_PLAY_EXPR
            return {
                "cmd": CMD_PLAY_EXPR,
                "value": behavior.get("expression", "DEFAULT"),
                "timeout": behavior.get("duration_ms", 3000),
            }

        meta = response.get("meta", {})
        tts = meta.get("tts", "")
        if tts:
            from ipc_protocol import CMD_SET_TEXT
            return {"cmd": CMD_SET_TEXT, "value": tts}

        return None

    def _dispatch(self, msg):
        if self.ipc_queue:
            self.ipc_queue.send(json.dumps(msg))

    def send_text_query(self, text):
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": ADUI_PROMPT},
                {"role": "user", "content": text},
            ],
        }
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        response = self._http_post(LLM_API_URL, payload, headers)
        return self._parse_adui(response)

    def _http_post(self, url, payload, headers):
        return {}


if __name__ == "__main__":
    gateway = AIGateway()
    while True:
        user_input = input("> ")
        if user_input:
            result = gateway.send_text_query(user_input)
            if result:
                print(json.dumps(result, ensure_ascii=False))
        time.sleep(0.1)
