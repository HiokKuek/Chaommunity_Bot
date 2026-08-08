from dataclasses import dataclass


GROUPS = ("G1", "G2", "G3", "G4", "G5", "G6")
GAMES = ("Game1", "Game2", "Game3", "Game4", "Game5", "Game6")


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

        if text == "/help":
            return "Use /score G1 Game1 <0-10> to record or correct a score. Use /leaderboard to show current standings."
        if text == "/leaderboard":
            try:
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not read Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            return _leaderboard_announcement(standings)

        command = _parse_score_command(text)
        if command is None:
            if text.startswith("/score"):
                return "Invalid score. Use: /score G1 Game1 <0-10>."
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
            return f"{group} already has {score}/10 for {game}. No announcement was posted."
        announcement = _completion_announcement(group, game, score) if result["is_first_score"] else _correction_announcement(group, game, result["previous_score"], score)
        await self.publisher.publish(self.announcement_chat_id, announcement, pin=False)
        await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
        return f"Score recorded for {group} in {game}: {score}/10."


def _parse_score_command(text):
    parts = text.split()
    if len(parts) != 4 or parts[0] != "/score":
        return None
    _, group, game, score_text = parts
    if group not in GROUPS or game not in GAMES or not score_text.isdigit():
        return None
    score = int(score_text)
    return (group, game, score) if score <= 10 else None


def _command_for_this_bot(text, bot_username):
    if not bot_username:
        return text
    command, separator, rest = text.partition(" ")
    suffix = f"@{bot_username}".lower()
    if command.lower().endswith(suffix):
        return command[:-len(suffix)] + separator + rest
    return text


def _completion_announcement(group, game, score):
    return f"🎉 <b>Game complete!</b>\n\n<b>{group}</b> has completed <i>{game}</i>\nScore awarded: <b>{score} / 10</b>"


def _correction_announcement(group, game, previous_score, score):
    return f"✏️ <b>{group}</b>'s <i>{game}</i> score was updated: <b>{previous_score} → {score} / 10</b>."


def _leaderboard_announcement(standings):
    ordered = sorted(standings, key=lambda standing: (-standing["total"], standing["group"]))
    previous_total = None
    rank = 0
    lines = ["🏆 <b>Leaderboard</b>", ""]
    for index, standing in enumerate(ordered, start=1):
        if standing["total"] != previous_total:
            rank = index
        previous_total = standing["total"]
        prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        lines.append(f"{prefix} <b>{standing['group']}</b> — <b>{standing['total']}</b>")
    return "\n".join(lines)
