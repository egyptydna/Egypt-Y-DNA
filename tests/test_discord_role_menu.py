"""Sanity tests for role menus: no ancestor+child redundancy, no unsafe roles."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from discord_role_menu import (
    SELECTABLE_ORIGINS, SELECTABLE_YDNA,
    FLAG_EMOJIS, ROLE_EMOJIS,
    menu_groups, menu_content, menu_emojis,
)

class RoleMenuTests(unittest.TestCase):
    def setUp(self):
        all_names = SELECTABLE_ORIGINS + SELECTABLE_YDNA + ("Male", "Female")
        self.roles = {name.casefold(): {"name": name, "permissions": "0"} for name in all_names}
        self.groups = menu_groups(self.roles)

    def test_no_generic_parent_letters(self):
        self.assertFalse(any(len(name) == 1 for name in SELECTABLE_YDNA))
        # J1 is deliberately allowed: not every J1 lineage belongs to P58.
        for umbrella in ["J", "J2", "R", "R1b", "E", "E-M35", "E-M78", "T-M70"]:
            self.assertNotIn(umbrella, SELECTABLE_YDNA)

    def test_flags_for_north_africa(self):
        self.assertEqual(FLAG_EMOJIS["Egypt"], "🇪🇬")
        self.assertEqual(FLAG_EMOJIS["Morocco"], "🇲🇦")
        self.assertEqual(FLAG_EMOJIS["Algeria"], "🇩🇿")
        self.assertEqual(FLAG_EMOJIS["Tunisia"], "🇹🇳")
        self.assertEqual(FLAG_EMOJIS["Libya"], "🇱🇾")

    def test_reactions_and_message_length(self):
        for marker, category, names in self.groups:
            emojis = menu_emojis(category, names)
            self.assertLessEqual(len(names), 20, marker)
            self.assertEqual(len(emojis), len(set(emojis)), marker)
            self.assertLessEqual(len(menu_content(marker, category, names)), 2000)

    def test_staff_never_self_selectable(self):
        selected = [n for _, _, names in self.groups for n in names]
        for restricted in ("Founder", "Administrator", "Moderator",
                           "Verified", "Member", "Bot", "Verified Y-DNA Tester"):
            self.assertNotIn(restricted, selected)

    def test_specific_roles_present(self):
        for name in ("E-M81", "J1", "J1-P58", "J2a", "J2b", "R1b-V88", "Q1", "Q2"):
            self.assertIn(name, SELECTABLE_YDNA)

    def test_e_v12_replaces_e_v32(self):
        self.assertIn("E-V12", SELECTABLE_YDNA)
        self.assertNotIn("E-V32", SELECTABLE_YDNA)

    def test_north_african_country_roles_present(self):
        for name in ("Egypt", "Morocco", "Algeria", "Tunisia", "Libya", "Sudan", "Mauritania"):
            self.assertIn(name, SELECTABLE_ORIGINS)

if __name__ == "__main__":
    unittest.main()
