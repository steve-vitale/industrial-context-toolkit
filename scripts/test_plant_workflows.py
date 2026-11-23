"""Tests for the plant-workflow pieces of scripts/one_map.py and scripts/map_changes.py: the work order closeout
check, field verification rulings, the change report between two map builds, the affected-records report and its
closeout, and the change flags. Built on copies of the fictional pasteurizer example. Stdlib only.

Usage:  python scripts/test_plant_workflows.py
"""
import contextlib
import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_changes as mc  # noqa: E402
import one_map as om  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAST = ROOT / "examples" / "one-map" / "inputs" / "pasteurizer"
FDV = "S1/P1/PAST1/FDV-2210"
PRIVATE_NAMES = ("tolipegnahc"[::-1], "kramatled"[::-1])  # product and company names kept out of this repo


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def write_csv(path, header, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(buf.getvalue(), encoding="utf-8", newline="\n")


WO_HEADER = ["work_order", "tag", "plant", "unit", "work_type", "opened_on", "closed_on", "description",
             "installed_manufacturer", "installed_model", "installed_serial_number", "installed_size"]


class Site:
    """A temporary copy of the pasteurizer inputs (which hold a valve datasheet, installed-equipment columns on the
    maintenance equipment export and a work order history) with the given work orders and FDV-2210 export row."""

    def __init__(self, tmp, work_orders, export_fdv=("Alfa Valve", "SRC-2", "AV-51007")):
        self.dir = Path(tmp) / "in"
        shutil.copytree(PAST, self.dir)
        p = self.dir / "lists" / "maintenance_equipment.csv"
        rows = list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))))
        for r in rows:
            if r["tag"] == "FDV-2210":
                r["manufacturer"], r["model"], r["serial_number"] = export_fdv
        write_csv(p, list(rows[0]), [list(r.values()) for r in rows])
        wo = list(csv.DictReader(io.StringIO((self.dir / "records" / "work_orders.csv").read_text(encoding="utf-8"))))
        header = list(wo[0])
        write_csv(self.dir / "records" / "work_orders.csv", header,
                  [[dict(zip(WO_HEADER, r)).get(k, "") for k in header] for r in work_orders])

    def build(self, out, **kw):
        g, _, rows, _ = quiet(om.build, self.dir / "site.json", Path(out), full=True, **kw)
        return g, rows


REPLACED = ["WO-60311", "FDV-2210", "P1", "PAST1", "modification", "2026-10-20", "2026-10-22",
            "Replace divert valve under MOC-0412", "Alfa Valve", "SRC-3", "AV-88412", "DN65"]


def conflicts_of(g):
    return [n["conflict"] for n in g["nodes"] if n["kind"] == "conflict"]


