from datetime import UTC, datetime


LEGACY_GAME_COLUMNS = {
    "GameA": "Game1",
    "GameB": "Game2",
    "GameC": "Game3",
    "GameD": "Game4",
    "GameE": "Game5",
    "GameF": "Game6",
}


class GoogleSheetsScoreStore:
    def __init__(self, api, spreadsheet_id, clock=None):
        self.api = api
        self.spreadsheet_id = spreadsheet_id
        self.clock = clock or (lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))

    async def replace_score(self, group, game, score, game_master, command):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:H7")
        audit = self.api.get_values(self.spreadsheet_id, "Audit!A2:H")
        score_row, score_column = _score_position(scores, group, game)
        previous_score = _as_score(scores[score_row][score_column])
        is_first_score = not any(row[1:3] == [group, game] for row in audit if len(row) >= 3)
        changed = previous_score != score
        if changed:
            audit_row = len(audit) + 2
            self.api.batch_update_values(
                self.spreadsheet_id,
                [
                    {"range": f"Scores!{_a1_column(score_column + 1)}{score_row + 1}", "values": [[score]]},
                    {
                        "range": f"Audit!A{audit_row}:H{audit_row}",
                        "values": [[self.clock(), group, game, previous_score, score, game_master["name"], game_master["id"], command]],
                    },
                ],
            )
        return {"previous_score": previous_score, "is_first_score": is_first_score, "changed": changed}

    async def leaderboard(self):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:H7")
        return [
            {"group": row[0], "total": sum(_as_score(value) for value in row[1:7])}
            for row in scores[1:]
        ]


def _score_position(scores, group, game):
    headers = scores[0]
    header_name = game if game in headers else LEGACY_GAME_COLUMNS.get(game, game)
    score_column = headers.index(header_name)
    for index, row in enumerate(scores[1:], start=1):
        if row[0] == group:
            return index, score_column
    raise ValueError(f"Unknown group: {group}")


def _as_score(value):
    return int(value) if value not in (None, "") else 0


def _a1_column(index):
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label
