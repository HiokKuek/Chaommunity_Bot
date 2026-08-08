import json
from urllib.request import Request, urlopen


class TelegramGateway:
    def __init__(self, token):
        self.base_url = f"https://api.telegram.org/bot{token}"

    @staticmethod
    def command_menu():
        return [
            {"command": "score", "description": "Record a game score — /score G1 GameA 8"},
            {"command": "secret", "description": "Record a secret mission — /secret G1"},
            {"command": "bonus", "description": "Add or remove a bonus mission — /bonus G1"},
            {"command": "resetmissions", "description": "Reset Secret Mission and Bonus Mission scores"},
            {"command": "resetscores", "description": "Reset every score for every group"},
            {"command": "leaderboard", "description": "Show live leaderboard"},
            {"command": "help", "description": "Show command guide"},
        ]

    async def publish(self, chat_id, text, pin):
        sent = self._call("sendMessage", {"chat_id": chat_id, "text": text})
        if pin:
            self._call("pinChatMessage", {"chat_id": chat_id, "message_id": sent["message_id"], "disable_notification": True})

    def set_commands(self):
        self._call("setMyCommands", {"commands": self.command_menu()})

    def set_webhook(self, url, secret_token):
        payload = {
            "url": url,
            "allowed_updates": ["message", "edited_message"],
            "drop_pending_updates": False,
        }
        if secret_token:
            payload["secret_token"] = secret_token
        self._call("setWebhook", payload)

    def webhook_info(self):
        return self._call("getWebhookInfo", {})

    def username(self):
        return self._call("getMe", {})["username"]

    def updates(self, offset):
        return self._call("getUpdates", {"offset": offset, "timeout": 30})

    def reply(self, chat_id, text):
        self._call("sendMessage", {"chat_id": chat_id, "text": text})

    def _call(self, method, payload):
        request = Request(f"{self.base_url}/{method}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=40) as response:
            body = json.load(response)
        if not body.get("ok"):
            raise RuntimeError(body.get("description", f"Telegram {method} failed"))
        return body["result"]