class WorkOrderCloseout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_installed_values_against_the_export_and_the_datasheet(self):
        site = Site(self.tmp.name, [
            REPLACED,
            ["WO-60312", "FDV-2210", "P1", "PAST1", "corrective", "2026-10-25", "", "Still open", "Other", "X-1",
             "S-1", "DN80"],  # not closed: not compared
            ["WO-60313", "P-101", "P1", "PAST1", "corrective", "2026-08-04", "2026-08-04", "Seal", "", "", "", ""],
            ["WO-60314", "XV-9999", "P1", "PAST1", "corrective", "2026-09-01", "2026-09-02", "Replaced", "Acme",
             "Q-1", "", ""],
        ])
        g, rows = site.build(Path(self.tmp.name) / "out")
        wo = {c["attribute"]: c for c in conflicts_of(g) if c["subject"] == FDV
              and c["source_a"]["source"]["document"] == "WO-HISTORY"}
        self.assertEqual(sorted(wo), ["model", "serial_number"], "manufacturer agrees; size is a datasheet fact")
        for c in wo.values():
            self.assertEqual(c["type"], "value_disagreement")
            self.assertEqual(c["record_owner"], "Maintenance")
            self.assertIn("work order WO-60311 (closed 2026-10-22)", c["what"])
        self.assertEqual((wo["model"]["source_a"]["says"], wo["model"]["source_b"]["says"]), ("SRC-3", "SRC-2"))
        like = [r for r in rows if r["kind"] == om.LIKE_FOR_LIKE]
        self.assertEqual(len(like), 1)
        self.assertEqual((like[0]["item"], like[0]["owner"]), (FDV, "Engineering"))
        for words in ("size DN65 installed", "datasheet VALVE-DATASHEETS (row 2) says DN50", "management of change",
                      "not a decision"):
            self.assertIn(words, like[0]["why"])
        notes = [r for r in rows if r["kind"] == om.WO_NOTE]
        self.assertEqual(len(notes), 1, [r["why"] for r in notes])
        self.assertIn("XV-9999", notes[0]["why"])
        self.assertFalse([c for c in conflicts_of(g) if "WO-60312" in c["what"] or "DN80" in json.dumps(c)])
        self.assertEqual(om.problems(g), [])

    def test_matching_closeout_raises_nothing_and_case_or_spacing_is_not_a_difference(self):
        site = Site(self.tmp.name, [REPLACED[:8] + ["alfa  valve", "src-3", "AV-88412", "dn65"]],
                    export_fdv=("Alfa Valve", "SRC-3", "AV-88412"))
        (site.dir / "lists" / "valve_datasheets.csv").write_text(
            "tag,plant,unit,size,body_material\nFDV-2210,P1,PAST1,DN65,316L\n", encoding="utf-8")
        g, rows = site.build(Path(self.tmp.name) / "out")
        self.assertFalse([c for c in conflicts_of(g) if c["source_a"]["source"]["document"] == "WO-HISTORY"])
        self.assertFalse([r for r in rows if r["kind"] in (om.LIKE_FOR_LIKE, om.WO_NOTE)])

    def test_only_the_latest_closeout_per_item_and_value_is_compared(self):
        older = ["WO-50001", "FDV-2210", "P1", "PAST1", "corrective", "2024-03-01", "2024-03-02", "Earlier swap",
                 "Alfa Valve", "SRC-1", "AV-10001", "DN40"]
        site = Site(self.tmp.name, [older, REPLACED[:8] + ["", "", "", "DN50"]],
                    export_fdv=("Alfa Valve", "SRC-2", "AV-51007"))
        g, rows = site.build(Path(self.tmp.name) / "out")
        # model and serial: only the 2024 work order records them, so it is the latest for those values
        wo = {c["attribute"]: c["source_a"]["says"] for c in conflicts_of(g) if c["subject"] == FDV
              and c["source_a"]["source"]["document"] == "WO-HISTORY"}
        self.assertEqual(wo, {"model": "SRC-1", "serial_number": "AV-10001"})
        # size: the 2026 closeout (DN50, as the datasheet) supersedes the 2024 DN40
        self.assertFalse([r for r in rows if r["kind"] == om.LIKE_FOR_LIKE])

    def test_installed_value_no_record_holds_is_a_note(self):
        site = Site(self.tmp.name, [["WO-1", "P-102", "P1", "PAST1", "corrective", "2026-10-01", "2026-10-02", "x",
                                     "Pumpco", "", "", ""]])
        _, rows = site.build(Path(self.tmp.name) / "out")
        notes = [r for r in rows if r["kind"] == om.WO_NOTE]
        self.assertEqual(len(notes), 1)
        self.assertIn("no maintenance equipment export or instrument index row for it holds manufacturer",
                      notes[0]["why"])


RULING_HEADER = ["ruling_id", "concerns", "attribute", "ruling", "chosen_source", "chosen_value", "reason", "by",
                 "on", "authority", "evidence"]


