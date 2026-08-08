import unittest

from orientation_bot.service import BotService, IncomingMessage


SCORE_HELP_MESSAGE = (
    "❗ <b>Invalid score command</b>\n"
    "Please use:\n"
    "/score &lt;group&gt; &lt;game&gt; &lt;1-10&gt;\n"
    "──────────\n"
    "<b>Example:</b>\n"
    "/score G1 GameA 10\n"
    "──────────\n"
    "<b>Games:</b>\n"
    "GameA: Teochew Speed Drawing\n"
    "GameB: Connect Four Relay\n"
    "GameC: Unlock the Code\n"
    "GameD: The Photo Quest\n"
    "GameE: Minefield\n"
    "GameF: Qiaopi: The Missing Letter"
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
    "GameA: Teochew Speed Drawing\n"
    "GameB: Connect Four Relay\n"
    "GameC: Unlock the Code\n"
    "GameD: The Photo Quest\n"
    "GameE: Minefield\n"
    "GameF: Qiaopi: The Missing Letter\n"
    "──────────\n"
    "<b>Missions:</b>\n"
    "/secret &lt;group&gt;\n"
    "/bonus &lt;group&gt;\n"
    "/bonus remove &lt;group&gt;\n"
    "/resetmissions\n"
    "<b>Rule:</b> /bonus only works after /secret."
)


class BotServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_staff_can_record_a_first_score_and_publish_a_pinned_leaderboard(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(
            score_store=score_store,
            publisher=publisher,
            game_master_chat_id=-1001,
            announcement_chat_id=-1002,
        )

        reply = await bot.handle(
            IncomingMessage(
                chat_id=-1001,
                chat_type="group",
                sender_id=7,
                sender_name="Aisha",
                text="/score G1 GameA 8",
            )
        )

        self.assertEqual(
            "✅ <b>Score recorded!</b>\n<b>Group:</b> G1\n<b>Game:</b> Teochew Speed Drawing (Game A)\n<b>Score:</b> 8/10",
            reply,
        )
        self.assertEqual(8, score_store.score_for("G1", "GameA"))
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "🎉 <b>Teochew Speed Drawing (Game A) complete!</b>\n\n<b>Group:</b> G1\n<b>Score:</b> 8/10",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 8\n🥈 G2: 0\n🥈 G3: 0\n🥈 G4: 0\n🥈 G5: 0\n🥈 G6: 0",
                    "pin": True,
                },
            ],
            publisher.messages,
        )

    async def test_score_correction_uses_game_name_in_messages(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/score G1 GameA 6"))
        publisher.messages.clear()

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/score G1 GameA 8"))

        self.assertEqual(
            "✅ <b>Score updated!</b>\n<b>Group:</b> G1\n<b>Game:</b> Teochew Speed Drawing (Game A)\n<b>Score:</b> 8/10",
            reply,
        )
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "✏️ <b>Score updated</b>\n\n<b>Group:</b> G1\n<b>Game:</b> Teochew Speed Drawing (Game A)\n<b>Score:</b> 6/10 → 8/10",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 8\n🥈 G2: 0\n🥈 G3: 0\n🥈 G4: 0\n🥈 G5: 0\n🥈 G6: 0",
                    "pin": True,
                },
            ],
            publisher.messages,
        )

    async def test_secret_mission_awards_the_highest_remaining_points(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))

        self.assertEqual(
            "✅ <b>Secret mission recorded!</b>\n<b>Group:</b> G1\n<b>Points awarded:</b> 10",
            reply,
        )
        self.assertEqual(10, score_store.secret_points_for("G1"))
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "🎯 <b>Secret mission completed!</b>\n\n<b>Group:</b> G1\n<b>Points awarded:</b> 10",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 10\n🥈 G2: 0\n🥈 G3: 0\n🥈 G4: 0\n🥈 G5: 0\n🥈 G6: 0",
                    "pin": True,
                },
            ],
            publisher.messages,
        )

    async def test_secret_mission_can_only_be_done_once(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))
        publisher.messages.clear()

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))

        self.assertEqual(
            "ℹ️ <b>No change</b>\n<b>Group:</b> G1\n<b>Secret Mission:</b> already recorded as 10",
            reply,
        )
        self.assertEqual([], publisher.messages)

    async def test_bonus_requires_secret_mission_first(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus G1"))

        self.assertEqual(
            "❗ <b>Bonus mission unavailable</b>\nComplete /secret for G1 before adding bonus mission points.",
            reply,
        )

    async def test_bonus_mission_can_be_added_multiple_times(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))
        publisher.messages.clear()

        first_reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus G1"))
        second_reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus G1"))

        self.assertEqual(
            "✅ <b>Bonus mission recorded!</b>\n<b>Group:</b> G1\n<b>Bonus added:</b> 8\n<b>Bonus Mission total:</b> 8",
            first_reply,
        )
        self.assertEqual(
            "✅ <b>Bonus mission recorded!</b>\n<b>Group:</b> G1\n<b>Bonus added:</b> 8\n<b>Bonus Mission total:</b> 16",
            second_reply,
        )
        self.assertEqual(16, score_store.bonus_points_for("G1"))
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "🕵️ <b>Bonus mission completed!</b>\n\n<b>Group:</b> G1\n<b>Points awarded:</b> 8\n<b>Bonus Mission total:</b> 8",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 18\n🥈 G2: 0\n🥈 G3: 0\n🥈 G4: 0\n🥈 G5: 0\n🥈 G6: 0",
                    "pin": True,
                },
                {
                    "chat_id": -1002,
                    "html": "🕵️ <b>Bonus mission completed!</b>\n\n<b>Group:</b> G1\n<b>Points awarded:</b> 8\n<b>Bonus Mission total:</b> 16",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 26\n🥈 G2: 0\n🥈 G3: 0\n🥈 G4: 0\n🥈 G5: 0\n🥈 G6: 0",
                    "pin": True,
                },
            ],
            publisher.messages,
        )

    async def test_bonus_remove_removes_one_bonus_step(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))
        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus G1"))
        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus G1"))
        publisher.messages.clear()

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus remove G1"))

        self.assertEqual(
            "✅ <b>Bonus mission removed!</b>\n<b>Group:</b> G1\n<b>Bonus removed:</b> 8\n<b>Bonus Mission total:</b> 8",
            reply,
        )
        self.assertEqual(8, score_store.bonus_points_for("G1"))
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "↩️ <b>Bonus mission removed</b>\n\n<b>Group:</b> G1\n<b>Points removed:</b> 8\n<b>Bonus Mission total:</b> 8",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 18\n🥈 G2: 0\n🥈 G3: 0\n🥈 G4: 0\n🥈 G5: 0\n🥈 G6: 0",
                    "pin": True,
                },
            ],
            publisher.messages,
        )

    async def test_bonus_remove_requires_existing_bonus_points(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))
        publisher.messages.clear()

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus remove G1"))

        self.assertEqual(
            "ℹ️ <b>No change</b>\n<b>Group:</b> G1\n<b>Bonus Mission:</b> already 0",
            reply,
        )
        self.assertEqual([], publisher.messages)

    async def test_resetmissions_clears_secret_and_bonus_scores(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret G1"))
        await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus G1"))
        publisher.messages.clear()

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/resetmissions"))

        self.assertEqual(
            "✅ <b>Mission scores reset!</b>\nAll Secret Mission and Bonus Mission scores are now 0.",
            reply,
        )
        self.assertEqual(0, score_store.secret_points_for("G1"))
        self.assertEqual(0, score_store.bonus_points_for("G1"))
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "🧹 <b>Mission scores reset</b>\n\nSecret Mission and Bonus Mission scores have been cleared for all groups.",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 G1: 0\n🥇 G2: 0\n🥇 G3: 0\n🥇 G4: 0\n🥇 G5: 0\n🥇 G6: 0",
                    "pin": True,
                },
            ],
            publisher.messages,
        )

    async def test_direct_messages_receive_the_access_instruction(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(
            IncomingMessage(
                chat_id=99,
                chat_type="private",
                sender_id=99,
                sender_name="Unauthorised user",
                text="/score G1 GameA 8",
            )
        )

        self.assertEqual("You are not an authenticated user. Contact @iamrolling if you require access.", reply)
        self.assertEqual(0, score_store.score_for("G1", "GameA"))
        self.assertEqual([], publisher.messages)

    async def test_staff_receive_a_helpful_validation_error_for_an_invalid_score(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(
            IncomingMessage(
                chat_id=-1001,
                chat_type="group",
                sender_id=7,
                sender_name="Aisha",
                text="/score G1 GameA 11",
            )
        )

        self.assertEqual(SCORE_HELP_MESSAGE, reply)

    async def test_zero_is_rejected_in_the_score_validation_message(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(
            IncomingMessage(
                chat_id=-1001,
                chat_type="group",
                sender_id=7,
                sender_name="Aisha",
                text="/score G1 GameA 0",
            )
        )

        self.assertEqual(SCORE_HELP_MESSAGE, reply)

    async def test_legacy_game_names_are_rejected(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(
            IncomingMessage(-1001, "group", 7, "Aisha", "/score G1 Game1 8")
        )

        self.assertEqual(SCORE_HELP_MESSAGE, reply)

    async def test_secret_without_group_shows_linked_mission_help(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/secret"))

        self.assertEqual(MISSION_HELP_MESSAGE, reply)

    async def test_bonus_without_group_shows_linked_mission_help(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/bonus"))

        self.assertEqual(MISSION_HELP_MESSAGE, reply)

    async def test_group_commands_addressed_to_this_bot_are_accepted(self):
        bot = BotService(
            MemoryScoreStore(),
            RecordingPublisher(),
            game_master_chat_id=-1001,
            announcement_chat_id=-1002,
            bot_username="chaommunity_bot",
        )

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/help@chaommunity_bot"))

        self.assertEqual(HELP_MESSAGE, reply)

    async def test_group_commands_addressed_to_another_bot_are_ignored(self):
        bot = BotService(
            MemoryScoreStore(),
            RecordingPublisher(),
            game_master_chat_id=-1001,
            announcement_chat_id=-1002,
            bot_username="chaommunity_bot",
        )

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/score@other_bot G1 GameA 8"))

        self.assertIsNone(reply)

    async def test_sheet_failure_rejects_the_score_without_an_announcement(self):
        publisher = RecordingPublisher()
        bot = BotService(FailingScoreStore(), publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(
            IncomingMessage(
                chat_id=-1001,
                chat_type="group",
                sender_id=7,
                sender_name="Aisha",
                text="/score G1 GameA 8",
            )
        )

        self.assertEqual(
            "Could not update Google Sheets. Please retry; use the manual sheet fallback if the problem continues.",
            reply,
        )
        self.assertEqual([], publisher.messages)

    async def test_unchanged_repeated_score_does_not_publish_again(self):
        score_store = MemoryScoreStore()
        publisher = RecordingPublisher()
        bot = BotService(score_store, publisher, game_master_chat_id=-1001, announcement_chat_id=-1002)
        message = IncomingMessage(-1001, "group", 7, "Aisha", "/score G1 GameA 8")

        await bot.handle(message)
        publisher.messages.clear()
        reply = await bot.handle(message)

        self.assertEqual(
            "ℹ️ <b>No change</b>\n<b>Group:</b> G1\n<b>Game:</b> Teochew Speed Drawing (Game A)\n<b>Score:</b> already 8/10",
            reply,
        )
        self.assertEqual([], publisher.messages)


class MemoryScoreStore:
    SECRET_SEQUENCE = (10, 9, 8, 7, 6, 5)

    def __init__(self):
        self.scores = {}
        self.secret_points = {group: 0 for group in ("G1", "G2", "G3", "G4", "G5", "G6")}
        self.bonus_points = {group: 0 for group in ("G1", "G2", "G3", "G4", "G5", "G6")}

    async def replace_score(self, group, game, score, game_master, command):
        key = (group, game)
        previous_score = self.scores.get(key, 0)
        is_first_score = key not in self.scores
        self.scores[key] = score
        return {
            "previous_score": previous_score,
            "is_first_score": is_first_score,
            "changed": previous_score != score,
        }

    async def complete_secret_mission(self, group, game_master, command):
        previous_score = self.secret_points[group]
        if previous_score:
            return {"changed": False, "points": previous_score}
        used = {score for score in self.secret_points.values() if score}
        awarded = next(score for score in self.SECRET_SEQUENCE if score not in used)
        self.secret_points[group] = awarded
        return {"changed": True, "points": awarded}

    async def add_bonus_mission(self, group, game_master, command):
        if not self.secret_points[group]:
            return {"changed": False, "reason": "secret_required"}
        total = self.bonus_points[group] + 8
        self.bonus_points[group] = total
        return {"changed": True, "added": 8, "total": total}

    async def remove_bonus_mission(self, group, game_master, command):
        total = self.bonus_points[group]
        if total == 0:
            return {"changed": False, "total": 0}
        total -= 8
        self.bonus_points[group] = total
        return {"changed": True, "removed": 8, "total": total}

    async def reset_missions(self, game_master, command):
        changed = any(self.secret_points.values()) or any(self.bonus_points.values())
        self.secret_points = {group: 0 for group in self.secret_points}
        self.bonus_points = {group: 0 for group in self.bonus_points}
        return {"changed": changed}

    async def leaderboard(self):
        return [
            {
                "group": group,
                "total": sum(score for (stored_group, _), score in self.scores.items() if stored_group == group)
                + self.secret_points[group]
                + self.bonus_points[group],
            }
            for group in ("G1", "G2", "G3", "G4", "G5", "G6")
        ]

    def score_for(self, group, game):
        return self.scores.get((group, game), 0)

    def secret_points_for(self, group):
        return self.secret_points[group]

    def bonus_points_for(self, group):
        return self.bonus_points[group]


class RecordingPublisher:
    def __init__(self):
        self.messages = []

    async def publish(self, chat_id, html, pin):
        self.messages.append({"chat_id": chat_id, "html": html, "pin": pin})


class FailingScoreStore:
    async def replace_score(self, **_):
        raise RuntimeError("Google Sheets unavailable")

    async def leaderboard(self):
        return []
