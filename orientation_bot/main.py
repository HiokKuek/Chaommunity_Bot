import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Header, HTTPException, Request

from orientation_bot.google_api import GoogleSheetsApi
from orientation_bot.service import BotService, IncomingMessage
from orientation_bot.sheets_store import GoogleSheetsScoreStore
from orientation_bot.telegram_api import TelegramGateway


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    google_spreadsheet_id: str
    google_service_account_file: str
    game_master_chat_id: int
    announcement_chat_id: int
    public_base_url: str
    webhook_secret: str

    @property
    def webhook_path(self) -> str:
        return "/telegram/webhook"

    @property
    def webhook_url(self) -> str:
        return self.public_base_url.rstrip("/") + self.webhook_path

    @classmethod
    def from_env(cls):
        return cls(
            telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
            google_spreadsheet_id=_required("GOOGLE_SPREADSHEET_ID"),
            google_service_account_file=_required("GOOGLE_SERVICE_ACCOUNT_FILE"),
            game_master_chat_id=int(_required("GAME_MASTER_CHAT_ID")),
            announcement_chat_id=int(_required("ANNOUNCEMENT_CHAT_ID")),
            public_base_url=_required("PUBLIC_BASE_URL"),
            webhook_secret=_required("WEBHOOK_SECRET"),
        )


@dataclass
class Runtime:
    settings: Settings
    telegram: TelegramGateway | None = None
    bot: BotService | None = None


def create_app(
    settings=None,
    telegram_factory=TelegramGateway,
    sheets_api_factory=GoogleSheetsApi.from_service_account_file,
    score_store_factory=GoogleSheetsScoreStore,
    bot_service_factory=BotService,
):
    settings = settings or Settings.from_env()
    runtime = Runtime(settings=settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        api = sheets_api_factory(settings.google_service_account_file)
        api.ensure_workbook(settings.google_spreadsheet_id)

        telegram = telegram_factory(settings.telegram_bot_token)
        telegram.set_commands()
        telegram.set_webhook(settings.webhook_url, settings.webhook_secret)

        runtime.telegram = telegram
        runtime.bot = bot_service_factory(
            score_store_factory(api, settings.google_spreadsheet_id),
            telegram,
            settings.game_master_chat_id,
            settings.announcement_chat_id,
            bot_username=telegram.username(),
        )
        yield

    app = FastAPI(title="Orientation Score Bot", lifespan=lifespan)
    app.state.runtime = runtime

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "webhook_path": settings.webhook_path,
            "webhook_url": settings.webhook_url,
            "telegram_configured": bool(settings.telegram_bot_token),
        }

    @app.post(settings.webhook_path)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ):
        if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

        update = await request.json()
        telegram_message = update.get("message") or update.get("edited_message")
        if not telegram_message or "text" not in telegram_message:
            return {"ok": True}

        chat = telegram_message.get("chat") or {}
        sender = telegram_message.get("from") or {}
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        text = telegram_message.get("text")
        if chat_id is None or chat_type is None or text is None:
            return {"ok": True}

        bot = runtime.bot
        telegram = runtime.telegram
        if bot is None or telegram is None:
            raise HTTPException(status_code=503, detail="Bot is still starting up")

        message = IncomingMessage(
            chat_id=chat_id,
            chat_type=chat_type,
            sender_id=sender.get("id", 0),
            sender_name=sender.get("first_name", "Game Master"),
            text=text,
        )
        reply = await bot.handle(message)
        if reply:
            telegram.reply(chat_id, reply)
        return {"ok": True}

    return app


def _required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _env_is_configured():
    required = (
        "TELEGRAM_BOT_TOKEN",
        "GOOGLE_SPREADSHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GAME_MASTER_CHAT_ID",
        "ANNOUNCEMENT_CHAT_ID",
        "PUBLIC_BASE_URL",
        "WEBHOOK_SECRET",
    )
    return all(os.environ.get(name) for name in required)


app = create_app() if _env_is_configured() else None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("orientation_bot.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