class FieldVerificationRulings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Site(self.tmp.name, [REPLACED])
        self.out = Path(self.tmp.name) / "out"
        self.g, _ = self.site.build(self.out)
        self.serial = next(c for c in conflicts_of(self.g) if c["subject"] == FDV and c["attribute"] == "serial_number")

    def tearDown(self):
        self.tmp.cleanup()

    def rulings(self, *rows):
        p = Path(self.tmp.name) / "rulings.csv"
        write_csv(p, RULING_HEADER, rows)
        return p

    def test_walkdown_ruling_settles_the_conflict_and_asks_the_record_owner_to_update(self):
        walk = ["R-0101", FDV, "serial_number", "accept_value", "", "AV-88412",
                "Walkdown: the nameplate on the installed body reads AV-88412", "Maintenance planner", "2026-11-03",
                "field", "photo walkdown-2026-11-03/FDV-2210-nameplate.jpg"]
        g, rows = self.site.build(self.out, decisions=[str(self.rulings(walk))])
        c = next(n["conflict"] for n in g["nodes"] if n["kind"] == "conflict" and n["conflict"]["id"] == self.serial["id"])
        self.assertEqual(c["status"], "resolved")
        h = c["history"][-1]
        self.assertEqual((h["authority"], h["ruling_id"], h["chosen_value"], h["by"], h["on"]),
                         ("field", "R-0101", "AV-88412", "Maintenance planner", "2026-11-03"))
        self.assertIn("nameplate", h["evidence"])
        upd = [r for r in rows if r["kind"] == om.RULED]
        self.assertEqual(len(upd), 1)
        self.assertEqual(upd[0]["owner"], "Maintenance")
        for words in ("ruled AV-88412 on 2026-11-03 (field: photo walkdown-2026-11-03", "CMMS-2026-10",
                      "still says AV-51007: update it"):
            self.assertIn(words, upd[0]["why"])
        self.assertFalse([r for r in rows if r["item"].endswith(self.serial["id"]) and r["tier"] == "red"])
        md = (self.out / "conflicts.md").read_text(encoding="utf-8")
        self.assertIn("## Decision history", md)
        self.assertIn("2026-11-03 Maintenance planner: resolved (ruling_id R-0101; ruling accept_value; authority field",
                      md)
        # the same file again adds no second history line; the earlier state carries the ruling forward
        g2, _ = self.site.build(self.out, decisions=[str(self.rulings(walk))])
        c2 = next(n["conflict"] for n in g2["nodes"] if n["kind"] == "conflict" and n["conflict"]["id"] == c["id"])
        self.assertEqual(len(c2["history"]), 1)

    def test_conflict_id_form_decisions_csv_and_refusals(self):
        cid = f"S1/CONFLICT/{self.serial['id']}"
        ok = ["R-1", cid, "", "defer", "", "", "Wait for the walkdown", "Maintenance planner", "2026-11-01", "", ""]
        g, _ = self.site.build(self.out, decisions=[str(self.rulings(ok))])
        c = next(n["conflict"] for n in g["nodes"] if n["kind"] == "conflict" and n["conflict"]["id"] == self.serial["id"])
        self.assertEqual((c["status"], c["history"][-1]["authority"]), ("disputed", "person"))
        bad = (
            (["R-2", FDV, "serial_number", "accept_value", "", "AV-88412", "seen", "x", "2026-11-03", "field", ""],
             "needs evidence"),
            (["R-3", FDV, "", "accept_value", "", "AV-88412", "seen", "x", "2026-11-03", "", ""], "names the attribute"),
            (["R-4", FDV, "flange_rating", "accept_value", "", "PN16", "seen", "x", "2026-11-03", "", ""],
             "no detected conflict"),
            (["R-5", cid, "", "overrule", "", "", "seen", "x", "2026-11-03", "", ""], "ruling must be one of"),
            (["R-6", cid, "", "defer", "", "", "seen", "x", "3 Nov", "", ""], "YYYY-MM-DD"),
            (["R-7", cid, "", "defer", "", "", "seen", "x", "2026-11-03", "drone", ""], "authority must be one of"),
        )
        for row, words in bad:
            with self.assertRaises(om.InputError) as cm:
                self.site.build(self.out, decisions=[str(self.rulings(row))])
            self.assertIn(words, str(cm.exception), row)


MOC_EXPECTED = ROOT / "examples" / "one-map" / "expected" / "pasteurizer-moc"
MOC_FILES = ("release/changes.md", "release/changes.json", "moc-open/affected.md", "moc-open/affected.json",
             "moc-pack/changes.md", "moc-pack/changes.json", "moc-close/closeout.md", "moc-close/closeout.json",
             "close/conflicts.md", "close/queues/review_queue.csv")


