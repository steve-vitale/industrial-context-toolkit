"""Retain real earlier-route runs beside a literal, source-authored key; no candidate imports."""
import argparse
import csv
import datetime
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def sha(path, text=False):
    value = path.read_bytes()
    return hashlib.sha256(value.replace(b"\r\n", b"\n") if text else value).hexdigest()


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def baseline(out):
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("Baseline destination exists; retain it and choose a new folder")
    out.mkdir(parents=True)
    checks, commands = [], []
    key = load(HERE / "BASELINE-KEY.json")

    def check(name, passed):
        checks.append({"check": name, "passed": bool(passed)})
        write(out / "checks.json", checks)
        if not passed:
            raise ValueError("Baseline key mismatch: " + name)

    def command(label, args, expected=0):
        started = time.perf_counter()
        result = subprocess.run([sys.executable, "-B", "-S", *args], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace")
        record = {"label": label, "args": args, "exit_code": result.returncode,
                  "expected_exit": expected, "wall_seconds": time.perf_counter() - started,
                  "stdout": result.stdout, "stderr": result.stderr}
        commands.append(record)
        write(out / "commands.json", commands)
        check(label + " expected exit", result.returncode == expected)
        return result

    # The document finding below is an authored agent brief checked against literal
    # original lines. This is not an automated text reader or a fresh-agent trial.
    doc = key["document"]
    lines = (ROOT / doc["source"]).read_text(encoding="utf-8").splitlines()
    check("original document fact lines",
          "FT-101 measures flow on S3 downstream of P-1." == lines[4]
          and "FIC-101 reads FT-101 and adjusts FV-101." == lines[6])
    check("original document missing context",
          all(value.lower() in lines[7].lower() for value in doc["unknowns"]))
    brief = {
        "operator": "root coding agent; fixture and key exposed",
        "finding": "FIC-101 reads FT-101 and adjusts FV-101; no valve fail position or trip setting is supplied.",
        "source": doc["source"], "locators": ["line 7", "line 8"],
        "source_sha256": sha(ROOT / doc["source"]), "plant_acceptance": "not performed",
        "software_route": "Agent-authored plain brief; no graph, signup or model call",
        "human_time": "not measured",
    }
    write(out / "document-brief.json", brief)

    mk = key["maintenance"]
    eq, orders = rows(ROOT / mk["equipment"]), rows(ROOT / mk["orders"])
    check("original equipment identities and serials",
          eq[0] == {"Equipment": "P-101", "Area": "U1", "Serial": "OLD-101", "Model": "PX20"}
          and eq[1]["Equipment"] == "P-101" and eq[1]["Area"] == "U2")
    check("closed installation and open proposal differ",
          orders[0]["Order"] == mk["closed_order"] and orders[0]["Closed"] == "2026-11-01"
          and orders[0]["InstalledSerial"] == mk["installed_serial"]
          and orders[1]["Order"] == mk["open_order"] and orders[1]["Closed"] == ""
          and orders[1]["InstalledSerial"] == mk["proposed_serial"])
    command("maintenance-three-revisions",
            ["examples/maintenance-intake/reproduce.py", "--out", str(out / "maintenance")])
    packets = [load(out / "maintenance" / name / "findings.json")
               for name in ("initial", "corrected", "next-replacement")]
    check("three actual conflict counts",
          [len(p["findings"]) for p in packets] == mk["expected_conflict_counts"])
    check("same functional position retains new installation discrepancy",
          packets[0]["findings"][0]["subject"] == packets[2]["findings"][0]["subject"] == mk["subject"])
    check("closed order source values retained",
          {packets[0]["findings"][0][side]["says"] for side in ("source_a", "source_b")}
          == {mk["export_serial"], mk["installed_serial"]})
    check("vanished discrepancy is not accepted correction",
          packets[1]["history"]["no_longer_detected"][0]["status"] == "open")

    requests = load(ROOT / key["drawing"]["requests"])["markups"]
    expected = key["drawing"]["first_request"]
    first = next(r for r in requests if r["id"] == expected["id"])["checks"][0]
    check("drawing request original literal basis",
          first["key"]["subject"] == expected["subject"]
          and first["key"]["name"] == expected["property"]
          and first["before"] == expected["before"] and first["after"] == expected["after"])
    command("drawing-receiving",
            ["examples/drawing-handoff/reproduce.py", "--out", str(out / "drawing")])
    drawing = load(out / "drawing/markup/result.json")
    check("drawing release remains unaccepted", drawing["release_accepted"] is False)

    command("one-map", ["scripts/one_map.py", "build",
            "examples/one-map/inputs/site.json", "--out", str(out / "map")])
    ambiguous = command("ambiguous-tag", ["scripts/one_map.py", "ask", "--map",
            str(out / "map/graph.json"), "--question-kind", "documents",
            "--item", "P-101", "--json"])
    abstention = json.loads(ambiguous.stdout)
    check("ambiguous selection returns no chosen item or invented facts",
          abstention["item"] is None and abstention["facts"] == []
          and abstention["answer"] == "can't answer from this map"
          and abstention["reason"] == "P-101 is in 2 scopes (S1/P1/200/P-101, S1/P2/300/P-101); give the qualified id")
    command("qualified-question", ["scripts/one_map.py", "ask", "--map",
            str(out / "map/graph.json"), "--question-kind", "disagreements",
            "--item", "S1/P1/200/P-101", "--json"])

    # Preserve the distinction between source bytes and normalized Python methods.
    source_dirs = ["examples/maintenance-intake/inputs", "examples/pid-markup-review/inputs"]
    sources = {doc["source"]: sha(ROOT / doc["source"])}
    for folder in source_dirs:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file():
                sources[path.relative_to(ROOT).as_posix()] = sha(path)
    methods = {p.relative_to(ROOT).as_posix(): sha(p, True)
               for p in sorted((ROOT / "scripts").glob("*.py"))}
    write(out / "basis.json", {
        "schema": "map-component-baseline-1",
        "started_from_commit": "a26a0e0a4e8588081e16a1a63b2f26d045a75cb4",
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(),
        "source_raw_sha256": sources, "method_sha256_lf": methods,
        "key_sha256_lf": sha(HERE / "BASELINE-KEY.json", True),
        "runner_sha256_lf": sha(Path(__file__), True),
        "method_claim": "Existing scripts only; commands/outputs retained, no candidate implementation used",
        "friction": {
            "maintenance_inner_cli_calls": len(load(out / "maintenance/replay.json")["commands"]),
            "maintenance_supplied_profile_json": "required",
            "document": "authored agent interpretation, exposed fixed text, no automated reading claim",
            "drawing": "supplied inventory and readings; own drawing preparation still required",
            "mapping_reuse": "profile supplied and revised by existing runner",
            "customer_interactions": "not measured; scripted setup is not a user trial",
            "receiving": "local files only; no product receiving"
        },
        "checks": len(checks), "passed": sum(c["passed"] for c in checks),
        "human_effort": "not measured", "engineering_acceptance": "not performed"
    })
    print(json.dumps({"checks": len(checks), "passed": sum(c["passed"] for c in checks),
                      "out": str(out), "product_receiving": "not run"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        baseline(args.out)
    except (OSError, ValueError, KeyError, IndexError) as error:
        parser.exit(2, str(error) + "\n")

