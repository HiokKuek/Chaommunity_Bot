import unittest

from orientation_bot.telegram_api import TelegramGateway


class TelegramGatewayTests(unittest.TestCase):
    def test_reply_uses_html_parse_mode(self):
        gateway = RecordingTelegramGateway()

        gateway.reply(-1001, "🏆 <b>Leaderboard</b>")

        self.assertEqual(
            [
                (
                    "sendMessage",
                    {
                        "chat_id": -1001,
                        "text": "🏆 <b>Leaderboard</b>",
                        "parse_mode": "HTML",
                    },
                )
            ],
            gateway.calls,
        )


class RecordingTelegramGateway(TelegramGateway):
    def __init__(self):
        self.calls = []
        super().__init__("test-token")

    def _call(self, method, payload):
        self.calls.append((method, payload))
        return {"ok": True}