def write_moc_example(out):
    """The MOC-0412 walk-through of examples/one-map/README.md, as its commands would write it under out/moc:
    three builds, then the release report, the MOC-open list, the before/after pack and the closeout check."""
    out = Path(out)
    tags = ["FDV-2210", "TT-2208"]
    lab = {k: f"out/moc/{k}/graph.json" for k in ("open", "revd", "close")}
    g = {}
    for name, key, kw in (("site.json", "open", {}), ("site-revD.json", "revd", {}),
                          ("site-moc-close.json", "close", {"decisions": [str(PAST / "walkdown_rulings.csv")]})):
        g[key] = quiet(om.build, PAST / name, out / key, full=True, **kw)[0]
    rep = mc.changes(g["open"], g["revd"], labels=(lab["open"], lab["revd"]))
    mc.write(out / "release", "changes", rep, mc.changes_md(rep))
    rep = mc.affected(g["open"], tags, label=lab["open"])
    mc.write(out / "moc-open", "affected", rep, mc.affected_md(rep))
    rep = mc.changes(g["open"], g["close"], tags, labels=(lab["open"], lab["close"]))
    mc.write(out / "moc-pack", "changes", rep, mc.changes_md(rep))
    rep = mc.closeout(g["open"], g["close"], tags, labels=(lab["open"], lab["close"]))
    mc.write(out / "moc-close", "closeout", rep, mc.closeout_md(rep))
    return g


class MocExample(unittest.TestCase):
    def test_expected_outputs_regenerate_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as t:
            write_moc_example(t)
            self.assertEqual(sorted(p.relative_to(MOC_EXPECTED).as_posix() for p in MOC_EXPECTED.rglob("*")
                                    if p.is_file()), sorted(MOC_FILES))
            for rel in MOC_FILES:
                self.assertEqual((Path(t) / rel).read_bytes().replace(b"\r\n", b"\n"),
                                 (MOC_EXPECTED / rel).read_bytes().replace(b"\r\n", b"\n"), rel)

    def test_public_files_name_no_private_product(self):
        for p in sorted(MOC_EXPECTED.rglob("*.*")) + sorted(PAST.rglob("*.*")) + [Path(mc.__file__)]:
            text = p.read_text(encoding="utf-8").lower()
            for word in PRIVATE_NAMES:
                self.assertNotIn(word, text, p.name)


class RunningTheMapGuide(unittest.TestCase):
    """docs/RUNNING_THE_MAP.md: every routine has a row, the commands it names exist, nothing private is named."""

    def test_routines_commands_and_links(self):
        doc = (ROOT / "docs" / "RUNNING_THE_MAP.md").read_text(encoding="utf-8")
        for routine in ("P&ID revision", "MOC open", "MOC close", "Work order closeout", "PM and calibration",
                        "Turnaround", "Walkdown / field verification", "HACCP verification and reassessment",
                        "CAPA", "PHA / HAZOP revalidation", "Incident investigation", "Procurement and receiving",
                        "New or revised document", "Onboarding", "Audit preparation"):
            self.assertIn(f"| **{routine}", doc)
        for words in ("Two numbers to watch", "No per-owner time allowance has been measured",
                      "no notification is sent automatically", "rollout.scopes",
                      "limit_per_scope", "your company's existing systems or a governed service"):
            self.assertIn(words, doc)
        lowered = doc.lower()
        for word in PRIVATE_NAMES:
            self.assertNotIn(word, lowered)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            om.main(["--help"])
        for cmd in ("build", "changes", "affected", "ask"):
            self.assertIn(f"`{cmd}", doc)
            self.assertIn(cmd, buf.getvalue())
        for readme, link in ((ROOT / "README.md", "docs/RUNNING_THE_MAP.md"),
                             (ROOT / "docs" / "README.md", "(RUNNING_THE_MAP.md)")):
            self.assertIn(link, readme.read_text(encoding="utf-8"))
        anchor = "#the-pasteurizer-through-an-moc-pid-revision-moc-open-and-close-work-order-walkdown"
        self.assertIn(anchor, doc)
        self.assertIn("## The pasteurizer through an MOC: P&ID revision, MOC open and close, work order, walkdown",
                      (ROOT / "examples" / "one-map" / "README.md").read_text(encoding="utf-8"))
        for flag in (mc.FLAG_HACCP, mc.FLAG_PHA, mc.FLAG_CRIT):
            self.assertIn(flag, doc)


