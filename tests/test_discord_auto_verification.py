"""Offline tests: automatically Verified on join, no reaction required."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_member_verification as worker

GUILD = "1568675059894194239"
BOT = "12345"
VERIFIED = "67890"
BOT_ROLE = "55555"
JOIN_CHANNEL = "1568675061039370335"
ROLES = [
    {"id": GUILD, "name": "@everyone", "position": 0, "permissions": "0"},
    {"id": VERIFIED, "name": "Verified", "position": 4, "permissions": "0"},
    {"id": BOT_ROLE, "name": "Egypt YDNA Bot", "position": 8,
     "permissions": str(1 << 28)},
]


class AutoVerificationTests(unittest.TestCase):
    def setUp(self):
        self.writes = []
        self.full_list = None
        self.roles = [dict(role) for role in ROLES]
        self.members = {
            BOT: {"user": {"id": BOT, "bot": True}, "roles": [BOT_ROLE]}
        }
        self.messages = []
        self.flags = 6  # native join notices enabled; boost/tip notices suppressed

    def fake_api(self, method, path, data=None, allow_404=False, allow_403=False):
        if method == "PUT":
            self.writes.append(path)
            return None
        if method != "GET":
            raise AssertionError(f"Unexpected write: {method} {path}")
        if path == f"/guilds/{GUILD}":
            return {
                "id": GUILD, "name": "Egypt Y-DNA",
                "system_channel_id": JOIN_CHANNEL,
                "system_channel_flags": self.flags,
            }
        if path == f"/guilds/{GUILD}/roles":
            return self.roles
        if path == "/users/@me":
            return {"id": BOT, "bot": True}
        if path == f"/guilds/{GUILD}/members/{BOT}":
            return self.members[BOT]
        if path == f"/guilds/{GUILD}/members?limit=1000":
            if self.full_list is None:
                self.assertTrue(allow_403)
            return self.full_list
        if path == f"/guilds/{GUILD}/channels":
            return [{"id": JOIN_CHANNEL, "type": 0, "name": "🚪・in"}]
        if path == f"/channels/{JOIN_CHANNEL}/messages?limit=100":
            return self.messages
        if path.startswith(f"/guilds/{GUILD}/members/"):
            uid = path.rsplit("/", 1)[-1]
            if uid in self.members:
                return self.members[uid]
            if allow_404:
                return None
        raise AssertionError(f"Unexpected API: {method} {path}")

    def run_main(self):
        with patch.object(worker, "GUILD", GUILD), \
             patch.object(worker, "TOKEN", "mock-only"), \
             patch.object(worker, "api", side_effect=self.fake_api):
            worker.main()

    def join(self, uid, *, bot=False):
        self.messages.append({
            "id": str(1000000000000000000 - len(self.messages)),
            "type": 7,
            "author": {"id": str(uid), "bot": bot},
        })

    def test_new_join_gets_verified_without_reaction(self):
        self.join("100")
        self.members["100"] = {
            "user": {"id": "100", "bot": False}, "roles": []
        }
        self.run_main()
        self.assertEqual(
            self.writes, [f"/guilds/{GUILD}/members/100/roles/{VERIFIED}"]
        )

    def test_join_fallback_skips_bots_and_left_users(self):
        self.join("100")
        self.join("101", bot=True)
        self.join("102")
        self.members["100"] = {
            "user": {"id": "100", "bot": False}, "roles": []
        }
        self.run_main()
        self.assertEqual(
            self.writes, [f"/guilds/{GUILD}/members/100/roles/{VERIFIED}"]
        )

    def test_member_listing_assigns_unverified_without_emoji(self):
        self.full_list = [
            {"user": {"id": "100", "bot": False}, "roles": []},
            {"user": {"id": "101", "bot": True}, "roles": []},
            {"user": {"id": "102", "bot": False}, "roles": [VERIFIED]},
        ]
        self.run_main()
        self.assertEqual(
            self.writes, [f"/guilds/{GUILD}/members/100/roles/{VERIFIED}"]
        )

    def test_existing_verified_unchanged(self):
        self.join("100")
        self.members["100"] = {
            "user": {"id": "100", "bot": False}, "roles": [VERIFIED]
        }
        self.run_main()
        self.assertEqual(self.writes, [])

    def test_pending_member_can_get_role_but_native_screening_remains(self):
        self.join("100")
        self.members["100"] = {
            "user": {"id": "100", "bot": False}, "roles": [],
            "pending": True,
        }
        self.run_main()
        self.assertEqual(
            self.writes, [f"/guilds/{GUILD}/members/100/roles/{VERIFIED}"]
        )

    def test_missing_join_notices_fails_instead_of_false_success(self):
        with self.assertRaisesRegex(RuntimeError, "No native join notices"):
            self.run_main()
        self.assertEqual(self.writes, [])

    def test_disabled_join_notices_fails(self):
        self.flags = 7
        with self.assertRaisesRegex(RuntimeError, "announcements are disabled"):
            self.run_main()
        self.assertEqual(self.writes, [])

    def test_invalid_role_hierarchy_fails_without_writes(self):
        self.roles[1]["position"] = 9
        with self.assertRaisesRegex(RuntimeError, "role hierarchy"):
            self.run_main()
        self.assertEqual(self.writes, [])

    def test_privileged_verified_role_fails_without_writes(self):
        self.roles[1]["permissions"] = str(1 << 2)
        with self.assertRaisesRegex(RuntimeError, "nonzero server-wide"):
            self.run_main()
        self.assertEqual(self.writes, [])

    def test_duplicate_join_messages_only_assign_once(self):
        self.join("100")
        self.join("100")
        self.members["100"] = {
            "user": {"id": "100", "bot": False}, "roles": []
        }
        self.run_main()
        self.assertEqual(len(self.writes), 1)


if __name__ == "__main__":
    unittest.main()
