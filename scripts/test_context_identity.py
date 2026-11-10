"""Source-known ordinary CSV identity crosswalk and explicit physical replacement controls."""
import copy
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import context_basis as cb
import context_packet as cp

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/map-component-cycle/inputs/identity-change"
PUMP, OTHER = "IX/P1/U1/FP-1001", "IX/P1/U2/FP-2001"


class IdentityCrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def cli(self, *args, code=0, message=None):
        result = subprocess.run([sys.executable,"-B","-S",str(ROOT/"scripts/context_workflow.py"),*map(str,args)],capture_output=True,timeout=60)
        self.assertEqual(result.returncode,code,result.stderr.decode("utf8","replace"))
        if message:self.assertIn(message,result.stderr.decode("utf8","replace"))
        return json.loads(result.stdout if code==0 else result.stderr)

    def prepare(self,rev,name,previous=None,records=None):
        target=self.root/name
        args=["prepare","--records",records or FIXTURE/('rev'+str(rev)),"--site","IX","--plant","P1","--out",target]
        if previous:args += ["--previous",previous]
        else:args += ["--identity-crosswalk","identity-crosswalk.csv"]
        self.cli(*args)
        return target

    def test_unique_alias_query_returns_canonical_identity_and_exact_source_evidence(self):
        packet=self.prepare(1,"r1")
        answer=self.cli("query",packet,"--item","LEGACY-7","--field","class")
        self.assertEqual(answer["subject"],PUMP)
        resolved=answer["identity_resolution"]
        self.assertEqual(resolved["subject"],PUMP)
        self.assertEqual(resolved["input"],"LEGACY-7")
        self.assertEqual(len(resolved["alias_evidence"]),1)
        evidence=resolved["alias_evidence"][0]
        self.assertEqual(evidence["value"],"LEGACY-7")
        self.assertEqual(evidence["source"],"XW")
        self.assertEqual(evidence["source_record"]["revision"],"1")
        self.assertEqual(evidence["roots"],["XW"])
        self.assertEqual(evidence["locator"],"CSV record 4; physical lines 4-4; column Alias")
        self.assertEqual(evidence["source_record"]["sha256"],cb.raw_sha((packet/"originals/identity-crosswalk.csv").read_bytes()))
        self.assertEqual(evidence["review"]["status"],"unreviewed")
        self.assertEqual(cb.read_json(packet/"intake.json")["identity_crosswalk"],"identity-crosswalk.csv")
        aliases = self.cli("query",packet,"--item",PUMP,"--field","identity_alias")
        self.assertEqual(aliases["state"],"sourced_unreviewed")
        self.assertEqual(aliases["cardinality"],"declared_alias_set")
        self.assertEqual(aliases["evidence_fingerprint"],cb.digest(aliases["alternatives"]))
        self.assertTrue(all(c["lookup_active"] for c in aliases["alternatives"]))
        self.assertTrue(self.cli("verify",packet)["verified"])

    def test_same_bare_alias_across_units_refuses_but_scoped_alias_resolves(self):
        packet=self.prepare(1,"r1")
        self.cli("query",packet,"--item","P-101",code=2,message="ambiguous item")
        for scoped,target in [("IX/P1/U1/P-101",PUMP),("IX/P1/U2/P-101",OTHER)]:
            answer=self.cli("query",packet,"--item",scoped,"--field","class")
            self.assertEqual(answer["subject"],target)
            self.assertTrue(answer["identity_resolution"]["alias_evidence"])

    def test_retained_revisions_preserve_stable_position_and_distinct_reported_physical_items(self):
        r1=self.prepare(1,"r1");r2=self.prepare(2,"r2",r1)
        self.assertEqual(self.cli("query",r2,"--item","P-201","--field","class")["subject"],PUMP)
        basis=cp.open_packet(r2)["basis"]
        identities={e["id"] for e in basis["entities"]}
        self.assertIn(PUMP,identities)
        self.assertIn("IX/P1/U1/item:ITEM-A",identities)
        self.assertIn("IX/P1/U1/item:ITEM-B",identities)
        links=[r for r in basis["relationships"] if r["predicate"]=="reported_installation_at" and r["object"]==PUMP]
        self.assertEqual({r["subject"] for r in links},{"IX/P1/U1/item:ITEM-A","IX/P1/U1/item:ITEM-B"})
        self.assertTrue(all("not independently verified current installation" in r["qualification"] for r in links))
        self.assertEqual((r2/"previous/originals/equipment.csv").read_bytes(),(r1/"originals/equipment.csv").read_bytes())
        self.assertEqual(self.cli("query",r2,"--item",PUMP,"--field","serial_number")["alternatives"][0]["value"],"SERIAL-X")
        self.assertNotIn("identity_resolution",self.cli("query",r2,"--item",PUMP,"--field","class"))

    def test_withdrawn_crosswalk_stops_current_alias_and_preserves_historical_source(self):
        r1=self.prepare(1,"r1");r2=self.prepare(2,"r2",r1);r3=self.prepare(3,"r3",r2)
        for alias in ("LEGACY-7","P-201","P-101"):
            self.cli("query",r3,"--item",alias,code=2,message="item not found")
        current=self.cli("query",r3,"--item",PUMP,"--field","identity_alias")
        self.assertEqual(current["state"],"inactive_evidence")
        self.assertTrue(all(not c["active_source"] for c in current["alternatives"]))
        self.assertEqual(self.cli("query",r3/"previous","--item","P-201","--field","class")["subject"],PUMP)
        self.assertEqual(self.cli("verify",r3)["history_depth"],2)
        delivery=self.root/"delivery.json";self.cli("bundle",r3,"--out",delivery)
        reopened=self.root/"reopened";self.cli("unbundle",delivery,"--out",reopened)
        self.cli("query",reopened,"--item","P-201",code=2,message="item not found")

    def test_unopted_crosswalk_keeps_exact_legacy_csv_route_and_does_not_activate_aliases(self):
        packet=self.root/"ordinary"
        self.cli("prepare","--records",FIXTURE/"rev1","--site","IX","--plant","P1","--out",packet)
        self.assertNotIn("identity_crosswalk",cb.read_json(packet/"intake.json"))
        self.cli("query",packet,"--item","LEGACY-7",code=2,message="item not found")
        self.assertTrue(self.cli("verify",packet)["verified"])

    def test_unknown_physical_target_and_canonical_shadow_refuse_without_output(self):
        for tag,alias in [("UNKNOWN","bad"),("item:ITEM-A","bad"),("FP-1001",OTHER)]:
            with self.subTest(tag=tag,alias=alias):
                records=self.root/('records-'+str(len(list(self.root.iterdir()))));shutil.copytree(FIXTURE/"rev1",records)
                (records/"identity-crosswalk.csv").write_text("Position,Area,Alias\n"+tag+",U1,"+alias+"\n",encoding="utf8")
                target=self.root/('refusal-'+str(len(list(self.root.iterdir()))))
                self.cli("prepare","--records",records,"--site","IX","--plant","P1","--identity-crosswalk","identity-crosswalk.csv","--out",target,code=2)
                self.assertFalse(target.exists())

    def test_missing_declared_crosswalk_stops_aliases_and_unknown_path_refuses(self):
        records=self.root/"missing-records";shutil.copytree(FIXTURE/"rev1",records)
        (records/"identity-crosswalk.csv").unlink()
        packet=self.prepare(1,"missing-crosswalk",records=records)
        self.cli("query",packet,"--item","LEGACY-7",code=2,message="item not found")
        basis=cp.open_packet(packet)["basis"]
        self.assertEqual(next(s for s in basis["sources"] if s["id"]=="XW")["status"],"missing")
        self.assertFalse(any(c["predicate"]=="identity_alias" for c in basis["claims"]))
        target=self.root/"bad-path"
        self.cli("prepare","--records",records,"--site","IX","--plant","P1","--identity-crosswalk","unknown.csv","--out",target,code=2,message="not declared")
        self.assertFalse(target.exists())

    def test_open_order_remains_proposal_and_alias_edits_retain_canonical_corrections(self):
        records=self.root/"open-records";shutil.copytree(FIXTURE/"rev2",records)
        source=records/"closed-orders.csv"
        source.write_bytes(source.read_bytes()+b"FP-1001,U1,WO-300,,ITEM-FUTURE,SERIAL-X\n")
        packet=self.prepare(2,"open",records=records)
        basis=cp.open_packet(packet)["basis"]
        self.assertFalse(any(e["id"]=="IX/P1/U1/item:ITEM-FUTURE" for e in basis["entities"]))
        future=next(c for c in basis["claims"] if c["predicate"]=="proposed_physical_item_id")
        self.assertEqual(future["subject"],"IX/P1/U1/record:WO-300")
        self.assertEqual(future["value"],"ITEM-FUTURE")
        self.assertEqual(future["review"]["status"],"proposed")
        edited=self.root/"edited"
        self.cli("edit",packet,"--item","P-201","--field","description","--value","Check source tag","--rationale","Confirm permitted record","--out",edited)
        self.assertEqual(cp.open_packet(edited)["basis"]["corrections"][0]["subject"],PUMP)
        self.assertEqual(self.cli("query",edited,"--item","P-201","--field","class")["subject"],PUMP)
        self.assertEqual(self.cli("query",edited,"--item",PUMP,"--field","description")["alternatives"][0]["value"],"Feed pump")

    def test_changed_source_or_forged_alias_basis_refuses_packet_replay(self):
        packet=self.prepare(1,"r1")
        source=packet/"originals/identity-crosswalk.csv";before=source.read_bytes();source.write_bytes(before+b"changed")
        self.cli("verify",packet,code=2)
        source.write_bytes(before)
        basis=cb.read_json(packet/"basis.json")
        claim=next(c for c in basis["claims"] if c["predicate"]=="identity_alias")
        claim["value"]="FORGED"
        (packet/"basis.json").write_bytes(cp.encode(basis))
        self.cli("verify",packet,code=2)

    def test_proposed_and_rejected_alias_claims_or_boundary_subjects_never_become_lookup_targets(self):
        packet=self.prepare(1,"r1");basis=cp.open_packet(packet)["basis"]
        for status in ("proposed","rejected"):
            changed=copy.deepcopy(basis)
            for c in changed["claims"]:
                if c["predicate"]=="identity_alias":c["review"]["status"]=status
            with self.assertRaisesRegex(cb.ContextError,"item not found"):cb.View(changed).resolve("LEGACY-7")
        changed=copy.deepcopy(basis)
        entity=next(e for e in changed["entities"] if e["id"]==PUMP)
        changed["entities"].remove(entity);changed["boundaries"].append({"id":PUMP,"name":"External identity reference"})
        with self.assertRaises(cb.ContextError):cb.View(changed)


if __name__ == "__main__":
    unittest.main()
