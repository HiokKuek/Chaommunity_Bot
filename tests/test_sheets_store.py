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

    async def test_secret_mission_uses_the_next_highest_remaining_points(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G2", 0, 0, 0, 0, 0, 0, 9, 0, 9],
            ["G3", 0, 0, 0, 0, 0, 0, 8, 0, 8],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.complete_secret_mission(
            group="G1",
            game_master={"id": 7, "name": "Aisha"},
            command="/secret G1",
        )

        self.assertEqual({"changed": True, "points": 10}, result)
        self.assertEqual(
            [
                {"range": "Scores!H2", "values": [[10]]},
                {
                    "range": "Audit!A2:H2",
                    "values": [["2026-08-08T05:30:00Z", "G1", "Secret Mission", 0, 10, "Aisha", 7, "/secret G1"]],
                },
            ],
            api.writes,
        )

    async def test_add_bonus_requires_secret_points_to_exist(self):
        api = FakeSheetsApi()
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.add_bonus_mission(
            group="G1",
            game_master={"id": 7, "name": "Aisha"},
            command="/bonus G1",
        )

        self.assertEqual({"changed": False, "reason": "secret_required"}, result)
        self.assertEqual([], api.writes)

    async def test_add_bonus_increments_bonus_by_eight(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 0, 0, 0, 0, 0, 0, 10, 8, 18],
            ["G2", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G3", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.add_bonus_mission(
            group="G1",
            game_master={"id": 7, "name": "Aisha"},
            command="/bonus G1",
        )

        self.assertEqual({"changed": True, "added": 8, "total": 16}, result)
        self.assertEqual(
            [
                {"range": "Scores!I2", "values": [[16]]},
                {
                    "range": "Audit!A2:H2",
                    "values": [["2026-08-08T05:30:00Z", "G1", "Bonus Mission", 8, 16, "Aisha", 7, "/bonus G1"]],
                },
            ],
            api.writes,
        )

    async def test_remove_bonus_subtracts_one_bonus_step(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 0, 0, 0, 0, 0, 0, 10, 16, 26],
            ["G2", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G3", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.remove_bonus_mission(
            group="G1",
            game_master={"id": 7, "name": "Aisha"},
            command="/bonus remove G1",
        )

        self.assertEqual({"changed": True, "removed": 8, "total": 8}, result)
        self.assertEqual(
            [
                {"range": "Scores!I2", "values": [[8]]},
                {
                    "range": "Audit!A2:H2",
                    "values": [["2026-08-08T05:30:00Z", "G1", "Bonus Mission", 16, 8, "Aisha", 7, "/bonus remove G1"]],
                },
            ],
            api.writes,
        )

    async def test_reset_missions_clears_secret_and_bonus_columns(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 8, 0, 0, 0, 0, 0, 10, 16, 34],
            ["G2", 5, 0, 0, 0, 0, 0, 9, 0, 14],
            ["G3", 0, 0, 0, 0, 0, 0, 0, 8, 8],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.reset_missions(
            game_master={"id": 7, "name": "Aisha"},
            command="/resetmissions",
        )

        self.assertEqual({"changed": True}, result)
        self.assertEqual(
            [
                {
                    "range": "Scores!H2:I7",
                    "values": [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
                },
                {
                    "range": "Audit!A2:H2",
                    "values": [["2026-08-08T05:30:00Z", "ALL", "Missions Reset", "", "", "Aisha", 7, "/resetmissions"]],
                },
            ],
            api.writes,
        )

    async def test_reset_all_scores_clears_games_and_missions(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 8, 1, 0, 0, 0, 0, 10, 16, 35],
            ["G2", 5, 0, 4, 0, 0, 0, 9, 0, 18],
            ["G3", 0, 0, 0, 0, 0, 0, 0, 8, 8],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123", clock=lambda: "2026-08-08T05:30:00Z")

        result = await store.reset_all_scores(
            game_master={"id": 7, "name": "Aisha"},
            command="/resetscores",
        )

        self.assertEqual({"changed": True}, result)
        self.assertEqual(
            [
                {
                    "range": "Scores!B2:I7",
                    "values": [
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                    ],
                },
                {
                    "range": "Audit!A2:H2",
                    "values": [["2026-08-08T05:30:00Z", "ALL", "All Scores Reset", "", "", "Aisha", 7, "/resetscores"]],
                },
            ],
            api.writes,
        )

    async def test_leaderboard_uses_game_secret_and_bonus_points(self):
        api = FakeSheetsApi(scores=[
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 8, 3, 0, 0, 0, 0, 10, 16, 37],
            ["G2", 5, 0, 0, 0, 0, 0, 9, 0, 14],
            ["G3", 0, 0, 0, 0, 0, 0, 0, 8, 8],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ])
        store = GoogleSheetsScoreStore(api, "spreadsheet-123")

        standings = await store.leaderboard()

        self.assertEqual(
            [
                {"group": "G1", "total": 37},
                {"group": "G2", "total": 14},
                {"group": "G3", "total": 8},
                {"group": "G4", "total": 0},
                {"group": "G5", "total": 0},
                {"group": "G6", "total": 0},
            ],
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
            ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
            ["G1", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G2", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G3", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G4", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G5", 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ["G6", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        self.audit = []
        self.writes = []

    def get_values(self, spreadsheet_id, range_name):
        if range_name in {"Scores!A1:J7", "Scores!A1:H7"}:
            return self.scores
        if range_name == "Audit!A2:H":
            return self.audit
        raise AssertionError(f"Unexpected range: {range_name}")

    def batch_update_values(self, spreadsheet_id, data):
        self.writes = data
