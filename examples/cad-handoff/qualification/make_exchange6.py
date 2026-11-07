"""Author fresh procedural inputs before developing the equipment-data sidecar method."""
import hashlib
import json
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parent / "exchange-6"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    target = ROOT / "inputs"
    target.mkdir(parents=True, exist_ok=False)
    cases = []
    for number, (version, encoding, crlf, count) in enumerate([
        ("R12", "cp1252", True, 1), ("R2000", "cp1252", False, 2),
        ("R2004", "cp1251", True, 1), ("R2007", "utf-8", False, 3),
        ("R2013", "utf-8", True, 1), ("R2018", "utf-8", False, 1),
    ], 1):
        case = target / f"case-{number}"
        case.mkdir()
        doc = ezdxf.new(version)
        doc.encoding = encoding
        doc.layers.new("RETAIN_PROCESS", dxfattribs={"color": 4})
        doc.appids.new("RETAIN_VENDOR")
        line = doc.modelspace().add_line((1, 3), (137, 29), dxfattribs={"layer": "RETAIN_PROCESS"})
        line.set_xdata("RETAIN_VENDOR", [(1000, "opaque-payload-6"), (1040, 6.125)])
        block = doc.blocks.new("EXCHANGE_SIX")
        block.add_circle((0, 0), 3.75)
        for i, key in enumerate(("ICT_ID", "TAG", "MODEL", "MANUFACTURER", "SIZE", "VENDOR_PRIVATE")):
            block.add_attdef(key, (5, -i * 2), height=1)
        changes = []
        for i in range(count):
            identity = f"EX6/{number}/asset-{i}"
            label = "Насос" if number == 3 else "Pump"
            vendor = '</script><img src=x onerror="globalThis.injected=1"> & retained' if number == 6 else "retain foreign field"
            before = f"{label}-{i}-old"
            ref = doc.modelspace().add_blockref("EXCHANGE_SIX", (20+i*40, 40),
                dxfattribs={"rotation": 37 if number == 2 else 0, "xscale": 1.25, "yscale": 0.75})
            ref.add_auto_attribs({"ICT_ID": identity, "TAG": f"FV-6{number}{i}", "MODEL": before,
                                 "MANUFACTURER": "Example & Co", "SIZE": "DN40", "VENDOR_PRIVATE": vendor})
            changes.append({"id": identity, "attribute": "MODEL", "before": before,
                            "after": "Модель-новая" if number == 3 else "X"*190 if number == 6 else f"Pump-{i}-new",
                            "reason": "Authored procedural replacement note; not installed-state evidence"})
        if number == 4:
            changes.append({"id": "EX6/4/asset-1", "attribute": "TAG", "before": "FV-641",
                            "after": "FV-641A", "reason": "Authored tag revision, same explicit stable ID"})
        if number == 5:
            layout = doc.layouts.new("Retain_layout_six")
            layout.add_viewport(center=(80, 50), size=(130, 80), view_center_point=(45, 35), view_height=85)
            layout.add_text("Retain paper label", dxfattribs={"insert": (5, 5), "height": 2})
        path = case / "source.dxf"
        doc.saveas(path)
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        if crlf:
            raw = raw.replace(b"\n", b"\r\n")
        path.write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        plan = {"schema": "cad-edit-plan-1", "source_sha256": sha, "changes": changes}
        write_json(case / "expected-plan.json", plan)
        cases.append({"id": case.name, "source": f"inputs/{case.name}/source.dxf", "source_sha256": sha,
                      "plan": f"inputs/{case.name}/expected-plan.json",
                      "plan_sha256": hashlib.sha256((case / "expected-plan.json").read_bytes()).hexdigest(),
                      "version": version, "encoding": encoding, "line_endings": "CRLF" if crlf else "LF",
                      "assets": count})
    write_json(ROOT / "INPUTS.json", {"schema": "cad-exchange-six-inputs-1", "cases": cases,
               "provenance": "Six newly authored same-agent procedural cases, not real plants or blind model tests",
               "recipe": "examples/cad-handoff/qualification/make_exchange6.py; ezdxf 1.4.5"})


if __name__ == "__main__":
    main()
