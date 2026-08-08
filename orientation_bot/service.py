from dataclasses import dataclass


GROUPS = ("G1", "G2", "G3", "G4", "G5", "G6")
GAME_DETAILS = {
    "GameA": {"letter": "A", "name": "Teochew Speed Drawing"},
    "GameB": {"letter": "B", "name": "Connect Four Relay"},
    "GameC": {"letter": "C", "name": "Unlock the Code"},
    "GameD": {"letter": "D", "name": "The Photo Quest"},
    "GameE": {"letter": "E", "name": "Minefield"},
    "GameF": {"letter": "F", "name": "Qiaopi: The Missing Letter"},
}
GAMES = tuple(GAME_DETAILS)
GAME_LISTING = "\n".join(f"{game}: {details['name']}" for game, details in GAME_DETAILS.items())
INVALID_SCORE_MESSAGE = (
    "❗ <b>Invalid message</b>\n"
    "Please use:\n"
    "/score &lt;group&gt; &lt;game&gt; &lt;1-10&gt;\n"
    "──────────\n"
    "<b>Example:</b>\n"
    "/score G1 GameA 10\n"
    "──────────\n"
    "<b>Games:</b>\n"
    f"{GAME_LISTING}"
)
SCORE_HELP_MESSAGE = (
    "📝 <b>How to record a score</b>\n\n"
    "<b>Format:</b>\n"
    "/score &lt;group&gt; &lt;game&gt; &lt;1-10&gt;\n"
    "──────────\n"
    "<b>Example:</b>\n"
    "/score G1 GameA 10\n"
    "──────────\n"
    "<b>Games:</b>\n"
    f"{GAME_LISTING}"
)


@dataclass(frozen=True)
class IncomingMessage:
    chat_id: int
    chat_type: str
    sender_id: int
    sender_name: str
    text: str


class BotService:
    def __init__(self, score_store, publisher, game_master_chat_id, announcement_chat_id, bot_username=None):
        self.score_store = score_store
        self.publisher = publisher
        self.game_master_chat_id = game_master_chat_id
        self.announcement_chat_id = announcement_chat_id
        self.bot_username = bot_username

    async def handle(self, message):
        if message.chat_id != self.game_master_chat_id:
            if message.chat_type == "private":
                return "You are not an authenticated user. Contact @iamrolling if you require access."
            return None

        text = _command_for_this_bot(message.text, self.bot_username)
        if text is None:
            return None

        if text == "/help":
            return SCORE_HELP_MESSAGE
        if text == "/leaderboard":
            try:
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not read Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            return _leaderboard_announcement(standings)

        command = _parse_score_command(text)
        if command is None:
            if text.startswith("/score"):
                return INVALID_SCORE_MESSAGE
            return None

        group, game, score = command
        try:
            result = await self.score_store.replace_score(
                group=group,
                game=game,
                score=score,
                game_master={"id": message.sender_id, "name": message.sender_name},
                command=message.text,
            )
            standings = await self.score_store.leaderboard()
        except Exception:
            return "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
        if not result["changed"]:
            return _unchanged_score_message(group, game, score)
        announcement = _completion_announcement(group, game, score) if result["is_first_score"] else _correction_announcement(group, game, result["previous_score"], score)
        await self.publisher.publish(self.announcement_chat_id, announcement, pin=False)
        await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
        return _score_saved_message(group, game, score, is_first_score=result["is_first_score"])


def _parse_score_command(text):
    parts = text.split()
    if len(parts) != 4 or parts[0] != "/score":
        return None
    _, group, game, score_text = parts
    if group not in GROUPS or game not in GAMES or not score_text.isdigit():
        return None
    score = int(score_text)
    return (group, game, score) if 1 <= score <= 10 else None


def _command_for_this_bot(text, bot_username):
    if not bot_username:
        return text
    command, separator, rest = text.partition(" ")
    suffix = f"@{bot_username}".lower()
    if command.lower().endswith(suffix):
        return command[:-len(suffix)] + separator + rest
    if "@" in command:
        return None
    return text


def _game_name(game):
    return GAME_DETAILS[game]["name"]


def _game_display(game):
    return f"{_game_name(game)} (Game {GAME_DETAILS[game]['letter']})"


def _score_saved_message(group, game, score, is_first_score):
    title = "Score recorded!" if is_first_score else "Score updated!"
    return (
        f"✅ <b>{title}</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Game:</b> {_game_display(game)}\n"
        f"<b>Score:</b> {score}/10"
    )


def _unchanged_score_message(group, game, score):
    return (
        "ℹ️ <b>No change</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Game:</b> {_game_display(game)}\n"
        f"<b>Score:</b> already {score}/10"
    )


def _completion_announcement(group, game, score):
    return (
        f"🎉 <b>{_game_display(game)} complete!</b>\n\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Score:</b> {score}/10"
    )


def _correction_announcement(group, game, previous_score, score):
    return (
        "✏️ <b>Score updated</b>\n\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Game:</b> {_game_display(game)}\n"
        f"<b>Score:</b> {previous_score}/10 → {score}/10"
    )


def _leaderboard_announcement(standings):
    ordered = sorted(standings, key=lambda standing: (-standing["total"], standing["group"]))
    previous_total = None
    rank = 0
    lines = ["🏆 <b>Leaderboard</b>", "<i>Live scores</i>", ""]
    for index, standing in enumerate(ordered, start=1):
        if standing["total"] != previous_total:
            rank = index
        previous_total = standing["total"]
        prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        lines.append(f"{prefix} {standing['group']}: {standing['total']}")
    return "\n".join(lines)
