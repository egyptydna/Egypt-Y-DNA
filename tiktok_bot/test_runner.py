import unittest
from .runner import eligible, lineage, caption, fingerprint, sources


class ReviewBotTests(unittest.TestCase):
    def sample(self):
        return {
            "id": 901, "created_at": "2026-11-17T10:00:00+00:00",
            "sync_visibility": "public", "owner_active": True,
            "origin_raw": "Cairo, Egypt", "governorate": "Cairo",
            "y_dna": "E-FT178335", "test_type": "Big Y-700",
            "full_snp_path": "E-M35 > E-M78 > E-V22 > E-FT178335",
            "y_link_1": "https://www.familytreedna.com/public/E-M35",
            "y_link_2": "—",
        }

    def test_eligible_public_with_explicit_egypt_origin(self):
        self.assertTrue(eligible(self.sample()))

    def test_reject_private_and_unproven_origin(self):
        sample = self.sample()
        sample["sync_visibility"] = "withdrawn"
        self.assertFalse(eligible(sample))
        sample = self.sample()
        sample["sync_visibility"] = "public"
        sample["origin_raw"] = "Unknown"
        self.assertFalse(eligible(sample))

    def test_no_external_fake_source(self):
        sample = self.sample()
        sample["y_link_1"] = "https://malicious.example.com/fake"
        self.assertFalse(eligible(sample))
        self.assertEqual(sources(sample), [])

    def test_lineage_no_invented_ancestry(self):
        sample = self.sample()
        self.assertEqual(lineage(sample), ["E-M35", "E-M78", "E-V22", "E-FT178335"])
        sample["full_snp_path"] = "J1 > J-P58"
        self.assertEqual(lineage(sample), ["E-FT178335"])

    def test_no_name_or_kit_in_caption(self):
        sample = self.sample()
        sample.update(name="NotForPublishing", kit_number="123456")
        text = caption(sample)
        self.assertNotIn("NotForPublishing", text)
        self.assertNotIn("123456", text)
        self.assertIn("E-FT178335", text)

    def test_modified_source_changes_review_digest(self):
        sample = self.sample()
        digest = fingerprint(sample)
        sample["y_dna"] = "E-V22"
        self.assertNotEqual(digest, fingerprint(sample))


if __name__ == "__main__":
    unittest.main()
