from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleSheetsApi:
    def __init__(self, service):
        self.service = service

    @classmethod
    def from_service_account_file(cls, filename):
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
        if created_scores or created_audit:
            rows = [[group, 0, 0, 0, 0, 0, 0, f"=SUM(B{index}:G{index})"] for index, group in enumerate(("G1", "G2", "G3", "G4", "G5", "G6"), start=2)]
            data = []
            if created_scores:
                data.append({"range": "Scores!A1:H7", "values": [["Group", "Game1", "Game2", "Game3", "Game4", "Game5", "Game6", "Total"], *rows]})
            if created_audit:
                data.append({"range": "Audit!A1:H1", "values": [["Timestamp", "Group", "Game", "Previous score", "New score", "Game Master", "Telegram ID", "Command"]]})
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
