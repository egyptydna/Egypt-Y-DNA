"""No-network tests for the independent YFull/FTDNA Egypt snapshot checker."""
import unittest
from .source_watch import extract_new_yfull, extract_snapshot_dates, text_content


HTML = """
<section id="recent">
<p>FTDNA: provider copies. YFull has a dated snapshot.</p>
<div class="m-note">new kits, 2026-10-09 → 2026-11-13</div>
<div class="m-note">new samples as of 2026-11-02</div>
<h3 class="rec-h">Y-DNA: branches that grew</h3>
<ul><li><b>E-M35</b>: +2</li></ul>
<h3 class="rec-h">New Y-DNA samples in YFull</h3>
<ul class="plain cols">
<li><b>A-PH3663</b></li>
<li><b>E-Y620430</b></li>
</ul>
<h3 class="rec-h">New mtDNA samples in YFull</h3>
<ul><li><b>L3e1</b></li></ul>
</section>
"""


class ExternalSourceTests(unittest.TestCase):
    def test_yfull_new_only_not_existing_tree(self):
        self.assertEqual(extract_new_yfull(HTML), ["A-PH3663", "E-Y620430"])

    def test_dates_are_dates_of_original_copies(self):
        self.assertEqual(extract_snapshot_dates(HTML), ("2026-11-02", "2026-11-13"))

    def test_missing_yfull_section_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_new_yfull("<h3>Tree branches</h3><ul><li>J-P58</li></ul>")

    def test_not_interpreting_mtdna_as_y_dna(self):
        other = HTML.replace("<li><b>E-Y620430</b></li>", "")
        self.assertEqual(extract_new_yfull(other), ["A-PH3663"])

    def test_html_entities_safe(self):
        self.assertEqual(text_content("<b>E-PF2179*</b>"), "E-PF2179*")


if __name__ == "__main__":
    unittest.main()
