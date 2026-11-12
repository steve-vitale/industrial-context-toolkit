"""The corpus depth register: docs/CORPUS_DEPTH.md is current, every acquired group has an area and a derived status,
the feeding rule finds real matrix cells, and a status can never be typed into a registry. Stdlib only."""
import copy
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import corpus_depth as cd  # noqa: E402


def with_groups(edit):
    """build() with the real registries passed through edit(groups)."""
    real = cd.load_groups

    def fake(root=cd.ROOT):
        groups, problems = real(root)
        groups = copy.deepcopy(groups)
        edit(groups)
        return groups, problems
    with patch.object(cd, "load_groups", fake):
        return cd.build()


class Register(unittest.TestCase):
    def test_doc_is_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_depth.py"), "--check"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_group_has_an_area_and_one_status(self):
        rows, _, problems = cd.build()
        self.assertEqual(problems, [])
        self.assertEqual(len(rows), 49, "docs/DEPTH_GOAL.md counts 49 acquired groups")
        self.assertTrue(all(r["area"] != "?" for r in rows))
        self.assertTrue(all(r["status"] in cd.STATUS_ORDER for r in rows))

    def test_unplanned_is_loud_and_first(self):
        rows, earlier, _ = cd.build()
        text = cd.page(rows, earlier)
        n = sum(r["status"] == cd.UNPLANNED for r in rows)
        self.assertLess(text.index(f"## UNPLANNED: {n} of {len(rows)}"), text.index("## The register"))
        self.assertLess(text.index("## Next to wire"), text.index("## The register"))
        if n:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_depth.py"), "--strict"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 1, "--strict must fail while any group is UNPLANNED")

    def test_feeding_rule_finds_real_cells_on_earlier_sources(self):
        # Positive control: sources that do feed the matrix are found by the same rule the 49 groups go through.
        _, earlier, _ = cd.build()
        by_id = {e["id"]: e for e in earlier}
        self.assertIn("hai-21.03", by_id["hai"]["inputs"])
        self.assertTrue(any(c["row"] == 6 and c["status"] in cd.SCORED for c in by_id["hai"]["cells"]))
        self.assertIn("historian-csv", by_id["skab"]["features"])

    def test_a_group_feeds_only_through_a_scored_cell(self):
        corpus = cd.read_json(cd.CORPUS)
        matrix = cd.read_json(cd.MATRIX)
        corpus["inputs"].append({"id": "x-input", "fetch": "python examples/public-data/fetch_sources.py uci-secom"})
        real = cd.read_json

        def fake(rel, root=cd.ROOT):
            return {cd.CORPUS: corpus, cd.MATRIX: matrix}.get(rel) or real(rel, root)
        for status, expected in (("needs data", cd.UNPLANNED), ("fail", cd.FEEDS)):
            matrix["cells"] = [c for c in matrix["cells"] if c["input"] != "x-input"]
            matrix["cells"].append({"row": 6, "input": "x-input", "status": status})
            with patch.object(cd, "read_json", fake):
                rows, _, _ = cd.build()
            row = next(r for r in rows if r["id"] == "uci-secom")
            self.assertEqual(row["status"], expected, status)
        self.assertIn("historian-csv", row["features"])

    def test_status_cannot_be_typed_into_a_registry(self):
        def edit(groups):
            groups["maintie"][1]["depth"]["status"] = "feeds a scored task"
        _, _, problems = with_groups(edit)
        self.assertTrue(any("maintie: depth.status is derived" in p for p in problems))

    def test_unbacked_evaluation_claim_is_refused(self):
        def edit(groups):
            groups["uci-ai4i"][1]["evidence_role"] = "evaluated"
        _, _, problems = with_groups(edit)
        self.assertTrue(any("uci-ai4i: evidence_role 'evaluated' claims evaluation" in p for p in problems))

    def test_a_plan_needs_date_key_task_and_existing_evidence(self):
        def undated(groups):
            groups["maintie"][1]["depth"]["plan"] = {"key": "gold annotations", "task": "x", "evidence": [cd.GOAL]}

        def missing(groups):
            groups["maintie"][1]["depth"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t",
                                                     "evidence": ["docs/NO_SUCH_PLAN.md"]}
        rows, _, problems = with_groups(undated)
        self.assertTrue(any("maintie: depth.plan needs" in p for p in problems))
        self.assertEqual(next(r for r in rows if r["id"] == "maintie")["status"], cd.UNPLANNED)
        _, _, problems = with_groups(missing)
        self.assertTrue(any("NO_SUCH_PLAN.md does not exist" in p for p in problems))

    def test_retirement_needs_a_reason_and_wins_over_unplanned(self):
        def edit(groups):
            groups["wine-competition"][1]["depth"]["retired"] = {"reason": "", "evidence": [cd.GOAL]}
        rows, _, problems = with_groups(edit)
        self.assertTrue(any("wine-competition: depth.retired needs a reason" in p for p in problems))
        self.assertEqual(next(r for r in rows if r["id"] == "wine-competition")["status"], cd.RETIRED)

    def test_a_group_outside_the_goal_areas_and_an_unmapped_category_are_refused(self):
        def edit(groups):
            rec = copy.deepcopy(groups["maintie"][1])
            rec["categories"] = ["telepathy"]
            groups["new-group"] = (groups["maintie"][0], rec)
        _, _, problems = with_groups(edit)
        self.assertTrue(any("new-group: acquired but in no area" in p for p in problems))
        self.assertTrue(any("category 'telepathy' has no CATEGORY_FIT" in p for p in problems))

    def test_keyless_groups_rank_after_groups_that_may_have_a_key(self):
        rows, _, _ = cd.build()
        order = [r["key"]["status"] in cd.KEY_BLOCKED for r in cd.ranked(rows)]
        self.assertEqual(order, sorted(order))

    def test_licence_status(self):
        self.assertEqual(cd.licence_status("CC BY 4.0"), "open licence stated")
        self.assertEqual(cd.licence_status("Dataset-specific terms unresolved"), "terms unresolved")
        self.assertEqual(cd.licence_status("Public regulatory record; local originals only"),
                         "public record, rights retained, local only")


if __name__ == "__main__":
    unittest.main(verbosity=1)
