import unittest

from fastapi.testclient import TestClient

from orientation_bot.main import Settings, create_app


class WebhookAppTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            telegram_bot_token="test-token",
            google_spreadsheet_id="sheet-123",
            google_service_account_file="/tmp/service-account.json",
            game_master_chat_id=-1001,
            announcement_chat_id=-2002,
            public_base_url="https://chaommunity-bot.example.com",
            webhook_secret="secret-123",
        )
        self.fake_api = FakeSheetsApi()
        self.fake_bot = FakeBotService()
        self.fake_telegram = FakeTelegramGateway()
        self.app = create_app(
            settings=self.settings,
            telegram_factory=lambda token: self.fake_telegram,
            sheets_api_factory=lambda filename: self.fake_api,
            score_store_factory=lambda api, spreadsheet_id: {"api": api, "spreadsheet_id": spreadsheet_id},
            bot_service_factory=lambda store, telegram, game_master_chat_id, announcement_chat_id, bot_username: self.fake_bot,
        )

    def test_health_reports_webhook_details(self):
        with TestClient(self.app) as client:
            response = client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "ok": True,
                "webhook_path": "/telegram/webhook",
                "webhook_url": "https://chaommunity-bot.example.com/telegram/webhook",
                "telegram_configured": True,
            },
            response.json(),
        )
        self.assertTrue(self.fake_api.ensure_workbook_called)
        self.assertTrue(self.fake_telegram.set_commands_called)
        self.assertEqual(
            [("https://chaommunity-bot.example.com/telegram/webhook", "secret-123")],
            self.fake_telegram.webhook_calls,
        )

    def test_webhook_rejects_invalid_secret(self):
        with TestClient(self.app) as client:
            response = client.post(
                "/telegram/webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
                json={"message": {"chat": {"id": -1001, "type": "group"}, "from": {"id": 7, "first_name": "GM"}, "text": "/help"}},
            )

        self.assertEqual(403, response.status_code)
        self.assertEqual([], self.fake_bot.handled_messages)
        self.assertEqual([], self.fake_telegram.replies)

    def test_webhook_processes_message_and_replies(self):
        self.fake_bot.response_text = "Command guide"

        with TestClient(self.app) as client:
            response = client.post(
                "/telegram/webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "secret-123"},
                json={
                    "message": {
                        "chat": {"id": -1001, "type": "group"},
                        "from": {"id": 7, "first_name": "Ernest"},
                        "text": "/help",
                    }
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"ok": True}, response.json())
        self.assertEqual(1, len(self.fake_bot.handled_messages))
        message = self.fake_bot.handled_messages[0]
        self.assertEqual(-1001, message.chat_id)
        self.assertEqual("group", message.chat_type)
        self.assertEqual(7, message.sender_id)
        self.assertEqual("Ernest", message.sender_name)
        self.assertEqual("/help", message.text)
        self.assertEqual([(-1001, "Command guide")], self.fake_telegram.replies)


class FakeSheetsApi:
    def __init__(self):
        self.ensure_workbook_called = False
        self.last_spreadsheet_id = None

    def ensure_workbook(self, spreadsheet_id):
        self.ensure_workbook_called = True
        self.last_spreadsheet_id = spreadsheet_id


class FakeTelegramGateway:
    def __init__(self):
        self.set_commands_called = False
        self.webhook_calls = []
        self.replies = []

    def set_commands(self):
        self.set_commands_called = True

    def set_webhook(self, url, secret_token):
        self.webhook_calls.append((url, secret_token))

    def username(self):
        return "test_bot"

    def reply(self, chat_id, text):
        self.replies.append((chat_id, text))


class FakeBotService:
    def __init__(self):
        self.handled_messages = []
        self.response_text = None

    async def handle(self, message):
        self.handled_messages.append(message)
        return self.response_text
