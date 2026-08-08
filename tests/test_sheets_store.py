import unittest

from orientation_bot.sheets_store import GoogleSheetsScoreStore


class GoogleSheetsScoreStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_replaces_a_score_and_appends_an_audit_entry_in_one_values_request(self):
        api = FakeSheetsApi()
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.replace_score(
            group="G1",
            game="GameA",
            score=8,
            game_master={"id": 7, "name": "Aisha"},
            command="/score G1 GameA 8",
        )

        self.assertEqual({"previous_score": 0, "is_first_score": True, "changed": True}, result)
        self.assertEqual(
            [
                {
                    "range": "Scores!B2",
                    "values": [[8]],
                },
                {
                    "range": "Audit!A2:H2",
                    "values": [["2026-08-08T05:30:00Z", "G1", "GameA", 0, 8, "Aisha", 7, "/score G1 GameA 8"]],
                },
            ],
            api.writes,
        )

    async def test_leaderboard_uses_the_current_scores_tab(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Total"],
            ["G1", 8, 3, 0, 0, 0, 0, 11],
            ["G2", 5, 0, 0, 0, 0, 0, 5],
            ["G3", 0, 0, 0, 0, 0, 0, 0],
            ["G4", 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123")

        standings = await store.leaderboard()

        self.assertEqual(
            [{"group": "G1", "total": 11}, {"group": "G2", "total": 5}, {"group": "G3", "total": 0}, {"group": "G4", "total": 0}, {"group": "G5", "total": 0}, {"group": "G6", "total": 0}],
            standings,
        )

    async def test_replace_score_supports_legacy_game_headers_during_transition(self):
        api = FakeSheetsApi(scores=[
            ["Group", "Game1", "Game2", "Game3", "Game4", "Game5", "Game6", "Total"],
            ["G1", 0, 0, 0, 0, 0, 0, 0],
            ["G2", 0, 0, 0, 0, 0, 0, 0],
            ["G3", 0, 0, 0, 0, 0, 0, 0],
            ["G4", 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.replace_score(
            group="G1",
            game="GameA",
            score=8,
            game_master={"id": 7, "name": "Aisha"},
            command="/score G1 GameA 8",
        )

        self.assertEqual({"previous_score": 0, "is_first_score": True, "changed": True}, result)
        self.assertEqual("Scores!B2", api.writes[0]["range"])


class FakeSheetsApi:
    def __init__(self, scores=None):
        self.scores = scores or [
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Total"],
            ["G1", 0, 0, 0, 0, 0, 0, 0],
            ["G2", 0, 0, 0, 0, 0, 0, 0],
            ["G3", 0, 0, 0, 0, 0, 0, 0],
            ["G4", 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0],
        ]
        self.audit = []
        self.writes = []

    def get_values(self, spreadsheet_id, range_name):
        if range_name == "Scores!A1:H7":
            return self.scores
        if range_name == "Audit!A2:H":
            return self.audit
        raise AssertionError(f"Unexpected range: {range_name}")

    def batch_update_values(self, spreadsheet_id, data):
        self.writes = data
