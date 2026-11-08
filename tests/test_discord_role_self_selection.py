"""Offline safety checks for Egypt Y-DNA reaction-based role assignment."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_role_reactions as worker

GUILD = "1568675059894194239"
BOT = "101"
ROLE_BOT = "200"
VERIFIED = "300"
E = "400"
J = "500"
CHANNEL = "600"
MESSAGE = "700"
GROUPS = [("**PICKER: E & J**", "Y-DNA", ["E-M2", "J1-P58"])]
ROLE_DATA = [
    {"id": GUILD, "name": "@everyone", "position": 0, "permissions": "0"},
    {"id": ROLE_BOT, "name": "Egypt YDNA Bot", "position": 20, "permissions": str(1 << 28)},
    {"id": VERIFIED, "name": "Verified", "position": 12, "permissions": "0"},
    {"id": E, "name": "E-M2", "position": 4, "permissions": "0"},
    {"id": J, "name": "J1-P58", "position": 5, "permissions": "0"},
]

class SelfSelectionTests(unittest.TestCase):
    def setUp(self):
        self.writes = []
        self.members = {
            "77": {"roles": [VERIFIED], "pending": False},
            "78": {"roles": [], "pending": False},
        }
        self.picks = {"🔵": ["77"], "🟢": []}

    def api(self, method, path, data=None, missing_ok=False):
        if method == "PUT":
            self.writes.append(path)
            return None
        if path == f"/guilds/{GUILD}":
            return {"id": GUILD, "name": "Egypt Y-DNA", "owner_id": "999"}
        if path == "/users/@me":
            return {"id": BOT}
        if path == f"/guilds/{GUILD}/roles":
            return ROLE_DATA
        if path == f"/guilds/{GUILD}/members/{BOT}":
            return {"roles": [ROLE_BOT]}
        if path == f"/guilds/{GUILD}/channels":
            return [{"name": "choose-roles", "id": CHANNEL, "type": 0}]
        if path == f"/channels/{CHANNEL}/messages?limit=100":
            return [{"id": MESSAGE, "author": {"id": BOT},
                     "content": "expected", "reactions": [
                         {"emoji": {"name": "🔵"}, "count": 2},
                         {"emoji": {"name": "🟢"}, "count": 1},
                     ]}]
        if path.startswith(f"/guilds/{GUILD}/members/"):
            return self.members.get(path.rsplit("/", 1)[1])
        raise AssertionError(f"Unexpected API {method} {path}")

    def run_worker(self):
        def fake_reactions(channel, message, emoji):
            return iter(self.picks.get(emoji, []))
        out = io.StringIO()
        with patch.object(worker, "GID", GUILD), \
             patch.object(worker, "TOKEN", "offline-placeholder"), \
             patch.object(worker, "api", side_effect=self.api), \
             patch.object(worker, "menu_groups", return_value=GROUPS), \
             patch.object(worker, "menu_content", return_value="expected"), \
             patch.object(worker, "menu_emojis", return_value=["🔵", "🟢"]), \
             patch.object(worker, "react_users", side_effect=fake_reactions), \
             redirect_stdout(out):
            worker.main()
        return out.getvalue()

    def test_new_verified_member_receives_role(self):
        logs = self.run_worker()
        self.assertEqual(self.writes, [f"/guilds/{GUILD}/members/77/roles/{E}"])
        self.assertIn("roles granted: 1", logs)

    def test_existing_role_does_not_get_duplicate(self):
        self.members["77"]["roles"] = [VERIFIED, E]
        logs = self.run_worker()
        self.assertEqual(self.writes, [])
        self.assertIn("already assigned: 1", logs)

    def test_unverified_is_not_granted_privileges(self):
        self.picks["🔵"] = ["78"]
        logs = self.run_worker()
        self.assertEqual(self.writes, [])
        self.assertIn("not Verified: 1", logs)

    def test_simultaneous_dna_choices_are_blocked(self):
        self.picks = {"🔵": ["77"], "🟢": ["77"]}
        logs = self.run_worker()
        self.assertEqual(self.writes, [])
        self.assertIn("[CONFLICT]", logs)
        self.assertIn("conflicting reactions: 2", logs)

if __name__ == "__main__":
    unittest.main()
