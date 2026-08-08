import json
from urllib.request import Request, urlopen


class TelegramGateway:
    def __init__(self, token):
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def publish(self, chat_id, html, pin):
        # Telegram HTML is a good fit for the small amount of emphasis in announcements.
        sent = self._call("sendMessage", {"chat_id": chat_id, "text": html, "parse_mode": "HTML"})
        if pin:
            self._call("pinChatMessage", {"chat_id": chat_id, "message_id": sent["message_id"], "disable_notification": True})

    def set_commands(self):
        self._call("setMyCommands", {"commands": [
            {"command": "score", "description": "Record a score: /score G1 GameA 8"},
            {"command": "leaderboard", "description": "Show the current leaderboard"},
            {"command": "help", "description": "Show score command help"},
        ]})

    def username(self):
        return self._call("getMe", {})["username"]

    def updates(self, offset):
        return self._call("getUpdates", {"offset": offset, "timeout": 30})

    def reply(self, chat_id, text):
        self._call("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

    def _call(self, method, payload):
        request = Request(f"{self.base_url}/{method}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=40) as response:
            body = json.load(response)
        if not body.get("ok"):
            raise RuntimeError(body.get("description", f"Telegram {method} failed"))
        return body["result"]
