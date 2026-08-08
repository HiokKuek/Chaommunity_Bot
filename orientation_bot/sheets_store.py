from datetime import UTC, datetime


LEGACY_GAME_COLUMNS = {
    "GameA": "Game1",
    "GameB": "Game2",
    "GameC": "Game3",
    "GameD": "Game4",
    "GameE": "Game5",
    "GameF": "Game6",
}
GAME_HEADERS = ("GameA", "GameB", "GameC", "GameD", "GameE", "GameF")
MISSION_HEADERS = ("Secret Mission", "Bonus Mission")
SCORE_COMPONENT_HEADERS = GAME_HEADERS + MISSION_HEADERS
SECRET_SEQUENCE = (10, 9, 8, 7, 6, 5)


class GoogleSheetsScoreStore:
    def __init__(self, api, spreadsheet_id, clock=None):
        self.api = api
        self.spreadsheet_id = spreadsheet_id
        self.clock = clock or (lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))

    async def replace_score(self, group, game, score, game_master, command):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:J7")
        audit = self.api.get_values(self.spreadsheet_id, "Audit!A2:H")
        score_row, score_column = _score_position(scores, group, game)
        previous_score = _value_at(scores, score_row, score_column)
        is_first_score = not any(row[1:3] == [group, game] for row in audit if len(row) >= 3)
        changed = previous_score != score
        if changed:
            self.api.batch_update_values(
                self.spreadsheet_id,
                [
                    {"range": f"Scores!{_a1_column(score_column + 1)}{score_row + 1}", "values": [[score]]},
                    _audit_entry(audit, self.clock(), group, game, previous_score, score, game_master, command),
                ],
            )
        return {"previous_score": previous_score, "is_first_score": is_first_score, "changed": changed}

    async def complete_secret_mission(self, group, game_master, command):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:J7")
        audit = self.api.get_values(self.spreadsheet_id, "Audit!A2:H")
        score_row, score_column = _score_position(scores, group, "Secret Mission")
        previous_score = _value_at(scores, score_row, score_column)
        if previous_score:
            return {"changed": False, "points": previous_score}
        used_scores = {_value_at(scores, row_index, score_column) for row_index in range(1, len(scores))}
        awarded = next(score for score in SECRET_SEQUENCE if score not in used_scores)
        self.api.batch_update_values(
            self.spreadsheet_id,
            [
                {"range": f"Scores!{_a1_column(score_column + 1)}{score_row + 1}", "values": [[awarded]]},
                _audit_entry(audit, self.clock(), group, "Secret Mission", previous_score, awarded, game_master, command),
            ],
        )
        return {"changed": True, "points": awarded}

    async def add_bonus_mission(self, group, game_master, command):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:J7")
        audit = self.api.get_values(self.spreadsheet_id, "Audit!A2:H")
        secret_row, secret_column = _score_position(scores, group, "Secret Mission")
        if _value_at(scores, secret_row, secret_column) == 0:
            return {"changed": False, "reason": "secret_required"}
        bonus_row, bonus_column = _score_position(scores, group, "Bonus Mission")
        previous_score = _value_at(scores, bonus_row, bonus_column)
        updated_score = previous_score + 8
        self.api.batch_update_values(
            self.spreadsheet_id,
            [
                {"range": f"Scores!{_a1_column(bonus_column + 1)}{bonus_row + 1}", "values": [[updated_score]]},
                _audit_entry(audit, self.clock(), group, "Bonus Mission", previous_score, updated_score, game_master, command),
            ],
        )
        return {"changed": True, "added": 8, "total": updated_score}

    async def remove_bonus_mission(self, group, game_master, command):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:J7")
        audit = self.api.get_values(self.spreadsheet_id, "Audit!A2:H")
        bonus_row, bonus_column = _score_position(scores, group, "Bonus Mission")
        previous_score = _value_at(scores, bonus_row, bonus_column)
        if previous_score == 0:
            return {"changed": False, "total": 0}
        updated_score = max(0, previous_score - 8)
        self.api.batch_update_values(
            self.spreadsheet_id,
            [
                {"range": f"Scores!{_a1_column(bonus_column + 1)}{bonus_row + 1}", "values": [[updated_score]]},
                _audit_entry(audit, self.clock(), group, "Bonus Mission", previous_score, updated_score, game_master, command),
            ],
        )
        return {"changed": True, "removed": 8, "total": updated_score}

    async def reset_missions(self, game_master, command):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:J7")
        audit = self.api.get_values(self.spreadsheet_id, "Audit!A2:H")
        secret_column = _header_index(scores[0], "Secret Mission")
        bonus_column = _header_index(scores[0], "Bonus Mission")
        changed = any(_value_at(scores, row_index, secret_column) or _value_at(scores, row_index, bonus_column) for row_index in range(1, len(scores)))
        if not changed:
            return {"changed": False}
        reset_values = [[0, 0] for _ in scores[1:7]]
        self.api.batch_update_values(
            self.spreadsheet_id,
            [
                {
                    "range": f"Scores!{_a1_column(secret_column + 1)}2:{_a1_column(bonus_column + 1)}7",
                    "values": reset_values,
                },
                _audit_entry(audit, self.clock(), "ALL", "Missions Reset", "", "", game_master, command),
            ],
        )
        return {"changed": True}

    async def leaderboard(self):
        scores = self.api.get_values(self.spreadsheet_id, "Scores!A1:J7")
        headers = scores[0]
        total_columns = [_header_index(headers, header) for header in SCORE_COMPONENT_HEADERS if _header_exists(headers, header)]
        return [
            {"group": row[0], "total": sum(_value_at_row(row, column_index) for column_index in total_columns)}
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


def _header_exists(headers, name):
    return name in headers or LEGACY_GAME_COLUMNS.get(name) in headers


def _header_index(headers, name):
    header_name = name if name in headers else LEGACY_GAME_COLUMNS.get(name, name)
    return headers.index(header_name)


def _value_at(scores, row_index, column_index):
    row = scores[row_index]
    return _value_at_row(row, column_index)


def _value_at_row(row, column_index):
    if column_index >= len(row):
        return 0
    return _as_score(row[column_index])


def _audit_entry(audit, timestamp, group, category, previous_score, score, game_master, command):
    audit_row = len(audit) + 2
    return {
        "range": f"Audit!A{audit_row}:H{audit_row}",
        "values": [[timestamp, group, category, previous_score, score, game_master["name"], game_master["id"], command]],
    }


def _as_score(value):
    return int(value) if value not in (None, "") else 0


def _a1_column(index):
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label
