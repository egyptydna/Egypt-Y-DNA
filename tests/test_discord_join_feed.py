"""Offline tests for the free native Discord join feed (no Discord token)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_join_feed as join

GID = "1568675059894194239"
SOURCE = "1568675061039370335"
BOT = "9900"
STAFF = [
    {"id": "100", "name": "Founder", "position": 20, "permissions": "0"},
    {"id": "101", "name": "Administrator", "position": 19, "permissions": "0"},
    {"id": "102", "name": "Moderator", "position": 18, "permissions": "0"},
]
ROLES = [
    {"id": GID, "name": "@everyone", "permissions": "0"},
    {"id": "200", "name": "Verified", "permissions": "0"},
    {"id": "300", "name": "Egypt YDNA Bot",
     "permissions": str(join.MANAGE_GUILD | join.MANAGE_CHANNELS)},
] + STAFF

class JoinFeedTests(unittest.TestCase):
    def setUp(self):
        self.writes = []
        self.guild = {
            "name": "Egypt Y-DNA",
            "system_channel_id": "9090",
            "system_channel_flags": 3,  # joins + boosts previously suppressed
        }
        self.channels = [
            {"id": SOURCE, "name": "general", "type": 0,
             "parent_id": "411", "permission_overwrites": [],
             "topic": None},
            {"id": "401", "name": "rules", "type": 0},
            {"id": "411", "name": "📌 START HERE", "type": 4},
        ]

    def fake_api(self, method, endpoint, data=None):
        if method == "PATCH":
            self.writes.append((endpoint, data))
            return {}
        if endpoint == f"/guilds/{GID}":
            return self.guild
        if endpoint == "/users/@me":
            return {"id": BOT}
        if endpoint == f"/guilds/{GID}/roles":
            return ROLES
        if endpoint == f"/guilds/{GID}/members/{BOT}":
            return {"roles": ["300"]}
        if endpoint == f"/guilds/{GID}/channels":
            return self.channels
        raise AssertionError(f"Unexpected API call: {method} {endpoint}")

    def run_workflow(self, mode):
        with patch.object(join, "GUILD", GID), \
             patch.object(join, "TOKEN", "dummy"), \
             patch.object(join, "MODE", mode), \
             patch.object(join, "api", side_effect=self.fake_api):
            join.main()

    def test_preview_is_read_only(self):
        self.run_workflow("preview")
        self.assertEqual(self.writes, [])

    def test_apply_renames_same_channel_and_turns_join_notices_on(self):
        self.run_workflow("apply")
        self.assertEqual(len(self.writes), 2)
        path, payload = self.writes[0]
        self.assertEqual(path, f"/channels/{SOURCE}")
        self.assertEqual(payload["name"], join.JOIN_NAME)
        self.assertEqual(payload["parent_id"], "411")
        self.assertEqual(self.writes[1][0], f"/guilds/{GID}")
        self.assertEqual(self.writes[1][1]["system_channel_id"], SOURCE)
        self.assertEqual(self.writes[1][1]["system_channel_flags"] & 1, 0)
        self.assertNotIn("DELETE", [endpoint for endpoint, _ in self.writes])

    def test_read_only_includes_thread_prevention(self):
        permissions = join.read_only_permissions(
            GID, "200", ["100", "101", "102"], BOT)
        required_deny = (join.SEND | join.SEND_IN_THREADS |
                         join.CREATE_PUBLIC_THREADS | join.CREATE_PRIVATE_THREADS)
        for permission in permissions[:-1]:
            self.assertEqual(int(permission["deny"]) & required_deny, required_deny)
        self.assertEqual(permissions[-1]["type"], 1)

    def test_does_not_create_second_channel(self):
        self.channels.append({"id": "499", "name": join.JOIN_NAME, "type": 0})
        self.run_workflow("apply")
        self.assertEqual(len(self.writes), 2)
        self.assertFalse(any("/channels" in url and url.startswith("/guilds/")
                             for url, _ in self.writes))

if __name__ == "__main__":
    unittest.main()
