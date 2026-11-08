"""Offline tests for opt-in ✅ rules reaction → Verified role.

These tests require no Discord token and make no network calls.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_member_verification as worker

GUILD = "1568675059894194239"
BOT = "12345"
RULES_CHANNEL = "555888"
RULES_MESSAGE = "999777"
VERIFIED = "67890"
BOT_ROLE = "55555"
ROLES = [
    {"id": GUILD, "name": "@everyone", "position": 0, "permissions": "0"},
    {"id": VERIFIED, "name": "Verified", "position": 4, "permissions": "0"},
    {"id": BOT_ROLE, "name": "Egypt YDNA Bot", "position": 8,
     "permissions": str(1 << 28)},
]

class ReactionVerificationTests(unittest.TestCase):
    def setUp(self):
        self.writes = []
        self.reactors = []
        self.members = {}
        self.rules_message = {
            "id": RULES_MESSAGE,
            "author": {"id": BOT, "bot": True},
            "content": worker.RULE_MARKER + "\nRead all ten rules.",
            "reactions": [{"emoji": {"name": "✅"}, "count": 2}],
        }

    def fake_api(self, method, path, data=None, allow_404=False):
        if method == "PUT":
            self.writes.append(path)
            return None
        if path == f"/guilds/{GUILD}":
            return {"name": "Egypt Y-DNA", "rules_channel_id": RULES_CHANNEL}
        if path == f"/guilds/{GUILD}/roles":
            return ROLES
        if path == "/users/@me":
            return {"id": BOT, "bot": True}
        if path == f"/guilds/{GUILD}/members/{BOT}":
            return {"roles": [BOT_ROLE]}
        if path == f"/guilds/{GUILD}/channels":
            return [{"id": RULES_CHANNEL, "type": 0, "name": "rules"}]
        if path == f"/channels/{RULES_CHANNEL}/messages?limit=100":
            return [self.rules_message] if self.rules_message else []
        if path.startswith(f"/channels/{RULES_CHANNEL}/messages/{RULES_MESSAGE}/reactions/"):
            return self.reactors
        if path.startswith(f"/guilds/{GUILD}/members/"):
            user = path.rsplit("/", 1)[1]
            if user in self.members:
                return self.members[user]
            if allow_404:
                return None
        raise AssertionError(f"Unexpected API request: {method} {path}")

    def run_worker(self):
        with patch.object(worker, "GUILD", GUILD), \
             patch.object(worker, "TOKEN", "example-not-a-secret"), \
             patch.object(worker, "api", side_effect=self.fake_api):
            worker.main()

    def test_reaction_verifies_only_human_clicker(self):
        self.reactors = [
            {"id": "1", "bot": False},
            {"id": BOT, "bot": True},
            {"id": "2", "bot": False},
            {"id": "3", "bot": False},
            {"id": "4", "bot": False},
        ]
        self.members = {
            "1": {"roles": [], "pending": False, "user": {"bot": False}},
            "2": {"roles": [], "pending": True, "user": {"bot": False}},
            "3": {"roles": [VERIFIED], "pending": False, "user": {"bot": False}},
            "4": {"roles": [], "pending": False, "user": {"bot": True}},
        }
        self.run_worker()
        self.assertEqual(
            self.writes, [f"/guilds/{GUILD}/members/1/roles/{VERIFIED}"]
        )

    def test_just_joining_never_verifies(self):
        self.members = {
            "1": {"roles": [], "pending": False, "user": {"bot": False}}
        }
        self.run_worker()
        self.assertEqual(self.writes, [])

    def test_missing_rules_post_fails_closed(self):
        self.rules_message = None
        with self.assertRaisesRegex(RuntimeError, "No official bot-authored"):
            self.run_worker()
        self.assertEqual(self.writes, [])

    def test_no_seeded_emoji_fails_closed(self):
        self.rules_message["reactions"] = []
        with self.assertRaisesRegex(RuntimeError, "No ✅"):
            self.run_worker()
        self.assertEqual(self.writes, [])

    def test_member_left_server_does_not_verify(self):
        self.reactors = [{"id": "5", "bot": False}]
        self.run_worker()
        self.assertEqual(self.writes, [])

    def test_missing_optional_pending_is_not_blocked(self):
        self.reactors = [{"id": "1", "bot": False}]
        self.members["1"] = {"roles": [], "user": {"bot": False}}
        self.run_worker()
        self.assertEqual(
            self.writes, [f"/guilds/{GUILD}/members/1/roles/{VERIFIED}"]
        )

    def test_existing_verified_is_idempotent(self):
        self.reactors = [{"id": "1", "bot": False}]
        self.members["1"] = {
            "roles": [VERIFIED], "user": {"bot": False}, "pending": False
        }
        self.run_worker()
        self.assertEqual(self.writes, [])

if __name__ == "__main__":
    unittest.main()
