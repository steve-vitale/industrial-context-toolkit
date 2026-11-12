"""The corpus depth register: docs/CORPUS_DEPTH.md is current, every acquired group has an area and a derived status,
the acquisition registries stay pinned, the feeding rule finds real matrix cells and skips agent-keyed ones, and a
status can never be typed in. Stdlib only."""
import copy
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import corpus_depth as cd  # noqa: E402


def with_sidecar(edit):
    """build() with the real dispositions passed through edit(sidecar)."""
    real = cd.load_sidecar()

    def fake(root=cd.ROOT):
        side = copy.deepcopy(real)
        edit(side)
        return side
    with patch.object(cd, "load_sidecar", fake):
        return cd.build()


def with_groups(edit):
    """build() with the real acquisition records passed through edit(groups)."""
    real = cd.load_groups

    def fake(root=cd.ROOT):
        groups, problems = real(root)
        groups = copy.deepcopy(groups)
        edit(groups)
        return groups, problems
    with patch.object(cd, "load_groups", fake):
        return cd.build()


def row(rows, sid):
    return next(r for r in rows if r["id"] == sid)


class Register(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.earlier, cls.problems = cd.build()

    def test_doc_is_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_depth.py"), "--check"],
                           capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_group_has_an_area_and_one_status(self):
        self.assertEqual(self.problems, [])
        self.assertEqual(len(self.rows), 49, "docs/DEPTH_GOAL.md counts 49 acquired groups")
        self.assertTrue(all(r["area"] != "?" for r in self.rows))
        self.assertTrue(all(r["status"] in cd.STATUS_ORDER for r in self.rows))

    def test_unplanned_is_loud_and_first_and_strict_fails(self):
        text = cd.page(self.rows, self.earlier)
        n = sum(r["status"] == cd.UNPLANNED for r in self.rows)
        self.assertLess(text.index(f"## UNPLANNED: {n} of {len(self.rows)}"), text.index("## The register"))
        self.assertLess(text.index("## Next to wire"), text.index("## The register"))
        if n:
            self.assertIn("Increment 1 is not done", text)
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_depth.py"), "--strict"],
                               capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 1, "--strict must fail while any group is UNPLANNED")

    def test_a_changed_registry_fails_its_pin(self):
        def edit(side):
            rel = sorted(side["registries"])[0]
            side["registries"][rel] = "0" * 64
        _, _, problems = with_sidecar(edit)
        self.assertTrue(any("changed since data/corpus_depth.json pinned it" in p for p in problems))

    def test_feeding_rule_finds_real_cells_and_skips_agent_keys(self):
        # Positive control: sources that do feed the matrix are found by the rule the 49 groups go through.
        by_id = {e["id"]: e for e in self.earlier}
        self.assertTrue(any(c["row"] == 6 for c in by_id["hai"]["scored"]))
        self.assertIn("historian-csv", by_id["skab"]["features"])
        # wikimedia-pid's scored cells are all on agent-made keys, so none counts.
        self.assertTrue(any(c["status"] == "pass" for c in by_id["wikimedia-pid"]["cells"]))
        self.assertEqual(by_id["wikimedia-pid"]["scored"], [])

    def test_a_group_feeds_only_through_a_scored_cell(self):
        corpus, matrix = cd.read_json(cd.CORPUS), cd.read_json(cd.MATRIX)
        corpus["inputs"].append({"id": "x-input", "family": "uci-secom", "kind": "historian",
                                 "fetch": "python examples/public-data/fetch_sources.py uci-secom"})
        real = cd.read_json

        def fake(rel, root=cd.ROOT):
            return {cd.CORPUS: corpus, cd.MATRIX: matrix}.get(rel) or real(rel, root)
        for status, expected in (("needs data", cd.UNPLANNED), ("fail", cd.FEEDS)):
            matrix["cells"] = [c for c in matrix["cells"] if c["input"] != "x-input"]
            matrix["cells"].append({"row": 6, "input": "x-input", "status": status})
            with patch.object(cd, "read_json", fake), patch.object(cd.corpus_matrix, "stale_cells", lambda *a: []):
                rows, _, _ = cd.build()
            self.assertEqual(row(rows, "uci-secom")["status"], expected, status)
        self.assertIn("historian-csv", row(rows, "uci-secom")["features"])

    def test_a_stale_matrix_fails(self):
        with patch.object(cd.corpus_matrix, "stale_cells", lambda *a: ["row 6 x skab: input no longer registered"]):
            _, _, problems = cd.build()
        self.assertTrue(any("cells are stale" in p for p in problems))

    def test_benchmarks_follow_case_paths_not_substrings(self):
        with patch.object(cd, "suite_paths", lambda rel, root=cd.ROOT: {"data/external/maintie/x.json"}):
            self.assertTrue(cd.benchmark_suites("maintie"))
            self.assertEqual(cd.benchmark_suites("maint"), [])
        # The real suites name no acquired group's files.
        self.assertTrue(all(not r["suites"] for r in self.rows))

    def test_status_cannot_be_typed_in(self):
        def side(s):
            s["groups"]["maintie"]["status"] = "feeds a scored task"

        def record(groups):
            groups["uci-ai4i"][1]["feeds"] = True
        _, _, problems = with_sidecar(side)
        self.assertTrue(any("maintie: status is derived" in p for p in problems))
        _, _, problems = with_groups(record)
        self.assertTrue(any("uci-ai4i: registry field 'feeds'" in p for p in problems))

    def test_unbacked_evaluation_claim_is_refused(self):
        def edit(groups):
            groups["uci-ai4i"][1]["evidence_role"] = "evaluated"
        _, _, problems = with_groups(edit)
        self.assertTrue(any("uci-ai4i: evidence_role 'evaluated' claims evaluation" in p for p in problems))

    def test_key_evidence_must_be_the_groups_own_record(self):
        def edit(s):
            s["groups"]["maintie"]["key"]["evidence"] = ["data/public_sources_20261107.json#uci-ai4i"]
        _, _, problems = with_sidecar(edit)
        self.assertTrue(any("maintie: key availability must cite its acquisition record" in p for p in problems))

    def test_a_plan_needs_date_quoted_tracked_evidence_that_names_the_group(self):
        def undated(s):
            s["groups"]["maintie"]["plan"] = {"key": "gold annotations", "task": "x",
                                              "evidence": [cd.GOAL + "#MaintIE"], "names": ["MaintIE"]}

        def bad_anchor(s):
            s["groups"]["maintie"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t", "names": ["MaintIE"],
                                              "evidence": [cd.GOAL + "#a sentence that is not there"]}

        def untracked(s):
            s["groups"]["maintie"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t",
                                              "evidence": ["docs/NO_SUCH_PLAN.md#x"]}

        def unnamed(s):
            s["groups"]["maintie"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t",
                                              "evidence": ["docs/GOAL_ROUND6.md#product-path rule"]}
        rows, _, problems = with_sidecar(undated)
        self.assertTrue(any("maintie: plan needs" in p for p in problems))
        self.assertEqual(row(rows, "maintie")["status"], cd.UNPLANNED)
        _, _, problems = with_sidecar(bad_anchor)
        self.assertTrue(any("is not in docs/DEPTH_GOAL.md" in p for p in problems))
        _, _, problems = with_sidecar(untracked)
        self.assertTrue(any("NO_SUCH_PLAN.md is not a tracked file" in p for p in problems))
        _, _, problems = with_sidecar(unnamed)
        self.assertTrue(any("GOAL_ROUND6.md never names the group" in p for p in problems))

    def test_a_plan_name_must_come_from_the_record(self):
        def edit(s):
            s["groups"]["maintie"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t", "names": ["Pahala"],
                                              "evidence": ["docs/GOAL_ROUND6.md#Pahala P-401 and P-501"]}
        _, _, problems = with_sidecar(edit)
        self.assertTrue(any("maintie: plan name 'Pahala' is not in the acquisition record" in p for p in problems))

    def test_retirement_needs_a_reason_and_wins_over_unplanned(self):
        def edit(s):
            s["groups"]["wine-competition"]["retired"] = {"reason": "", "evidence": [cd.GOAL + "#wine-competition"]}
        rows, _, problems = with_sidecar(edit)
        self.assertTrue(any("wine-competition: retired needs a reason" in p for p in problems))
        self.assertEqual(row(rows, "wine-competition")["status"], cd.RETIRED)

    def test_a_group_outside_the_goal_areas_and_an_unmapped_category_are_refused(self):
        def edit(groups):
            rec = copy.deepcopy(groups["maintie"][1])
            rec["categories"] = ["telepathy"]
            groups["new-group"] = (groups["maintie"][0], rec)
        _, _, problems = with_groups(edit)
        self.assertTrue(any("new-group: acquired but in no area" in p for p in problems))
        self.assertTrue(any("new-group: no entry in data/corpus_depth.json" in p for p in problems))
        self.assertTrue(any("category 'telepathy' has no CATEGORY_FIT" in p for p in problems))

    def test_keyless_groups_rank_after_groups_that_may_have_a_key(self):
        order = [r["key"]["status"] in cd.KEY_BLOCKED for r in cd.ranked(self.rows)]
        self.assertEqual(order, sorted(order))

    def test_planned_open_item_shows_in_the_status(self):
        amps = row(self.rows, "nyc-amps-2024w01")
        self.assertEqual(amps["status"], cd.PLANNED)
        self.assertIn("reserved cohort not acquired", cd.status_text(amps))

    def test_licence_status(self):
        self.assertEqual(cd.licence_status("CC BY 4.0"), "open licence stated")
        self.assertEqual(cd.licence_status("Dataset-specific terms unresolved"), "terms unresolved")
        self.assertEqual(cd.licence_status("Public regulatory record; local originals only"),
                         "public record, rights retained, local only")


if __name__ == "__main__":
    unittest.main(verbosity=1)
