# Orientation Score Bot

Telegram bot for recording `G1`–`G6` scores for `Game1`–`Game6`, publishing a pinned leaderboard, and keeping Google Sheets as the source of truth.

## Local development

```sh
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## One-time setup

1. Create a bot with Telegram's `@BotFather` and save its token.
2. Create a private Game Master group and an announcement channel. Add the bot to both. Make it an administrator in the announcement channel with permission to post and pin messages.
3. Start the bot once in each chat, then obtain each numeric chat ID from a temporary `getUpdates` response (or a trusted Telegram ID utility). Put them in `GAME_MASTER_CHAT_ID` and `ANNOUNCEMENT_CHAT_ID`; these are usually negative for groups/channels.
4. In Google Cloud, create a project, enable **Google Sheets API**, then create a service account and download its JSON key. Create a blank Google Spreadsheet and share it as **Editor** with the service account email. Copy the spreadsheet ID from its URL.
5. Copy `.env.example` to `.env`, fill in the values, and keep the JSON key outside git. On first start, the bot uses the Sheets API to create/format `Scores` and `Audit` tabs, headers, totals, and frozen header rows.

## Run in Docker

```sh
docker build -t orientation-score-bot .
docker run --env-file .env \
  -v /absolute/path/to/service-account.json:/run/secrets/google-service-account.json:ro \
  orientation-score-bot
```

The bot uses long polling, so it needs no public URL. Keep one container running on your home server. If Sheets is unavailable, it refuses the command and posts no announcement; update both the Scores and Audit tabs manually as the agreed fallback.
