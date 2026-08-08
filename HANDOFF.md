# Home Server Handoff

This repository contains a Python Telegram bot for an orientation game. It records scores for six groups and six games, uses Google Sheets as the source of truth, and posts a public leaderboard.

## Current State

Implemented and tested:

- `/score G1 Game1 8` accepts Groups `G1`–`G6`, Games `Game1`–`Game6`, and whole scores from 0 through 10.
- A score replaces the current Group–Game score; it never adds points.
- The bot reads the current `Scores` tab before each update, then updates the score and appends an Audit entry through the Sheets API.
- The leaderboard sums scores only. Equal totals share a rank and are listed alphabetically. Ranks 1–3 use medal emoji; later ranks are numeric.
- A first recorded score posts a friendly completion notice and then a pinned HTML leaderboard. A correction posts a compact correction notice and then a pinned leaderboard.
- Repeating an unchanged score posts no public messages.
- If Sheets cannot be read or written, no public announcement is sent; the Game Master gets a retry/manual-fallback message.
- Commands are accepted only in `GAME_MASTER_CHAT_ID`. Direct messages reply: `You are not an authenticated user. Contact @iamrolling if you require access.` Other chats are ignored.
- `/help` and `/leaderboard` are implemented and registered in Telegram's command menu at startup.
- The bot uses long polling, so the home server does not need a public URL.
- The Google Sheets setup API creates `Scores` and `Audit` tabs when needed, adds headers and Total formulas, and formats/freeze-panes the header rows.

## Files to Read First

- `README.md` — human setup and Docker commands.
- `CONTEXT.md` — agreed domain vocabulary and behavior.
- `docs/adr/0001-google-sheets-score-store.md` — why Google Sheets is the score store.
- `docs/testing.md` — agreed public test seams.
- `orientation_bot/main.py` — runtime wiring and required environment variables.

## Required Runtime Configuration

Set these values in `.env` (start from `.env.example`):

```dotenv
TELEGRAM_BOT_TOKEN=
GOOGLE_SPREADSHEET_ID=
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/google-service-account.json
GAME_MASTER_CHAT_ID=
ANNOUNCEMENT_CHAT_ID=
```

Keep the Google service-account JSON outside the repository. Share the chosen spreadsheet with its service-account email as an Editor. Add the Telegram bot to the private Game Master group and the public announcement channel; grant it permission to post and pin in the announcement channel.

## Local Environment and Verification

A local `.venv` already exists and has the runtime dependencies installed. Use it for all Python commands:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

At handoff, all 7 tests pass. They cover the command handler and Google Sheets score-store seams. The test suite uses in-memory boundary fakes; it does not call Telegram or Google.

## Remaining Work

1. Create the Telegram bot and Google service account, then create/share the spreadsheet as described in `README.md`.
2. Fill `.env` with the token, spreadsheet ID, service-account path, and the two Telegram chat IDs.
3. Start Docker on the home server and run the Docker build/run commands from `README.md`.
4. Perform a live smoke test in a test Telegram group/channel: run one valid score, a correction, an unchanged duplicate, `/leaderboard`, and a direct message.
5. Confirm that the bot can pin messages in the announcement channel. If it cannot, fix its channel administrator permissions.
6. Before the event, decide whether `G1`–`G6` and `Game1`–`Game6` should remain the public names. The current code intentionally uses exactly those identifiers.

## Known Verification Gap

The Docker image was not built in this workspace because the local Docker daemon was not running. Python tests and bytecode compilation passed. The home-server agent should run `docker build -t orientation-score-bot .` before deployment.

## Operational Fallback

If Google Sheets is unavailable during the event, update `Scores` manually and add a matching manual row in `Audit`. Once Sheets is reachable, the bot reads the current sheet state again; it does not retain a separate score cache.
