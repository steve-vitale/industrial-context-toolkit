"""The corpus depth register: docs/CORPUS_DEPTH.md is current, every acquired group has an area and a derived status,
the acquisition registries stay pinned, the feeding rule finds real matrix cells and skips agent-keyed ones, and a
status can never be typed in. Stdlib only."""
import copy
import hashlib
import subprocess
import tempfile
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
        if not n:
            self.assertIn("Increment 1 is done: 49 of 49", text)
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
        side = cd.load_sidecar()
        undisposed = copy.deepcopy(side)
        undisposed["groups"]["uci-secom"].pop("deferred")
        for status, expected in (("needs data", cd.UNPLANNED), ("fail", cd.FEEDS)):
            matrix["cells"] = [c for c in matrix["cells"] if c["input"] != "x-input"]
            matrix["cells"].append({"row": 6, "input": "x-input", "status": status})
            with patch.object(cd, "read_json", fake), patch.object(cd.corpus_matrix, "stale_cells", lambda *a: []), \
                    patch.object(cd, "load_sidecar", lambda root=cd.ROOT: undisposed):
                rows, _, _ = cd.build()
            self.assertEqual(row(rows, "uci-secom")["status"], expected, status)
        self.assertIn("historian-csv", row(rows, "uci-secom")["features"])
        # A deferred or retired group that starts feeding a scored cell is a broken rule, not a silent change.
        retired = copy.deepcopy(undisposed)
        retired["groups"]["uci-secom"]["retired"] = {"kind": "no area", "reason": "x",
                                                     "evidence": ["data/public_sources_20261107_round2.json#uci-secom"]}
        for sidecar, expected in ((side, "uci-secom: deferred but feeds 1 scored cells"),
                                  (retired, "uci-secom: retired but still feeds 1 scored cells")):
            with patch.object(cd, "read_json", fake), patch.object(cd.corpus_matrix, "stale_cells", lambda *a: []), \
                    patch.object(cd, "load_sidecar", lambda root=cd.ROOT, sc=sidecar: sc):
                _, _, problems = cd.build()
            self.assertTrue(any(p.startswith(expected) for p in problems), expected)

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
            s["groups"]["maintie"].pop("deferred", None)
            s["groups"]["maintie"]["plan"] = {"key": "gold annotations", "task": "x",
                                              "evidence": [cd.GOAL + "#MaintIE"], "names": ["MaintIE"]}

        def bad_anchor(s):
            s["groups"]["maintie"].pop("deferred", None)
            s["groups"]["maintie"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t", "names": ["MaintIE"],
                                              "evidence": [cd.GOAL + "#a sentence that is not there"]}

        def untracked(s):
            s["groups"]["maintie"].pop("deferred", None)
            s["groups"]["maintie"]["plan"] = {"date": "2026-11-10", "key": "k", "task": "t",
                                              "evidence": ["docs/NO_SUCH_PLAN.md#x"]}

        def unnamed(s):
            s["groups"]["maintie"].pop("deferred", None)
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
            s["groups"]["maintie"].pop("deferred", None)
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

    def test_every_key_is_verified_from_a_pinned_or_tracked_file(self):
        self.assertTrue(all(r["key"]["status"] in cd.KEY_STATUSES and r["key"].get("verified") for r in self.rows))

        def unverified(s):
            del s["groups"]["uci-secom"]["key"]["verified"]

        def old_status(s):
            s["groups"]["uci-secom"]["key"]["status"] = "acquisition record says labels exist, unopened"

        def unpinned(s):
            s["groups"]["uci-secom"]["key"]["verified"]["file"] = "secom_from_memory.csv"

        def member_of_pinned_archive(s):
            s["groups"]["uci-secom"]["key"]["verified"]["file"] = "original.zip!secom.names"

        def long_example(s):
            s["groups"]["uci-secom"]["key"]["verified"]["example"] = "x" * (cd.EXAMPLE_MAX + 1)

        def two_lines(s):
            s["groups"]["uci-secom"]["key"]["verified"]["example"] = "row 1\nrow 2"

        def no_count(s):
            s["groups"]["uci-secom"]["key"]["verified"]["count"] = ""

        def future(s):
            s["groups"]["uci-secom"]["key"]["verified"]["date"] = "2999-01-01"

        def someone_elses_tracked_file(s):
            s["groups"]["uci-secom"]["key"]["verified"]["file"] = "data/attempts.json"

        def bad_check(s):
            s["groups"]["uci-secom"]["key"]["verified"]["checks"] = [{"reader": "guess", "path": "original.zip",
                                                                      "expect": 1}]
        for edit, expected in ((unverified, "uci-secom: key status needs a 'verified' record"),
                               (old_status, "uci-secom: key status 'acquisition record says labels exist"),
                               (unpinned, "uci-secom: verified file 'secom_from_memory.csv' is neither"),
                               (long_example, "uci-secom: verified example must be one line"),
                               (two_lines, "uci-secom: verified example must be one line"),
                               (no_count, "uci-secom: verified record has no count"),
                               (future, "uci-secom: verified date '2999-01-01' is not a past ISO date"),
                               (someone_elses_tracked_file, "uci-secom: verified file 'data/attempts.json' is neither"),
                               (bad_check, "uci-secom: verified check 0 needs a known reader")):
            _, _, problems = with_sidecar(edit)
            self.assertTrue(any(p.startswith(expected) for p in problems), (edit.__name__, problems))
        _, _, problems = with_sidecar(member_of_pinned_archive)
        self.assertEqual(problems, [])

    def test_a_plan_needs_a_verified_key_a_real_feature_and_a_split_made_first(self):
        self.assertTrue(all(r["plan"]["feature"] and r["key"]["status"] == cd.KEY
                            for r in self.rows if r["status"] == cd.PLANNED))

        def not_a_task_key(s):
            s["groups"]["tina-mining"]["key"]["status"] = cd.NOT_A_TASK_KEY

        def no_feature(s):
            s["groups"]["tina-mining"]["plan"]["feature"] = "telepathy"

        def no_split(s):
            del s["groups"]["tina-mining"]["plan"]["split"]

        def overlap(s):
            sp = s["groups"]["tina-mining"]["plan"]["split"]
            sp["held_out"] = sp["held_out"] + sp["development"]

        def nothing_held_out(s):
            s["groups"]["tina-mining"]["plan"]["split"]["held_out"] = []

        def no_independence(s):
            del s["groups"]["tina-mining"]["key"]["independence"]

        def no_exposure(s):
            s["groups"]["tina-mining"]["plan"]["exposure"] = " "

        def split_after_plan(s):
            s["groups"]["tina-mining"]["plan"]["split"]["decided"] = "2026-11-13"
            s["groups"]["tina-mining"]["plan"]["date"] = "2026-11-12"
        for edit, expected in ((not_a_task_key, "tina-mining: plan needs key status 'verified key'"),
                               (no_feature, "tina-mining: plan feature 'telepathy' is not a feature"),
                               (no_split, "tina-mining: plan needs a split"),
                               (overlap, "tina-mining: plan split puts"),
                               (nothing_held_out, "tina-mining: plan split needs a development list and a non-empty"),
                               (split_after_plan, "tina-mining: plan split needs a past ISO 'decided' date"),
                               (no_independence, "tina-mining: plan needs key independence"),
                               (no_exposure, "tina-mining: plan needs an exposure statement")):
            rows, _, problems = with_sidecar(edit)
            self.assertTrue(any(p.startswith(expected) for p in problems), (edit.__name__, problems))
            self.assertEqual(row(rows, "tina-mining")["status"], cd.UNPLANNED, edit.__name__)

    def test_a_retirement_names_a_known_kind(self):
        self.assertTrue(all(r["retired"]["kind"] in cd.RETIRE_KINDS for r in self.rows if r["status"] == cd.RETIRED))

        def edit(s):
            s["groups"]["wine-competition"]["retired"]["kind"] = "boring"

        def no_toolkit_task(s):
            s["groups"]["wine-competition"]["retired"]["kind"] = "no toolkit task"

        def keyed_but_no_usable_key(s):
            g = s["groups"]["uci-secom"]
            g["retired"] = {"kind": "no usable key", "reason": "x", "evidence": g.pop("deferred")["evidence"]}

        def retired_task_key(s):
            g = s["groups"]["tina-mining"]
            g["retired"] = {"kind": "no area", "reason": "x", "evidence": g.pop("plan")["evidence"]}
        for e, expected in ((edit, "wine-competition: retirement kind 'boring' not one of"),
                            (no_toolkit_task, "(a verified key no feature consumes is deferred, not retired)"),
                            (keyed_but_no_usable_key, "uci-secom: retired as 'no usable key' but its key status"),
                            (retired_task_key, "tina-mining: retired with a 'verified key'")):
            _, _, problems = with_sidecar(e)
            self.assertTrue(any(expected in p for p in problems), (e.__name__, problems))

    def test_a_deferral_needs_a_checkable_key_a_new_capability_and_the_area(self):
        deferred = [r for r in self.rows if r["status"] == cd.DEFERRED]
        self.assertEqual(len(deferred), 12)
        self.assertTrue({"maintie", "uci-secom", "nasa-cmapss"} <= {r["id"] for r in deferred})
        text = cd.page(self.rows, self.earlier)
        self.assertIn("### Deferred: a verified key waits for a feature: 12", text)
        self.assertIn("work-order-text-reader", text)

        def wrong_status(s):
            s["groups"]["maintie"]["key"]["status"] = cd.KEY

        def existing_feature(s):
            s["groups"]["maintie"]["deferred"]["feature"]["id"] = "maintenance-history"

        def no_description(s):
            s["groups"]["maintie"]["deferred"]["feature"]["description"] = ""

        def wrong_area(s):
            s["groups"]["maintie"]["deferred"]["area"] = "CAD"

        def two_dispositions(s):
            s["groups"]["maintie"]["retired"] = {"kind": "no area", "reason": "x",
                                                 "evidence": ["data/public_sources_20261107.json#maintie"]}
        for e, expected in ((wrong_status, "maintie: deferred needs key status"),
                            (existing_feature, "maintie: deferred feature id 'maintenance-history' must be a new"),
                            (no_description, "maintie: deferred feature needs a one-line description"),
                            (wrong_area, "maintie: deferred area 'CAD' is not the group's area"),
                            (two_dispositions, "maintie: more than one of a plan, a deferral and a retirement")):
            rows, _, problems = with_sidecar(e)
            self.assertTrue(any(p.startswith(expected) for p in problems), (e.__name__, problems))
            if e is not two_dispositions:
                self.assertEqual(row(rows, "maintie")["status"], cd.UNPLANNED, e.__name__)

    def test_check_and_strict_combine(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_depth.py"), "--check", "--strict"],
                           capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Reverify(unittest.TestCase):
    """--reverify recomputes a recorded count from pinned bytes, and refuses a wrong count, a changed file and a
    member that is not in the archive's listing."""

    def run_checks(self, checks, files, pinned=None):
        import io
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            pins = {}
            for name, data in files.items():
                (Path(tmp) / "g").mkdir(exist_ok=True)
                (Path(tmp) / "g" / name).write_bytes(data)
                pins[name] = {"sha256": hashlib.sha256((pinned or {}).get(name, data)).hexdigest()}
            real = cd.read_json
            with patch.object(cd, "read_json", lambda rel, root=cd.ROOT: {"g": pins} if rel == cd.PINS
                              else real(rel, root)):
                return cd.reverify([{"id": "g", "key": {"verified": {"file": "a.zip!x.csv", "checks": checks}}}], tmp)

    def test_counts_members_and_pins(self):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("x.csv", "h,c\n1,a\n2,b\n3,a\n")
        files = {"a.zip": buf.getvalue(), "t.inp": b"[PIPES]\n;c\n1 2 3\n4 5 6\n[TANKS]\n9\n"}
        lines, bad = self.run_checks([{"reader": "csv-rows", "path": "a.zip!x.csv", "expect": 3},
                                      {"reader": "csv-count", "path": "a.zip!x.csv", "expect": 2, "column": "c",
                                       "value": "a"},
                                      {"reader": "inp-section", "path": "t.inp", "expect": 2, "section": "[PIPES]"}],
                                     files)
        self.assertEqual(bad, [])
        self.assertEqual(sum(x.startswith("ok") for x in lines), 4)  # three counts and the verified member
        _, bad = self.run_checks([{"reader": "csv-rows", "path": "a.zip!x.csv", "expect": 4}], files)
        self.assertTrue(any("recorded 4, recomputed 3" in b for b in bad))
        _, bad = self.run_checks([{"reader": "csv-rows", "path": "a.zip!y.csv", "expect": 3}], files)
        self.assertTrue(any("is not in the listing of a.zip" in b for b in bad))
        _, bad = self.run_checks([{"reader": "csv-rows", "path": "a.zip!x.csv", "expect": 3}], files,
                                 pinned={"a.zip": b"other bytes"})
        self.assertTrue(any("does not match its pinned sha256" in b for b in bad))

    def test_parquet_footer_row_count(self):
        # FileMetaData {1: version i32 = 1, 2: schema list<struct> of one {4: name "x"}, 3: num_rows i64 = 5}
        meta = bytes([0x15, 0x02, 0x19, 0x1C, 0x48, 0x01, ord("x"), 0x00, 0x16, 0x0A, 0x00])
        data = b"PAR1" + meta + len(meta).to_bytes(4, "little") + b"PAR1"
        self.assertEqual(cd.READERS["parquet-rows"](data, {}), 5)


class LicenceStatus(unittest.TestCase):

    def test_licence_status(self):
        self.assertEqual(cd.licence_status("CC BY 4.0"), "open licence stated")
        self.assertEqual(cd.licence_status("Dataset-specific terms unresolved"), "terms unresolved")
        self.assertEqual(cd.licence_status("Public regulatory record; local originals only"),
                         "public record, rights retained, local only")


if __name__ == "__main__":
    unittest.main(verbosity=1)
