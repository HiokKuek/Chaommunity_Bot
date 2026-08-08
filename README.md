# Orientation Score Bot

A small Telegram bot for recording orientation-game scores and publishing a pinned leaderboard. Scores are kept in Google Sheets, so organisers can view and correct the source data whenever needed.

The bot is designed for one private Game Master group and one announcement channel. It uses long polling, so it does not need a public web address or webhook.

## What it does

- Records a score with `/score G1 GameA 8`.
- Records secret-mission completions with `/secret G1` and bonus-mission updates with `/bonus G1` or `/bonus remove G1`.
- Accepts groups `G1`–`G6`, games `GameA`–`GameF`, and whole-number scores from 1 to 10.
- Automatically awards Secret Mission points in completion order: `10, 9, 8, 7, 6, 5`.
- Only allows Bonus Mission points after that group's own Secret Mission is complete; each `/bonus` adds `8` points.
- Replaces a previous game score instead of adding to it.
- Posts a completion or correction notice and a pinned leaderboard in the announcement channel.
- Keeps `Scores` and `Audit` tabs in the configured Google Sheet.
- Only accepts commands in the configured Game Master group. Direct messages receive an access notice; other group chats are ignored.

## Before you start

You need:

- Docker running on the home server.
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- A private Game Master group and an announcement channel. Add the bot to both; make it an administrator in the announcement channel with permission to post and pin messages.
- A Google account that can create a Google Cloud project and spreadsheet.

## One-time setup

### 1. Find the Telegram chat IDs

Add the bot to both chats. Send `/start` in the Game Master group and publish a temporary post in the announcement channel. Use Telegram's `getUpdates` API or a trusted chat-ID utility to find their numeric IDs. Group and channel IDs are normally negative.

### 2. Set up Google Sheets access

1. Create a Google Cloud project and enable the **Google Sheets API**.
2. Create a service account and download a **JSON** key.
3. Create a blank Google Sheet and copy its ID from its URL:

   ```text
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```

4. Share that sheet directly with the service account's email address as an **Editor**.

Do not commit the JSON key. Keep it next to the deployment files or in another private location on the server. The bot creates and formats the `Scores` and `Audit` tabs on its first successful start. Existing `Scores` tabs with legacy `Game1`–`Game6` headers are renamed in place to `GameA`–`GameF` on startup.

### 3. Create `.env`

Copy the template and fill it in:

```sh
cp .env.example .env
```

```dotenv
TELEGRAM_BOT_TOKEN=your_bot_token
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/google-service-account.json
GAME_MASTER_CHAT_ID=-1000000000000
ANNOUNCEMENT_CHAT_ID=-1000000000001
```

`GOOGLE_SERVICE_ACCOUNT_FILE` is the path **inside** the container. It should stay exactly as shown when using the Docker command below.

## Run the bot with Docker

From the repository directory, where `google-service-account.json` is stored locally:

```sh
docker build -t orientation-score-bot .

docker run -d \
  --name orientation-score-bot \
  --restart unless-stopped \
  --env-file .env \
  -v "$(pwd)/google-service-account.json:/run/secrets/google-service-account.json:ro" \
  orientation-score-bot
```

The key is mounted read-only. The container restarts automatically after a Docker or server restart.

Useful commands:

```sh
docker logs -f orientation-score-bot
docker stop orientation-score-bot
docker start orientation-score-bot
```

## Using the bot

In the Game Master group, type `/` or use Telegram's command-menu button to see the available commands:

```text
/help
/leaderboard
/score G1 GameA 8
/secret G1
/bonus G1
/bonus remove G1
/resetmissions
```

`/secret` marks a group's own Secret Mission as complete and automatically assigns the next available score from `10, 9, 8, 7, 6, 5`.

`/bonus` adds `8` Bonus Mission points after that group has completed `/secret`. `/bonus remove` subtracts one `8`-point step if a Game Master records too many bonus missions.

In a group, Telegram may address a command to the bot. These forms work too:

```text
/help@chaommunity_bot
/leaderboard@chaommunity_bot
/score@chaommunity_bot G1 GameA 8
```

Commands addressed to another bot are ignored.

A repeated score does not send another announcement. A changed score posts a correction and refreshed, pinned leaderboard.

## Local checks

Create a virtual environment and run the test suite:

```sh
python3 -m venv .venv
.venv/bin/python -m unittest discover -s tests -v
```

## If something goes wrong

- **Google Sheets says permission denied:** make sure the exact spreadsheet is shared as **Editor** with the email inside the service-account JSON file.
- **The bot does not reply:** confirm you are using a slash command in the configured Game Master group, then inspect `docker logs -f orientation-score-bot`.
- **The bot cannot pin leaderboard messages:** grant it permission to pin messages in the announcement channel.
- **Google Sheets is unavailable during the event:** update `Scores` manually and add a matching row in `Audit`. The bot reads from Sheets each time and does not maintain a separate score cache.
