"""Offline tests for the Founder-only mention permission workflow."""
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_founder_mentions as script

GID = "1568675059894194239"
OWNER_BOT = "900"
BOT_ROLE = "901"
FOUNDER = "902"

class MentionTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.founder_permissions = 1 << 4

    def fake_api(self, method, endpoint, data=None):
        self.calls.append((method, endpoint, data))
        if method == "GET" and endpoint == f"/guilds/{GID}":
            return {"name": "Egypt Y-DNA"}
        if method == "GET" and endpoint == f"/guilds/{GID}/roles":
            return [
                {"id": GID, "name": "@everyone", "permissions": "0",
                 "position": 0},
                {"id": FOUNDER, "name": "Founder",
                 "permissions": str(self.founder_permissions),
                 "position": 5},
                {"id": BOT_ROLE, "name": "Egypt YDNA Bot",
                 "permissions": str(script.MANAGE_ROLES),
                 "position": 10},
                {"id": "903", "name": "Verified", "permissions": "0",
                 "position": 2},
            ]
        if method == "GET" and endpoint == "/users/@me":
            return {"id": OWNER_BOT}
        if method == "GET" and endpoint == f"/guilds/{GID}/members/{OWNER_BOT}":
            return {"roles": [BOT_ROLE]}
        if method == "PATCH" and endpoint == f"/guilds/{GID}/roles/{FOUNDER}":
            self.founder_permissions = int(data["permissions"])
            return None
        raise AssertionError(f"Unexpected Discord call: {method} {endpoint}")

    def run_worker(self, mode):
        with patch.object(script, "GID", GID), \
             patch.object(script, "TOKEN", "fake-for-tests"), \
             patch.object(script, "MODE", mode), \
             patch.object(script, "api", side_effect=self.fake_api):
            script.main()

    def test_preview_does_not_mutate(self):
        self.run_worker("preview")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

    def test_apply_only_changes_founder_permissions(self):
        self.run_worker("apply")
        writes = [call for call in self.calls if call[0] != "GET"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1], f"/guilds/{GID}/roles/{FOUNDER}")
        self.assertEqual(
            int(writes[0][2]["permissions"]),
            (1 << 4) | script.MENTION_EVERYONE
        )

    def test_idempotent(self):
        self.founder_permissions |= script.MENTION_EVERYONE
        self.run_worker("apply")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

    def test_missing_role_fails_closed(self):
        original = self.fake_api
        def missing(method, endpoint, data=None):
            result = original(method, endpoint, data)
            if endpoint == f"/guilds/{GID}/roles":
                return [role for role in result if role["name"] != "Founder"]
            return result
        with patch.object(script, "GID", GID), \
             patch.object(script, "TOKEN", "fake-for-tests"), \
             patch.object(script, "MODE", "apply"), \
             patch.object(script, "api", side_effect=missing):
            with self.assertRaisesRegex(RuntimeError, "Exactly one Founder"):
                script.main()
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

if __name__ == "__main__":
    unittest.main()
