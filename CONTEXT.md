# Orientation Games

This context manages the scoring and public standings for an orientation game's teams and stations.

## Language

**Group**:
One of the six competing orientation groups. A group begins with zero and has one current score for each game.
_Avoid_: Team

**Game**:
One of the six orientation activities for which a group can receive a Score. Games are identified as `GameA` through `GameF`.
_Avoid_: Station, challenge

**Game Master**:
An authorized person who records a Group's game result from the configured Game Master Group.
_Avoid_: Scorekeeper, facilitator

**Game Master Group**:
The single private Telegram group from which the bot accepts score commands.
_Avoid_: Staff chat, admin group

**Announcement Channel**:
The Telegram chat where the bot publishes score updates and pins each new Leaderboard.
_Avoid_: Public group, broadcast chat

**Score**:
The current whole-number result, from 0 to 10 inclusive, for one group's game.
_Avoid_: Points

**Score Update**:
The replacement of a Group's current Score for one Game. The first Score Update records completion; later updates are corrections.
_Avoid_: Increment, add points

**Leaderboard**:
The public ranking of groups ordered only by total score.
_Avoid_: Standings

**Rank**:
A Group's displayed leaderboard position. Groups with the same total share a Rank, and groups within a shared Rank are listed alphabetically.
_Avoid_: Placement

**Audit Entry**:
An immutable record of a score change, including its former and new score, the Group, Game, Game Master, and time.
_Avoid_: History, log row

**Manual Correction**:
A direct change to the Scores sheet used only while the bot cannot reach Google Sheets. It remains the current source of truth and is accompanied by a manually entered Audit Entry.
_Avoid_: Offline overwrite
