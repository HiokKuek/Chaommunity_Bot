import unittest

from orientation_bot.telegram_api import TelegramGateway


class TelegramGatewayTests(unittest.TestCase):
    def test_reply_sends_plain_text(self):
        gateway = RecordingTelegramGateway()

        gateway.reply(-1001, "🏆 Leaderboard — Live Scores")

        self.assertEqual(
            [
                (
                    "sendMessage",
                    {
                        "chat_id": -1001,
                        "text": "🏆 Leaderboard — Live Scores",
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
                            {"command": "score", "description": "Record a game score — /score G1 GameA 8"},
                            {"command": "secret", "description": "Record a secret mission — /secret G1"},
                            {"command": "bonus", "description": "Add or remove a bonus mission — /bonus G1"},
                            {"command": "resetmissions", "description": "Reset Secret Mission and Bonus Mission scores"},
                            {"command": "resetscores", "description": "Reset every score for every group"},
                            {"command": "leaderboard", "description": "Show live leaderboard"},
                            {"command": "help", "description": "Show command guide"},
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
