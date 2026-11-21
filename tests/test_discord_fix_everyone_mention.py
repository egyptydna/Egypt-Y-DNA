"""Offline non-destructive tests for legacy @E role mention fix."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_fix_everyone_mention as fix

GID = "1568675059894194239"
BOT_ID = "123"
BOT_ROLE_ID = "456"
E_ROLE_ID = "789"

class MentionFixTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.old_name = "E"
        self.legacy = {
            "id": E_ROLE_ID, "name": self.old_name, "permissions": "0",
            "position": 2, "managed": False,
        }
        self.roles = [
            {"id": GID, "name": "@everyone", "permissions": "0",
             "position": 0},
            {"id": BOT_ROLE_ID, "name": "Egypt YDNA Bot",
             "permissions": str(fix.MANAGE_ROLES), "position": 10},
            self.legacy,
        ]

    def fake_api(self, method, path, data=None):
        self.calls.append((method, path, data))
        if method == "GET":
            if path == f"/guilds/{GID}":
                return {"id": GID, "name": "Egypt Y-DNA"}
            if path == f"/guilds/{GID}/roles":
                return self.roles
            if path == "/users/@me":
                return {"id": BOT_ID}
            if path == f"/guilds/{GID}/members/{BOT_ID}":
                return {"roles": [BOT_ROLE_ID]}
        if method == "PATCH" and path == f"/guilds/{GID}/roles/{E_ROLE_ID}":
            self.legacy["name"] = data["name"]
            return {}
        raise AssertionError(f"Unexpected API request {method} {path}")

    def run_main(self, mode):
        with patch.object(fix, "GID", GID), \
             patch.object(fix, "TOKEN", "mock-token"), \
             patch.object(fix, "MODE", mode), \
             patch.object(fix, "api", side_effect=self.fake_api):
            fix.main()

    def test_preview_no_changes(self):
        self.run_main("preview")
        self.assertEqual(self.legacy["name"], "E")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

    def test_apply_renames_only_existing_role(self):
        self.run_main("apply")
        self.assertEqual(self.legacy["name"], fix.NEW_NAME)
        writes = [call for call in self.calls if call[0] != "GET"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1], f"/guilds/{GID}/roles/{E_ROLE_ID}")
        self.assertEqual(writes[0][2], {"name": fix.NEW_NAME})
        self.assertEqual(self.legacy["permissions"], "0")
        self.assertEqual(self.legacy["id"], E_ROLE_ID)

    def test_second_run_no_changes(self):
        self.run_main("apply")
        self.calls.clear()
        self.run_main("apply")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

    def test_managed_role_fails_safe(self):
        self.legacy["managed"] = True
        with self.assertRaisesRegex(RuntimeError, "managed integration"):
            self.run_main("apply")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

    def test_duplicate_target_name_fails_safe(self):
        self.roles.append({
            "id": "900", "name": fix.NEW_NAME, "position": 3,
            "permissions": "0",
        })
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            self.run_main("apply")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

    def test_bot_below_role_fails_safe(self):
        self.legacy["position"] = 11
        with self.assertRaisesRegex(RuntimeError, "at or above"):
            self.run_main("apply")
        self.assertFalse([call for call in self.calls if call[0] != "GET"])

if __name__ == "__main__":
    unittest.main()
