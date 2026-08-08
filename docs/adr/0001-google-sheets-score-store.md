# Google Sheets as the score store

The bot will treat one Google Spreadsheet as the source of truth: its first sheet holds current group scores and its second sheet holds the append-only audit trail. This replaces the initial Excel assumption because it allows the bot to update the event record directly through the Google Sheets API without requiring organizers to make manual edits.
