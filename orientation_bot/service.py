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
GAME_LISTING = "\n".join(f"{game} — {details['name']}" for game, details in GAME_DETAILS.items())
GROUP_LISTING = ", ".join(GROUPS)
SCORE_HELP_MESSAGE = (
    "❗ Invalid score command\n\n"
    "Why this happened\n"
    "Use /score with a valid group, game, and score from 1 to 10.\n\n"
    "Command: /score <group> <game> <1-10>\n"
    "Usage: /score G1 GameA 10\n\n"
    "Valid groups: " + GROUP_LISTING + "\n\n"
    "Valid games\n"
    f"{GAME_LISTING}"
)
MISSION_HELP_MESSAGE = (
    "🕵️ Mission guide\n\n"
    "After completing a secret mission\n"
    "Command: /secret <group>\n"
    "Usage: /secret G1\n"
    "Secret Mission points are auto-assigned in this order: 10, 9, 8, 7, 6, 5\n\n"
    "After completing a bonus mission\n"
    "Command: /bonus <group>\n"
    "Usage: /bonus G1\n"
    "Rule: /bonus only works after /secret. Each /bonus adds 8 points.\n\n"
    "Remove 1 mistaken bonus mission\n"
    "Command: /bonus remove <group>\n"
    "Usage: /bonus remove G1\n\n"
    "Admin\n"
    "/resetmissions — Reset Secret Mission and Bonus Mission scores\n"
    "/resetscores — Reset every score"
)
HELP_MESSAGE = (
    "📝 Command guide\n\n"
    "Score updates\n\n"
    "After completing a game\n"
    "Command: /score <group> <game> <1-10>\n"
    "Usage: /score G1 GameA 10\n"
    "Games: GameA, GameB, GameC, GameD, GameE, GameF\n\n"
    "After completing a secret mission\n"
    "Command: /secret <group>\n"
    "Usage: /secret G1\n"
    "Secret Mission points are auto-assigned in this order: 10, 9, 8, 7, 6, 5\n\n"
    "After completing a bonus mission\n"
    "Command: /bonus <group>\n"
    "Usage: /bonus G1\n"
    "Rule: /bonus only works after /secret. Each /bonus adds 8 points.\n\n"
    "Remove 1 mistaken bonus mission\n"
    "Command: /bonus remove <group>\n"
    "Usage: /bonus remove G1\n\n"
    "Admin & resets\n\n"
    "Reset mission scores — /resetmissions\n"
    "Reset every score — /resetscores"
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
                return "ℹ️ No change\n\nSecret Mission and Bonus Mission scores are already 0."
            await self.publisher.publish(self.announcement_chat_id, _missions_reset_announcement(), pin=False)
            await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
            return "✅ Mission scores reset\n\nAll Secret Mission and Bonus Mission scores are now 0."

        if text == "/resetscores":
            try:
                result = await self.score_store.reset_all_scores(
                    game_master={"id": message.sender_id, "name": message.sender_name},
                    command=message.text,
                )
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            if not result["changed"]:
                return "ℹ️ No change\n\nAll game, Secret Mission, and Bonus Mission scores are already 0."
            await self.publisher.publish(self.announcement_chat_id, _all_scores_reset_announcement(), pin=False)
            await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
            return "✅ All scores reset\n\nGame, Secret Mission, and Bonus Mission scores are now 0 for all groups."

        command = _parse_score_command(text)
        if command["matched"]:
            if not command["valid"]:
                return _invalid_score_command_message(command["reason"])
            group, game, score = command["group"], command["game"], command["score"]
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

        secret_command = _parse_secret_command(text)
        if secret_command["matched"]:
            if not secret_command["valid"]:
                return _invalid_secret_command_message(secret_command["reason"])
            try:
                result = await self.score_store.complete_secret_mission(
                    group=secret_command["group"],
                    game_master={"id": message.sender_id, "name": message.sender_name},
                    command=message.text,
                )
                standings = await self.score_store.leaderboard()
            except Exception:
                return "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues."
            if not result["changed"]:
                return _unchanged_secret_message(secret_command["group"], result["points"])
            await self.publisher.publish(self.announcement_chat_id, _secret_mission_announcement(secret_command["group"], result["points"]), pin=False)
            await self.publisher.publish(self.announcement_chat_id, _leaderboard_announcement(standings), pin=True)
            return _secret_mission_saved_message(secret_command["group"], result["points"])

        bonus_command = _parse_bonus_command(text)
        if bonus_command["matched"]:
            if not bonus_command["valid"]:
                return _invalid_bonus_command_message(bonus_command["reason"])
            action, group = bonus_command["action"], bonus_command["group"]
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
    if not parts or parts[0] != "/score":
        return {"matched": False}
    if len(parts) != 4:
        return {"matched": True, "valid": False, "reason": "Expected 3 parts after /score: group, game, and score."}

    _, group, game, score_text = parts
    if group not in GROUPS:
        return {"matched": True, "valid": False, "reason": f"Group must be one of: {GROUP_LISTING}."}
    if game not in GAMES:
        return {"matched": True, "valid": False, "reason": "Game must be one of: GameA, GameB, GameC, GameD, GameE, GameF."}
    if not score_text.isdigit():
        return {"matched": True, "valid": False, "reason": "Score must be a whole number from 1 to 10."}

    score = int(score_text)
    if not 1 <= score <= 10:
        return {"matched": True, "valid": False, "reason": "Score must be between 1 and 10."}
    return {"matched": True, "valid": True, "group": group, "game": game, "score": score}


def _parse_secret_command(text):
    parts = text.split()
    if not parts or parts[0] != "/secret":
        return {"matched": False}
    if len(parts) == 1:
        return {"matched": True, "valid": False, "reason": "Missing group after /secret."}
    if len(parts) != 2:
        return {"matched": True, "valid": False, "reason": "Use exactly 1 group after /secret."}

    _, group = parts
    if group not in GROUPS:
        return {"matched": True, "valid": False, "reason": f"Group must be one of: {GROUP_LISTING}."}
    return {"matched": True, "valid": True, "group": group}


def _parse_bonus_command(text):
    parts = text.split()
    if not parts or parts[0] != "/bonus":
        return {"matched": False}
    if len(parts) == 1:
        return {"matched": True, "valid": False, "reason": "Missing group after /bonus."}
    if parts[1] == "remove":
        if len(parts) == 2:
            return {"matched": True, "valid": False, "reason": "Missing group after /bonus remove."}
        if len(parts) != 3:
            return {"matched": True, "valid": False, "reason": "Use exactly 1 group after /bonus remove."}
        if parts[2] not in GROUPS:
            return {"matched": True, "valid": False, "reason": f"Group must be one of: {GROUP_LISTING}."}
        return {"matched": True, "valid": True, "action": "remove", "group": parts[2]}
    if len(parts) != 2:
        return {"matched": True, "valid": False, "reason": "Use /bonus <group> to add points, or /bonus remove <group> to undo 1 bonus mission."}
    if parts[1] not in GROUPS:
        return {"matched": True, "valid": False, "reason": f"Group must be one of: {GROUP_LISTING}."}
    return {"matched": True, "valid": True, "action": "add", "group": parts[1]}


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


def _invalid_score_command_message(reason):
    return (
        "❗ Invalid score command\n\n"
        "Why this happened\n"
        f"{reason}\n\n"
        "Command: /score <group> <game> <1-10>\n"
        "Usage: /score G1 GameA 10\n\n"
        f"Valid groups: {GROUP_LISTING}\n\n"
        "Valid games\n"
        f"{GAME_LISTING}"
    )


def _invalid_secret_command_message(reason):
    return (
        "❗ Invalid secret mission command\n\n"
        "Why this happened\n"
        f"{reason}\n\n"
        "Command: /secret <group>\n"
        "Usage: /secret G1\n\n"
        f"Valid groups: {GROUP_LISTING}"
    )


def _invalid_bonus_command_message(reason):
    return (
        "❗ Invalid bonus mission command\n\n"
        "Why this happened\n"
        f"{reason}\n\n"
        "Add a bonus mission\n"
        "Command: /bonus <group>\n"
        "Usage: /bonus G1\n\n"
        "Remove 1 mistaken bonus mission\n"
        "Command: /bonus remove <group>\n"
        "Usage: /bonus remove G1\n\n"
        f"Valid groups: {GROUP_LISTING}\n"
        "Rule: /bonus only works after /secret. Each /bonus adds 8 points."
    )


def _score_saved_message(group, game, score, is_first_score):
    title = "Score recorded!" if is_first_score else "Score updated!"
    return (
        f"✅ {title}\n\n"
        f"Group — {group}\n"
        f"Game — {_game_display(game)}\n"
        f"Score — {score}/10"
    )


def _unchanged_score_message(group, game, score):
    return (
        "ℹ️ No change\n\n"
        f"Group — {group}\n"
        f"Game — {_game_display(game)}\n"
        f"Score — already {score}/10"
    )


def _secret_mission_saved_message(group, points):
    return (
        "✅ Secret mission recorded\n\n"
        f"Group — {group}\n"
        f"Points awarded — {points}"
    )


def _unchanged_secret_message(group, points):
    return (
        "ℹ️ No change\n\n"
        f"Group — {group}\n"
        f"Secret Mission — already recorded as {points}"
    )


def _bonus_requires_secret_message(group):
    return (
        "❗ Bonus mission unavailable\n\n"
        f"Complete /secret for {group} before adding bonus mission points."
    )


def _bonus_mission_saved_message(group, added, total):
    return (
        "✅ Bonus mission recorded\n\n"
        f"Group — {group}\n"
        f"Bonus added — {added}\n"
        f"Bonus Mission total — {total}"
    )


def _bonus_mission_removed_message(group, removed, total):
    return (
        "✅ Bonus mission removed\n\n"
        f"Group — {group}\n"
        f"Bonus removed — {removed}\n"
        f"Bonus Mission total — {total}"
    )


def _unchanged_bonus_message(group):
    return (
        "ℹ️ No change\n\n"
        f"Group — {group}\n"
        f"Bonus Mission — already 0"
    )


def _completion_announcement(group, game, score):
    return (
        f"🎉 {_game_display(game)} complete\n\n"
        f"Group — {group}\n"
        f"Score — {score}/10"
    )


def _correction_announcement(group, game, previous_score, score):
    return (
        "✏️ Score updated\n\n"
        f"Group — {group}\n"
        f"Game — {_game_display(game)}\n"
        f"Score — {previous_score}/10 → {score}/10"
    )


def _secret_mission_announcement(group, points):
    return (
        "🎯 Secret mission completed\n\n"
        f"Group — {group}\n"
        f"Points awarded — {points}"
    )


def _bonus_mission_announcement(group, points, total):
    return (
        "🕵️ Bonus mission completed\n\n"
        f"Group — {group}\n"
        f"Points awarded — {points}\n"
        f"Bonus Mission total — {total}"
    )


def _bonus_mission_removed_announcement(group, removed, total):
    return (
        "↩️ Bonus mission removed\n\n"
        f"Group — {group}\n"
        f"Points removed — {removed}\n"
        f"Bonus Mission total — {total}"
    )


def _missions_reset_announcement():
    return (
        "🧹 Mission scores reset\n\n"
        "Secret Mission and Bonus Mission scores have been cleared for all groups."
    )


def _all_scores_reset_announcement():
    return (
        "🧹 All scores reset\n\n"
        "Game, Secret Mission, and Bonus Mission scores have been cleared for all groups."
    )


def _leaderboard_announcement(standings):
    ordered = sorted(standings, key=lambda standing: (-standing["total"], standing["group"]))
    seen_totals = set()
    lines = ["🏆 Leaderboard — Live Scores", ""]
    for index, standing in enumerate(ordered, start=1):
        medal = {1: "🥇 ", 2: "🥈 ", 3: "🥉 "}.get(index, "")
        tie_suffix = " (tie)" if standing["total"] in seen_totals else ""
        lines.append(f"{index}. {medal}{standing['group']} — {standing['total']} pts{tie_suffix}")
        seen_totals.add(standing["total"])
    return "\n".join(lines)
