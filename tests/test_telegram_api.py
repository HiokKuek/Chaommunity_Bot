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

    def test_set_commands_includes_mission_commands(self):
        gateway = RecordingTelegramGateway()

        gateway.set_commands()

        self.assertEqual(
            [
                (
                    "setMyCommands",
                    {
                        "commands": [
                            {"command": "score", "description": "Record a score: /score G1 GameA 8"},
                            {"command": "secret", "description": "Record a secret mission: /secret G1"},
                            {"command": "bonus", "description": "Add or remove a bonus mission: /bonus G1"},
                            {"command": "resetmissions", "description": "Reset all Secret Mission and Bonus Mission scores"},
                            {"command": "leaderboard", "description": "Show the current leaderboard"},
                            {"command": "help", "description": "Show score and mission help"},
                        ]
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
