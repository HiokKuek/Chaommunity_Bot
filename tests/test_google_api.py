import unittest

from orientation_bot.google_api import GoogleSheetsApi


class GoogleSheetsApiTests(unittest.TestCase):
    def test_ensure_workbook_creates_scores_with_secret_and_bonus_columns(self):
        service = FakeGoogleService(
            metadata_sequence=[
                {
                    "sheets": [
                        {"properties": {"sheetId": 1, "title": "Sheet1"}},
                    ]
                },
                {
                    "sheets": [
                        {"properties": {"sheetId": 1, "title": "Scores"}},
                        {"properties": {"sheetId": 2, "title": "Audit"}},
                    ]
                },
            ],
            values={"Scores!A1:J1": [], "Scores!A1:H1": []},
        )
        api = GoogleSheetsApi(service)

        api.ensure_workbook("spreadsheet-123")

        self.assertEqual(
            [
                {
                    "range": "Scores!A1:J7",
                    "values": [
                        ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
                        ["G1", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B2:I2)"],
                        ["G2", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B3:I3)"],
                        ["G3", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B4:I4)"],
                        ["G4", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B5:I5)"],
                        ["G5", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B6:I6)"],
                        ["G6", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B7:I7)"],
                    ],
                },
                {
                    "range": "Audit!A1:H1",
                    "values": [["Timestamp", "Group", "Game", "Previous score", "New score", "Game Master", "Telegram ID", "Command"]],
                },
            ],
            service.value_batches[0],
        )

    def test_ensure_workbook_migrates_existing_scores_sheet_to_include_mission_columns(self):
        service = FakeGoogleService(
            metadata_sequence=[
                {
                    "sheets": [
                        {"properties": {"sheetId": 1, "title": "Scores"}},
                        {"properties": {"sheetId": 2, "title": "Audit"}},
                    ]
                },
                {
                    "sheets": [
                        {"properties": {"sheetId": 1, "title": "Scores"}},
                        {"properties": {"sheetId": 2, "title": "Audit"}},
                    ]
                },
            ],
            values={
                "Scores!A1:J7": [
                    ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Total"],
                    ["G1", 8, 3, 0, 0, 0, 0, 11],
                    ["G2", 5, 0, 0, 0, 0, 0, 5],
                    ["G3", 0, 0, 0, 0, 0, 0, 0],
                    ["G4", 0, 0, 0, 0, 0, 0, 0],
                    ["G5", 0, 0, 0, 0, 0, 0, 0],
                    ["G6", 0, 0, 0, 0, 0, 0, 0],
                ],
                "Audit!A1:H1": [["Timestamp", "Group", "Game", "Previous score", "New score", "Game Master", "Telegram ID", "Command"]],
            },
        )
        api = GoogleSheetsApi(service)

        api.ensure_workbook("spreadsheet-123")

        self.assertEqual(
            [
                {
                    "range": "Scores!A1:J7",
                    "values": [
                        ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Secret Mission", "Bonus Mission", "Total"],
                        ["G1", 8, 3, 0, 0, 0, 0, 0, 0, "=SUM(B2:I2)"],
                        ["G2", 5, 0, 0, 0, 0, 0, 0, 0, "=SUM(B3:I3)"],
                        ["G3", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B4:I4)"],
                        ["G4", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B5:I5)"],
                        ["G5", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B6:I6)"],
                        ["G6", 0, 0, 0, 0, 0, 0, 0, 0, "=SUM(B7:I7)"],
                    ],
                }
            ],
            service.value_batches[0],
        )


class FakeGoogleService:
    def __init__(self, metadata_sequence, values):
        self.metadata_sequence = list(metadata_sequence)
        self.values = values
        self.sheet_batches = []
        self.value_batches = []

    def spreadsheets(self):
        return FakeSpreadsheetsResource(self)


class FakeSpreadsheetsResource:
    def __init__(self, service):
        self.service = service

    def get(self, spreadsheetId):
        return FakeExecute(self.service.metadata_sequence.pop(0))

    def values(self):
        return FakeValuesResource(self.service)

    def batchUpdate(self, spreadsheetId, body):
        self.service.sheet_batches.append(body["requests"])
        return FakeExecute({})


class FakeValuesResource:
    def __init__(self, service):
        self.service = service

    def get(self, spreadsheetId, range):
        return FakeExecute({"values": self.service.values.get(range, [])})

    def batchUpdate(self, spreadsheetId, body):
        self.service.value_batches.append(body["data"])
        return FakeExecute({})


class FakeExecute:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload
