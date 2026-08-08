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
SCORE_HELP_MESSAGE = (
    "❗ <b>Invalid score command</b>\n"
    "Please use:\n"
    "/score &lt;group&gt; &lt;game&gt; &lt;1-10&gt;\n"
    "──────────\n"
    "<b>Example:</b>\n"
    "/score G1 GameA 10\n"
    "──────────\n"
    "<b>Games:</b>\n"
    f"{GAME_LISTING}"
)
MISSION_HELP_MESSAGE = (
    "🕵️ <b>Mission commands</b>\n"
    "/secret &lt;group&gt; — mark the group's own secret mission as complete\n"
    "/bonus &lt;group&gt; — add 8 bonus points after /secret\n"
    "/bonus remove &lt;group&gt; — remove 8 bonus points\n"
    "──────────\n"
    "<b>Examples:</b>\n"
    "/secret G1\n"
    "/bonus G1\n"
    "──────────\n"
    "<b>Rule:</b> A group must finish its own secret mission before bonus missions count."
)
HELP_MESSAGE = (
    "📝 <b>Score and mission guide</b>\n\n"
    "<b>Game scores:</b>\n"
    "/score &lt;group&gt; &lt;game&gt; &lt;1-10&gt;\n"
    "<b>Example:</b> /score G1 GameA 10\n"
    "──────────\n"
    "<b>Games:</b>\n"
    f"{GAME_LISTING}\n"
    "──────────\n"
    "<b>Missions:</b>\n"
    "/secret &lt;group&gt;\n"
    "/bonus &lt;group&gt;\n"
    "/bonus remove &lt;group&gt;\n"
    "/resetmissions\n"
    "<b>Rule:</b> /bonus only works after /secret."
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
            return HELP_MESSAGE
        if text == "/leaderboard":
            try:
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not read Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            return _leaderboard_announcement(standings)

        if text == "/resetmissions":
            try:
                result = await self.score_store.reset_missions(
                    game_master={"id": message.sender_id, "name": message.sender_name},
                    command=message.text,
                )
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            if not result["changed"]:
                return "ℹ️ <b>No change</b>\nSecret Mission and Bonus Mission scores are already 0."
            await self.publisher.publish(self.announcement_chat_id, _missions_reset_announcement(), pin=False)
            await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
            return "✅ <b>Mission scores reset!</b>\nAll Secret Mission and Bonus Mission scores are now 0."

        command = _parse_score_command(text)
        if command is not None:
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

        secret_group = _parse_secret_command(text)
        if secret_group is not None:
            try:
                result = await self.score_store.complete_secret_mission(
                    group=secret_group,
                    game_master={"id": message.sender_id, "name": message.sender_name},
                    command=message.text,
                )
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            if not result["changed"]:
                return _unchanged_secret_message(secret_group, result["points"])
            await self.publisher.publish(self.announcement_chat_id, _secret_mission_announcement(secret_group, result["points"]), pin=False)
            await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
            return _secret_mission_saved_message(secret_group, result["points"])

        bonus_command = _parse_bonus_command(text)
        if bonus_command is not None:
            action, group = bonus_command
            try:
                if action == "add":
                    result = await self.score_store.add_bonus_mission(
                        group=group,
                        game_master={"id": message.sender_id, "name": message.sender_name},
                        command=message.text,
                    )
                    if not result["changed"]:
                        return _bonus_requires_secret_message(group)
                    standings = await self.score_store.leaderboard()
                    await self.publisher.publish(self.announcement_chat_id, _bonus_mission_announcement(group, result["added"], result["total"]), pin=False)
                    await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
                    return _bonus_mission_saved_message(group, result["added"], result["total"])

                result = await self.score_store.remove_bonus_mission(
                    group=group,
                    game_master={"id": message.sender_id, "name": message.sender_name},
                    command=message.text,
                )
                if not result["changed"]:
                    return _unchanged_bonus_message(group)
                standings = await self.score_store.leaderboard()
                await self.publisher.publish(self.announcement_chat_id, _bonus_mission_removed_announcement(group, result["removed"], result["total"]), pin=False)
                await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
                return _bonus_mission_removed_message(group, result["removed"], result["total"])
            except Exception:
                return "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues."

        if text.startswith("/score"):
            return SCORE_HELP_MESSAGE
        if text.startswith("/secret") or text.startswith("/bonus"):
            return MISSION_HELP_MESSAGE
        return None


def _parse_score_command(text):
    parts = text.split()
    if len(parts) != 4 or parts[0] != "/score":
        return None
    _, group, game, score_text = parts
    if group not in GROUPS or game not in GAMES or not score_text.isdigit():
        return None
    score = int(score_text)
    return (group, game, score) if 1 <= score <= 10 else None


def _parse_secret_command(text):
    parts = text.split()
    if len(parts) != 2 or parts[0] != "/secret":
        return None
    _, group = parts
    return group if group in GROUPS else None


def _parse_bonus_command(text):
    parts = text.split()
    if not parts or parts[0] != "/bonus":
        return None
    if len(parts) == 2 and parts[1] in GROUPS:
        return ("add", parts[1])
    if len(parts) == 3 and parts[1] == "remove" and parts[2] in GROUPS:
        return ("remove", parts[2])
    return None


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


def _secret_mission_saved_message(group, points):
    return (
        "✅ <b>Secret mission recorded!</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Points awarded:</b> {points}"
    )


def _unchanged_secret_message(group, points):
    return (
        "ℹ️ <b>No change</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Secret Mission:</b> already recorded as {points}"
    )


def _bonus_requires_secret_message(group):
    return (
        "❗ <b>Bonus mission unavailable</b>\n"
        f"Complete /secret for {group} before adding bonus mission points."
    )


def _bonus_mission_saved_message(group, added, total):
    return (
        "✅ <b>Bonus mission recorded!</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Bonus added:</b> {added}\n"
        f"<b>Bonus Mission total:</b> {total}"
    )


def _bonus_mission_removed_message(group, removed, total):
    return (
        "✅ <b>Bonus mission removed!</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Bonus removed:</b> {removed}\n"
        f"<b>Bonus Mission total:</b> {total}"
    )


def _unchanged_bonus_message(group):
    return (
        "ℹ️ <b>No change</b>\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Bonus Mission:</b> already 0"
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


def _secret_mission_announcement(group, points):
    return (
        "🎯 <b>Secret mission completed!</b>\n\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Points awarded:</b> {points}"
    )


def _bonus_mission_announcement(group, points, total):
    return (
        "🕵️ <b>Bonus mission completed!</b>\n\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Points awarded:</b> {points}\n"
        f"<b>Bonus Mission total:</b> {total}"
    )


def _bonus_mission_removed_announcement(group, removed, total):
    return (
        "↩️ <b>Bonus mission removed</b>\n\n"
        f"<b>Group:</b> {group}\n"
        f"<b>Points removed:</b> {removed}\n"
        f"<b>Bonus Mission total:</b> {total}"
    )


def _missions_reset_announcement():
    return (
        "🧹 <b>Mission scores reset</b>\n\n"
        "Secret Mission and Bonus Mission scores have been cleared for all groups."
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
