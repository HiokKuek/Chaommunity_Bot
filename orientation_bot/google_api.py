NEW_SCORE_HEADERS = [
    "Group",
    "GameA",
    "GameB",
    "GameC",
    "GameD",
    "GameE",
    "GameF",
    "Secret Mission",
    "Bonus Mission",
    "Total",
]
PRE_MISSION_SCORE_HEADERS = ["Group", "GameA", "GameB", "GameC", "GameD", "GameE", "GameF", "Total"]
LEGACY_SCORE_HEADERS = ["Group", "Game1", "Game2", "Game3", "Game4", "Game5", "Game6", "Total"]
GROUPS = ("G1", "G2", "G3", "G4", "G5", "G6")
AUDIT_HEADERS = [["Timestamp", "Group", "Game", "Previous score", "New score", "Game Master", "Telegram ID", "Command"]]


class GoogleSheetsApi:
    def __init__(self, service):
        self.service = service

    @classmethod
    def from_service_account_file(cls, filename):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            filename,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return cls(build("sheets", "v4", credentials=credentials, cache_discovery=False))

    def get_values(self, spreadsheet_id, range_name):
        return self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute().get("values", [])

    def batch_update_values(self, spreadsheet_id, data):
        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()

    def ensure_workbook(self, spreadsheet_id):
        metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = metadata["sheets"]
        titles = {sheet["properties"]["title"]: sheet["properties"]["sheetId"] for sheet in sheets}
        requests = []
        created_scores = False
        if "Scores" not in titles:
            first = sheets[0]["properties"]
            requests.append({"updateSheetProperties": {"properties": {"sheetId": first["sheetId"], "title": "Scores"}, "fields": "title"}})
            created_scores = True
        created_audit = "Audit" not in titles
        if created_audit:
            requests.append({"addSheet": {"properties": {"title": "Audit"}}})
        if requests:
            self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()

        data = []
        scores = self.get_values(spreadsheet_id, "Scores!A1:J7")
        if created_scores or not scores:
            data.append({"range": "Scores!A1:J7", "values": _default_score_grid()})
        elif _needs_mission_columns(scores[0]):
            data.append({"range": "Scores!A1:J7", "values": _migrated_score_grid(scores)})
        if created_audit or not self.get_values(spreadsheet_id, "Audit!A1:H1"):
            data.append({"range": "Audit!A1:H1", "values": AUDIT_HEADERS})
        if data:
            self.batch_update_values(spreadsheet_id, data)

        formatted = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        ids = {sheet["properties"]["title"]: sheet["properties"]["sheetId"] for sheet in formatted["sheets"]}
        format_requests = []
        for title in ("Scores", "Audit"):
            sheet_id = ids[title]
            format_requests.extend([
                {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.12, "green": 0.35, "blue": 0.65}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
                {"updateSheetProperties": {"properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
            ])
        self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": format_requests}).execute()


def _default_score_grid():
    return [NEW_SCORE_HEADERS, *[_score_row(group, row_index) for row_index, group in enumerate(GROUPS, start=2)]]


def _score_row(group, row_index, game_scores=None, secret_score=0, bonus_score=0):
    game_scores = game_scores or [0, 0, 0, 0, 0, 0]
    return [group, *game_scores, secret_score, bonus_score, f"=SUM(B{row_index}:I{row_index})"]


def _needs_mission_columns(headers):
    return headers[:10] != NEW_SCORE_HEADERS


def _migrated_score_grid(scores):
    headers = scores[0]
    rows = [NEW_SCORE_HEADERS]
    for row_index, group in enumerate(GROUPS, start=2):
        source_row = next((row for row in scores[1:] if row and row[0] == group), [group])
        if headers[:8] == LEGACY_SCORE_HEADERS:
            game_scores = [_int_or_zero(source_row[index]) for index in range(1, 7)]
        else:
            game_scores = [_int_or_zero(source_row[index]) for index in range(1, 7)]
        secret_score = _source_value(headers, source_row, "Secret Mission")
        bonus_score = _source_value(headers, source_row, "Bonus Mission")
        rows.append(_score_row(group, row_index, game_scores, secret_score, bonus_score))
    return rows


def _source_value(headers, row, label):
    if label not in headers:
        return 0
    index = headers.index(label)
    if index >= len(row):
        return 0
    return _int_or_zero(row[index])


def _int_or_zero(value):
    return int(value) if value not in (None, "") else 0