class MocBuilds:
    """The pasteurizer at MOC-0412 open (P&ID rev C), after P&ID rev D is released, and at close (records updated,
    work order WO-60311 closed, the walkdown ruling recorded). Built once per test class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.open, cls.revd, cls.close = (
            quiet(om.build, PAST / name, t / out, full=True, **kw)[0]
            for name, out, kw in (("site.json", "open", {}), ("site-revD.json", "revd", {}),
                                  ("site-moc-close.json", "close",
                                   {"decisions": [str(PAST / "walkdown_rulings.csv")]})))
        cls.dir = t

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class ChangeReport(MocBuilds, unittest.TestCase):
    def test_pid_revision_release_report(self):
        rep = mc.changes(self.open, self.revd)
        self.assertEqual([x["id"] for x in rep["items"]["added"]], ["S1/P1/PAST1/TT-2208"])
        fdv = next(x for x in rep["items"]["changed"] if x["id"] == FDV)
        self.assertEqual(fdv["changes"], [{"what": "on P&ID", "old": ["PAST1-01:D3"],
                                           "new": ["PAST1-01:D3 (size DN65 printed)"]}])
        self.assertEqual(sorted(f["flag"] for f in fdv["flags"]), [mc.FLAG_HACCP, mc.FLAG_CRIT])
        self.assertIn({"type": "measures", "from": "S1/P1/PAST1/TT-2208", "to": "S1/P1/PAST1/HT-100"},
                      rep["links"]["added"])
        doc = rep["documents"]["changed"]
        self.assertEqual([d["id"] for d in doc], ["S1/DOC/PID-P1-PAST1-01"])
        self.assertIn({"what": "revision", "old": "C", "new": "D"}, doc[0]["changes"])
        self.assertEqual(sorted(c["type"] for c in rep["conflicts"]["added"]), ["asset_presence", "superseded_basis"])
        self.assertEqual(rep["records"], {"added": [], "removed": [], "changed": []})
        md = mc.changes_md(rep)
        for words in ("| Items | 1 | 0 | 1 |", "FDV-2210 | changed | HACCP reassessment",
                      "S1/DOC/PID-P1-PAST1-01 | changed | Doc control | content changed; revision: C -> D"):
            self.assertIn(words, md)

    def test_same_build_has_no_changes_and_is_deterministic(self):
        rep = mc.changes(self.open, self.open)
        self.assertTrue(all(v == 0 for sec in rep["counts"].values() for v in sec.values()))
        self.assertIn("No changes.", mc.changes_md(rep))
        a = json.dumps(mc.changes(self.open, self.close, ["FDV-2210"]), sort_keys=True)
        self.assertEqual(a, json.dumps(mc.changes(self.open, self.close, ["FDV-2210"]), sort_keys=True))

    def test_moc_pack_filter_by_tags_and_scope(self):
        rep = mc.changes(self.open, self.close, ["FDV-2210", "TT-2208"])
        self.assertEqual(sorted(x["id"] for x in rep["items"]["changed"] + rep["items"]["added"]),
                         [FDV, "S1/P1/PAST1/TT-2208"])
        model = next(d for d in rep["items"]["changed"][0]["changes"] if d["what"] == "attribute model")
        self.assertEqual((model["old"], model["new"]), ("SRC-2 (CMMS-2026-10)", "SRC-3 (CMMS-2026-10)"))
        self.assertEqual([(r["record"], r["row"]) for r in rep["records"]["added"]], [("WO-HISTORY", "WO-60311")])
        self.assertEqual(sorted(d["id"] for d in rep["documents"]["changed"]),
                         ["S1/DOC/HACCP-PLAN-P1", "S1/DOC/PID-P1-PAST1-01"])
        self.assertNotIn("S1/P1/PAST1/P-101", json.dumps(rep), "other items stay out of a tag-filtered pack")
        cip = mc.changes(self.open, self.close, scopes=["S1/P1/CIP1"])
        self.assertTrue(all(sum(v.values()) == 0 for v in cip["counts"].values()), cip["counts"])
        new = mc.changes(self.open, self.close, ["XV-0001"])
        self.assertEqual(new["filter"]["not_on_either_map"], ["XV-0001"])
        with self.assertRaises(mc.ReportError):
            mc.changes(self.open, self.close, scopes=["S1/P9"])

    def test_cli_writes_markdown_and_json(self):
        g1, g2 = self.dir / "open" / "graph.json", self.dir / "revd" / "graph.json"
        out = self.dir / "cli"
        self.assertEqual(quiet(om.main, ["changes", str(g1), str(g2), "--out", str(out)]), 0)
        self.assertEqual(json.loads((out / "changes.json").read_text(encoding="utf-8"))["schema"], mc.CHANGES_SCHEMA)
        self.assertTrue((out / "changes.md").read_text(encoding="utf-8").startswith("# Changes:"))
        self.assertEqual(quiet(om.main, ["changes", str(g1), str(g2), "--scope", "S1/X"]), 2)
        self.assertEqual(quiet(om.main, ["affected", "--tags", "FDV-2210"]), 2, "needs --map or --closeout")


class AffectedRecords(MocBuilds, unittest.TestCase):
    def test_moc_open_list_by_owner(self):
        rep = mc.affected(self.open, ["FDV-2210", "TT-2208"])
        self.assertEqual(rep["selection"]["not_on_the_map"], ["TT-2208"])
        own = {o: {r["record"]: r for r in rows} for o, rows in rep["by_owner"].items()}
        self.assertEqual(sorted(own), ["Doc control", "Engineering", "I&C", "Maintenance", "Production", "Quality"])
        self.assertIn("rev C shows FDV-2210 at D3", own["Doc control"]["S1/DOC/PID-P1-PAST1-01"]["check"])
        self.assertIn("size", own["Engineering"]["VALVE-DATASHEETS"]["check"])
        self.assertIn("FDV-2210 is its output", own["I&C"]["LOOPS-PAST1"]["check"])
        self.assertEqual(set(own["Maintenance"]), {"CMMS-2026-10", "CRIT-P1", "rule R-CRITICAL-PM",
                                                   "flag: criticality review"})
        self.assertIn("mentions FDV-2210", own["Production"]["S1/DOC/SOP-PAST1-02"]["check"])
        haccp = own["Quality"]["S1/DOC/HACCP-PLAN-P1"]["check"]
        for words in ("based on PID-P1-PAST1-01 rev C", "mentions FDV-2210"):
            self.assertIn(words, haccp)
        self.assertIn("corrective_action names FDV-2210", own["Quality"]["HACCP-P1-01"]["check"])
        self.assertIn("flag: HACCP reassessment", own["Quality"])
        linked = {(x["link"], x["item"]) for x in rep["items"][0]["linked"]}
        self.assertEqual(linked, {("connects", "S1/P1/PAST1/HT-100"), ("connects", "S1/P1/PAST1/PHE-2201"),
                                  ("controls", "S1/P1/PAST1/TIC-2207"), ("signal_line", "S1/P1/PAST1/TIC-2207")})
        md = mc.affected_md(rep)
        for words in ("Not on the map yet: TT-2208", "### Engineering", "TIC-2207 controls FDV-2210"):
            self.assertIn(words, md)

    def test_open_conflicts_and_scope_selection(self):
        rep = mc.affected(self.revd, scopes=["S1/P1/PAST1"])
        rows = [r for rs in rep["by_owner"].values() for r in rs]
        self.assertTrue(any(r["entry"] == "conflict" and r["tag"] == "TT-2208" for r in rows))
        self.assertIn("S1/P1/PAST1/P-101", rep["selection"]["items"])
        with self.assertRaises(mc.ReportError):
            mc.affected(self.revd)
        twin = dict(next(n for n in self.open["nodes"] if n["id"] == FDV), id="S1/P1/CIP1/FDV-2210",
                    scope="S1/P1/CIP1")
        with self.assertRaises(mc.ReportError) as cm:  # a tag on two items refuses
            mc.select((mc.View(dict(self.open, nodes=self.open["nodes"] + [twin]), "x"),), ["FDV-2210"])
        self.assertIn("give the qualified id", str(cm.exception))

    def test_closeout_changed_and_still_unchanged_per_owner(self):
        rep = mc.closeout(self.open, self.close, ["FDV-2210", "TT-2208"])
        status = {(r["record"], r["tag"]): r["status"] for rs in rep["by_owner"].values() for r in rs}
        for key, want in ((("S1/DOC/PID-P1-PAST1-01", "FDV-2210"), "changed"),
                          (("CMMS-2026-10", "FDV-2210"), "changed"),
                          (("INSTRUMENT-INDEX", "TT-2208"), "changed"),
                          (("S1/DOC/HACCP-PLAN-P1", "FDV-2210"), "changed"),
                          (("WO-HISTORY", "FDV-2210"), "changed"),
                          (("VALVE-DATASHEETS", "FDV-2210"), "unchanged"),
                          (("S1/DOC/SOP-PAST1-02", "TT-2208"), "unchanged"),
                          (("rule R-CRITICAL-PM", "FDV-2210"), "still open"),
                          (("flag: HACCP reassessment", "FDV-2210"), "not checked here: confirm the review was done")):
            self.assertEqual(status[key], want, key)
        self.assertEqual([r["record"] for r in rep["still_unchanged"]["Engineering"]], ["VALVE-DATASHEETS"])
        md = mc.closeout_md(rep)
        self.assertIn("## Still unchanged, by owner", md)
        self.assertIn("### Engineering", md)


class ChangeFlags(MocBuilds, unittest.TestCase):
    def test_flags_for_ccp_relief_interlock_and_criticality(self):
        v = mc.View(self.open, "open")
        self.assertEqual([f[0] for f in mc.flags(v, "S1/P1/PAST1/TT-2207")], [mc.FLAG_HACCP, mc.FLAG_CRIT])
        self.assertIn("monitoring instrument of CCP-1", mc.flags(v, "S1/P1/PAST1/TT-2207")[0][1])
        self.assertEqual([f[0] for f in mc.flags(v, "S1/P1/PAST1/PSV-2215")], [mc.FLAG_PHA])
        self.assertEqual([f[0] for f in mc.flags(v, "S1/P1/PAST1/PSV-2216")], [mc.FLAG_PHA], "a relief device kind")
        self.assertEqual(mc.flags(v, "S1/P1/PAST1/PHE-2201"), [])
        self.assertEqual(mc.flags(v, "S1/P1/CIP1/P-301", critical=("B",)), [], "the critical values are a choice")
        g = json.loads(json.dumps(self.open))
        g["records"]["interlock_list"] = [{"register": "interlock_list", "id": "IL-7", "item": "S1/P1/PAST1/TT-2207",
                                           "scope": "S1/P1/PAST1",
                                           "values": {"interlock_id": "IL-7", "cause_tag": "TT-2207",
                                                      "effect_tag": "FDV-2210"},
                                           "source": {"document": "IL-P1", "locator": "row 2"}}]
        v2 = mc.View(g, "g")
        self.assertIn((mc.FLAG_PHA, "effect of interlock IL-7 (IL-P1)", "IL-P1"), mc.flags(v2, FDV))
        self.assertIn((mc.FLAG_PHA, "cause of interlock IL-7 (IL-P1)", "IL-P1"), mc.flags(v2, "S1/P1/PAST1/TT-2207"))


CHANGE_HEADER = ["change_id", "tag", "plant", "unit", "changed_on", "change", "change_kind", "attribute", "old_value",
                 "new_value", "uom", "reason", "raised_by", "decided_by", "decided_on", "source_quote",
                 "affects_register", "external_ref", "locator", "status", "note"]
ALARM_HEADER = ["tag", "plant", "unit", "alarm_type", "setpoint", "uom", "priority", "operator_action",
                "rationalized_on", "locator", "status", "note"]
TT = "S1/P1/PAST1/TT-2207"


def change(cid, tag, on, new_value, register="alarm_list", attribute="setpoint", status="unverified"):
    row = dict(change_id=cid, tag=tag, plant="P1", unit="PAST1", changed_on=on, change=f"{attribute} to {new_value}",
               attribute=attribute, new_value=new_value, affects_register=register, status=status,
               external_ref=f"https://changes.example.com/{cid}")
    return [row.get(k, "") for k in CHANGE_HEADER]


class ChangeRecordCopies(unittest.TestCase):
    """change_record rows (a read-only copy of accepted changes) with affects_register flag the named register's row
    for the same tag as possibly out of date; they never change a value."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "in"
        shutil.copytree(PAST, self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, changes, alarm_setpoint="72.5"):
        write_csv(self.dir / "records" / "alarm_list.csv", ALARM_HEADER,
                  [["TT-2207", "P1", "PAST1", "L", alarm_setpoint, "degC", "High", "Confirm divert", "2026-01-12", "",
                    "unverified", ""]])
        write_csv(self.dir / "records" / "change_record.csv", CHANGE_HEADER, changes)
        site = json.loads((self.dir / "site.json").read_text(encoding="utf-8"))
        site["records"] += [{"id": "ALARMS-P1", "register": "alarm_list", "path": "records/alarm_list.csv",
                             "revision": "4", "scopes": ["S1/P1"]},
                            {"id": "CHANGES-P1", "register": "change_record", "path": "records/change_record.csv",
                             "revision": "2026-11-01", "scopes": ["S1/P1"]}]
        (self.dir / "site.json").write_text(json.dumps(site, indent=1), encoding="utf-8")
        g, _, rows, _ = quiet(om.build, self.dir / "site.json", Path(self.tmp.name) / "out", full=True)
        return g, [r for r in rows if r["kind"] in (om.CHANGE_STALE, om.CHANGE_NOTE)]

    def test_affected_register_row_becomes_a_review_item_and_no_value_changes(self):
        g, rows = self.build([change("CHG-2026-0412", "TT-2207", "2026-10-20", "72.8"),
                              change("CHG-2026-0388", "P-101", "2026-09-30", "double mechanical", register="datasheet",
                                     attribute="seal_type")])
        by_item = {r["item"]: r for r in rows}
        self.assertEqual(sorted(by_item), ["S1/P1/PAST1/P-101", TT], [r["why"] for r in rows])
        alarm = by_item[TT]
        self.assertEqual((alarm["kind"], alarm["owner"]), (om.CHANGE_STALE, "I&C"))
        for words in ("alarm list ALARMS-P1 (row 2) may be out of date since change CHG-2026-0412 (2026-10-20",
                      "it says setpoint 72.5, the change says 72.8", "https://changes.example.com/CHG-2026-0412",
                      "nothing was changed here"):
            self.assertIn(words, alarm["why"])
        pump = by_item["S1/P1/PAST1/P-101"]
        self.assertEqual(pump["owner"], "Engineering")
        self.assertIn("datasheet PUMP-DATASHEETS may be out of date since change CHG-2026-0388", pump["why"])
        self.assertNotIn("it says", pump["why"], "the datasheet holds no seal_type, so nothing is quoted")
        # read-only: the alarm row keeps its value, and a change record is never a value conflict
        self.assertIn("72.5", (self.dir / "records" / "alarm_list.csv").read_text(encoding="utf-8"))
        self.assertFalse([c for c in conflicts_of(g) if "CHG-2026" in json.dumps(c)])
        self.assertEqual(om.problems(g), [])

    def test_row_already_holding_the_new_value_or_superseded_or_rejected_raises_nothing(self):
        _, rows = self.build([change("CHG-2026-0412", "TT-2207", "2026-10-20", "72.8")], alarm_setpoint="72.8")
        self.assertEqual(rows, [])
        _, rows = self.build([change("CHG-2026-0101", "TT-2207", "2026-01-05", "72.6"),
                              change("CHG-2026-0412", "TT-2207", "2026-10-20", "72.8")], alarm_setpoint="72.8")
        self.assertEqual(rows, [], "only the latest change per item, register and attribute is compared")
        _, rows = self.build([change("CHG-2026-0412", "TT-2207", "2026-10-20", "72.8", status="rejected")])
        self.assertEqual(rows, [])

    def test_undated_change_says_undated(self):
        _, rows = self.build([change("CHG-2026-0412", "TT-2207", "", "72.8")])
        self.assertEqual(len(rows), 1)
        self.assertIn("since change CHG-2026-0412 (undated:", rows[0]["why"])
        self.assertNotIn("None", rows[0]["why"])

    def test_unknown_register_is_a_note_not_a_flag(self):
        _, rows = self.build([change("CHG-2026-0412", "TT-2207", "2026-10-20", "72.8", register="alarm_lists")])
        self.assertEqual([(r["kind"], r["owner"]) for r in rows], [(om.CHANGE_NOTE, "Change process owner")])
        self.assertIn("'alarm_lists', which is not a register", rows[0]["why"])


if __name__ == "__main__":
    unittest.main()
