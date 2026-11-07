"""Offline regression tests for native Discord Rules Screening → Verified.

No real Discord or GitHub credentials are needed. The fake API returns
member objects, including their official pending flag, and records role writes.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discord_member_verification as worker

GUILD = "1568675059894194239"
BOT_ID = "12345"
VERIFIED_ID = "67890"
MANAGED_BOT_ROLE = "55555"
ROLE_DATA = [
    {"id": GUILD, "name": "@everyone", "position": 0,
     "permissions": "0"},
    {"id": VERIFIED_ID, "name": "Verified", "position": 4,
     "permissions": "0"},
    {"id": MANAGED_BOT_ROLE, "name": "Egypt YDNA Bot", "position": 8,
     "permissions": str(1 << 28)},
]

class AutoVerificationTests(unittest.TestCase):
    def fake_api(self, method, path, data=None):
        if path == f"/guilds/{GUILD}":
            return {"name": "Egypt Y-DNA",
                    "features": [worker.SCREENING_FEATURE]}
        if path == f"/guilds/{GUILD}/roles":
            return ROLE_DATA
        if path == "/users/@me":
            return {"id": BOT_ID, "bot": True}
        if path == f"/guilds/{GUILD}/members/{BOT_ID}":
            return {"roles": [MANAGED_BOT_ROLE]}
        if method == "PUT":
            self.grants.append(path)
            return None
        raise AssertionError(f"Unexpected API request: {method} {path}")

    def setUp(self):
        self.grants = []

    def run_check(self, members):
        with patch.object(worker, "GUILD", GUILD), \
             patch.object(worker, "TOKEN", "test_only"), \
             patch.object(worker, "api", side_effect=self.fake_api), \
             patch.object(worker, "all_members", return_value=iter(members)):
            worker.main()

    @staticmethod
    def member(id_, pending=None, roles=None, is_bot=False, include_pending=True):
        out = {"user": {"id": str(id_), "bot": is_bot},
               "roles": roles or []}
        if include_pending:
            out["pending"] = pending
        return out

    def test_auto_verifies_only_confirmed_humans(self):
        self.run_check([
            self.member(1, False),
            self.member(2, True),
            self.member(3, include_pending=False),
            self.member(4, False, is_bot=True),
            self.member(5, False, roles=[VERIFIED_ID]),
        ])
        self.assertEqual(self.grants, [
            f"/guilds/{GUILD}/members/1/roles/{VERIFIED_ID}"
        ])

    def test_refuses_to_verify_when_screening_disabled(self):
        def fake_no_screen(method, path, data=None):
            if path == f"/guilds/{GUILD}":
                return {"name": "Egypt Y-DNA", "features": []}
            return self.fake_api(method, path, data)
        with patch.object(worker, "GUILD", GUILD), \
             patch.object(worker, "TOKEN", "test_only"), \
             patch.object(worker, "api", side_effect=fake_no_screen), \
             patch.object(worker, "all_members", return_value=iter([self.member(1, False)])):
            with self.assertRaisesRegex(RuntimeError, "Rules Screening"):
                worker.main()
        self.assertEqual(self.grants, [])

    def test_missing_pending_flag_never_counts_as_acceptance(self):
        self.run_check([
            self.member(1, include_pending=False),
            self.member(2, None),
        ])
        self.assertEqual(self.grants, [])

    def test_role_grant_is_idempotent(self):
        self.run_check([self.member(1, False, roles=[VERIFIED_ID])])
        self.assertEqual(self.grants, [])

if __name__ == "__main__":
    unittest.main()
