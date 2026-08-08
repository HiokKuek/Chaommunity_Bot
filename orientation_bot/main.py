import asyncio
import os

from orientation_bot.google_api import GoogleSheetsApi
from orientation_bot.service import BotService, IncomingMessage
from orientation_bot.sheets_store import GoogleSheetsScoreStore
from orientation_bot.telegram_api import TelegramGateway


async def run():
    token = _required("TELEGRAM_BOT_TOKEN")
    spreadsheet_id = _required("GOOGLE_SPREADSHEET_ID")
    game_master_chat_id = int(_required("GAME_MASTER_CHAT_ID"))
    announcement_chat_id = int(_required("ANNOUNCEMENT_CHAT_ID"))
    api = GoogleSheetsApi.from_service_account_file(_required("GOOGLE_SERVICE_ACCOUNT_FILE"))
    api.ensure_workbook(spreadsheet_id)
    telegram = TelegramGateway(token)
    telegram.set_commands()
    bot = BotService(GoogleSheetsScoreStore(api, spreadsheet_id), telegram, game_master_chat_id, announcement_chat_id)
    offset = 0
    while True:
        for update in telegram.updates(offset):
            offset = update["update_id"] + 1
            telegram_message = update.get("message")
            if not telegram_message or "text" not in telegram_message:
                continue
            chat = telegram_message["chat"]
            sender = telegram_message.get("from", {})
            message = IncomingMessage(chat["id"], chat["type"], sender.get("id", 0), sender.get("first_name", "Game Master"), telegram_message["text"])
            reply = await bot.handle(message)
            if reply:
                telegram.reply(chat["id"], reply)
        await asyncio.sleep(0)


def _required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


if __name__ == "__main__":
    asyncio.run(run())
