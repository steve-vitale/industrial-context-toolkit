"""Check the frozen literal key against original CSV/text, without importing candidate tools."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(path.read_bytes())


def table(path, delimiter=","):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def check_inputs():
    freeze = read(HERE / "INPUT-FREEZE.json")
    expected = read(HERE / "inputs/EXPECTED.json")
    checks = []

    def check(name, value):
        if not value:
            raise ValueError("Input/key mismatch: " + name)
        checks.append(name)

    actual_files = {p.relative_to(HERE).as_posix()
                    for p in (HERE / "inputs").rglob("*") if p.is_file()}
    check("complete fixed input inventory", actual_files == set(freeze["input_raw_sha256"]))
    for name, digest in freeze["input_raw_sha256"].items():
        check("raw bytes " + name,
              hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest)
    for name, digest in freeze["preselected_public_procedural_transfer"].items():
        check("retained public conversion " + name,
              hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest)
    for record in expected["revisions"]:
        rev = record["revision"]
        folder = HERE / "inputs/development" / ("rev" + str(rev))
        equipment = table(folder / "equipment.csv")
        orders = table(folder / "work-orders.csv")
        instruments = table(folder / "instruments.csv")
        sheet = table(folder / "datasheet.csv")[0]
        sources = {r["DocumentID"]: r for r in table(folder / "source-register.csv")}
        pump = next(r for r in equipment if r["Equipment"] == "P-101" and r["Area"] == "U1")
        other = next(r for r in equipment if r["Equipment"] == "P-101" and r["Area"] == "U2")
        check(f"rev{rev} separate scoped pumps",
              pump["Serial"] == record["export_serial"] and other["Serial"] == "OTHER-101")
        check(f"rev{rev} closed orders versus proposal",
              [r["InstalledSerial"] for r in orders if r["Closed"]] == record["closed_order_serials"]
              and [r["InstalledSerial"] for r in orders if not r["Closed"]] == [record["open_proposal_serial"]])
        check(f"rev{rev} actual datasheet value/status",
              sheet["RatedFlow"] == record["datasheet_flow"] and sheet["FlowUnit"] == "m3/h"
              and sources["DS"]["Status"] == record["datasheet_status"])
        check(f"rev{rev} required instrument facts",
              [(r["Tag"], r["Type"]) for r in instruments] ==
              [("FT-101", "transmitter"), ("FIC-101", "controller"), ("FV-101", "control_valve")]
              and instruments[0]["EngineeringUnit"] == expected["shared_facts"]["unit"])
        note = (folder / "engineering-note.txt").read_text(encoding="utf-8").splitlines()
        check(f"rev{rev} independent literal narrative and missing behavior",
              note[3] == "FIC-101 reads FT-101 and adjusts FV-101."
              and note[4] == "Valve fail position, trip settings and operating limits are not supplied.")
    first, second = (HERE / "inputs/development" / r for r in ("rev1", "rev2"))
    check("rev2 independent records unchanged",
          all((first / f).read_bytes() == (second / f).read_bytes()
              for f in ("equipment.csv", "work-orders.csv", "instruments.csv", "engineering-note.txt")))
    transfer = HERE / "inputs/transfer/dialect-b"
    equipment = table(transfer / "equipment.csv", ";")
    orders = table(transfer / "work-orders.csv", ";")
    key = expected["transfer_dialect_b"]
    check("second dialect fixed scope/serial expectations",
          equipment[0]["Vendor serial"] == key["export_serial"]
          and equipment[1]["Functional location"] == "SKID-B"
          and orders[0]["Installed serial"] == key["closed_order_serial"])
    # Type assertions here guard the oracle itself, not a candidate's equality.
    check("false/zero/null/empty controls remain distinct types",
          [type(v).__name__ for v in expected["typed_controls"]] ==
          ["bool", "int", "bool", "int", "NoneType", "str", "list", "dict", "str", "str"])
    original_types = read(HERE / "inputs/development/typed-source.json")
    check("typed expectations are grounded in retained original JSON",
          json.dumps(original_types["values"], sort_keys=True) ==
          json.dumps(expected["typed_controls"], sort_keys=True)
          and type(original_types["float_one"]) is float
          and json.dumps(original_types["signed_zero"]) == "-0.0")
    print(json.dumps({"checks": len(checks), "passed": len(checks),
                      "scope": "original fixture bytes and literal source/key consistency only",
                      "candidate_acceptance": "not run", "product_receiving": "not run"}))


if __name__ == "__main__":
    check_inputs()
