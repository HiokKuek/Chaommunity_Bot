# Test Seams

The bot is tested through these public boundaries:

- Command handling for `/score`, `/leaderboard`, and `/help`.
- The score-store contract used to read and update the Google Spreadsheet.
- The Telegram announcement and pinning contract.

Adapters are replaced by behavioral in-memory fakes in tests. Tests do not reach into SDK implementations.
