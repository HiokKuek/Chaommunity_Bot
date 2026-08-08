import unittest

from orientation_bot.service import BotService, IncomingMessage


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

        self.assertEqual("✅ Score recorded\nG1 · GameA · 8/10", reply)
        self.assertEqual(8, score_store.score_for("G1", "GameA"))
        self.assertEqual(
            [
                {
                    "chat_id": -1002,
                    "html": "🎉 <b>GameA complete!</b>\n\n<b>Group</b> · G1\n<b>Score</b> · 8 / 10",
                    "pin": False,
                },
                {
                    "chat_id": -1002,
                    "html": "🏆 <b>Leaderboard</b>\n<i>Live scores</i>\n\n🥇 <b>G1</b> · <b>8</b>\n🥈 <b>G2</b> · <b>0</b>\n🥈 <b>G3</b> · <b>0</b>\n🥈 <b>G4</b> · <b>0</b>\n🥈 <b>G5</b> · <b>0</b>\n🥈 <b>G6</b> · <b>0</b>",
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

        self.assertEqual("Invalid score format. Use: /score G1 GameA 8 (score must be 0-10).", reply)

    async def test_legacy_game_names_are_rejected(self):
        bot = BotService(MemoryScoreStore(), RecordingPublisher(), game_master_chat_id=-1001, announcement_chat_id=-1002)

        reply = await bot.handle(
            IncomingMessage(-1001, "group", 7, "Aisha", "/score G1 Game1 8")
        )

        self.assertEqual("Invalid score format. Use: /score G1 GameA 8 (score must be 0-10).", reply)

    async def test_group_commands_addressed_to_this_bot_are_accepted(self):
        bot = BotService(
            MemoryScoreStore(),
            RecordingPublisher(),
            game_master_chat_id=-1001,
            announcement_chat_id=-1002,
            bot_username="chaommunity_bot",
        )

        reply = await bot.handle(IncomingMessage(-1001, "group", 7, "Aisha", "/help@chaommunity_bot"))

        self.assertEqual("Record or correct a score:\n/score G1 GameA 8\n\nUse a whole number from 0 to 10. Use /leaderboard to show current standings.", reply)

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

        self.assertEqual("No change: G1 already has 8/10 for GameA.", reply)
        self.assertEqual([], publisher.messages)


class MemoryScoreStore:
    def __init__(self):
        self.scores = {}

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

    async def leaderboard(self):
        return [
            {
                "group": group,
                "total": sum(score for (stored_group, _), score in self.scores.items() if stored_group == group),
            }
            for group in ("G1", "G2", "G3", "G4", "G5", "G6")
        ]

    def score_for(self, group, game):
        return self.scores.get((group, game), 0)


class RecordingPublisher:
    def __init__(self):
        self.messages = []

    async def publish(self, chat_id, html, pin):
        self.messages.append({"chat_id": chat_id, "html": html, "pin": pin})


class FailingScoreStore:
    async def replace_score(self, **_):
        raise RuntimeError("Google Sheets unavailable")
