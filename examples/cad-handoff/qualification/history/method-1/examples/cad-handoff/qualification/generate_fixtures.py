"""Freeze authored development/reserved DXF fixtures before a preservation candidate is run."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import ezdxf

CASES = [
    ("dev-legacy", "development", "R2000", "cp1252", "crlf", 1, 0, "A", "B"),
    ("dev-unicode", "development", "R2013", "utf8", "lf", 2, 25, "Pump α", "ポンプ β"),
    ("reserve-r12", "reserved-authored", "R12", "cp1252", "lf", 1, 0, "Legacy", "Legacy-2"),
    ("reserve-mirror", "reserved-authored", "R2000", "cp1252", "crlf", 2, 137, "Étage", "Étage-2"),
    ("reserve-cyrillic", "reserved-authored", "R2004", "cp1251", "crlf", 1, 315, "Насос", "Насос-2"),
    ("reserve-multiple", "reserved-authored", "R2007", "utf8", "lf", 3, 63, "Train-1", "Train-2"),
    ("reserve-foreign", "reserved-authored", "R2013", "utf8", "crlf", 2, 11, "장치-A", "장치-B"),
    ("reserve-mixed", "reserved-authored", "R2018", "utf8", "mixed", 3, 269, "Model {A}", "Model {B}"),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def generate(dest):
    if dest.exists():
        raise ValueError("Destination exists; retain the original frozen fixtures")
    dest.mkdir(parents=True)
    ezdxf.options.write_fixed_meta_data_for_testing = True
    cases = []
    for name, split, version, encoding, newline, count, rotation, before, after in CASES:
        doc = ezdxf.new(version)
        doc.encoding = encoding
        doc.layers.new("PIPE", dxfattribs={"color": 3})
        doc.layers.new("LABEL", dxfattribs={"color": 2})
        doc.appids.new("FOREIGN_VENDOR")
        block = doc.blocks.new("ASSET")
        block.add_circle((0, 0), 2)
        block.add_line((-3, 0), (3, 0))
        keys = ["ICT_ID", "TAG", "MODEL", "SERIAL", "SIZE", "VENDOR_PRIVATE"]
        if name in {"reserve-foreign", "reserve-mixed"}:
            keys.reverse()
        for i, key in enumerate(keys):
            block.add_attdef(key, (3, -i), dxfattribs={"height": 0.6, "layer": "LABEL"})
        changes = []
        for i in range(count):
            identity = name + "/asset-" + str(i + 1)
            ref = doc.modelspace().add_blockref("ASSET", (15 + i * 35, 20 + i * 8), dxfattribs={
                "rotation": rotation, "xscale": -1 if name == "reserve-mirror" else 1 + i / 3,
                "yscale": 1 + i / 5, "layer": "PIPE"})
            ref.add_auto_attribs(dict(ICT_ID=identity, TAG="FV-"+str(101+i), MODEL=before,
                                      SERIAL="UNCHANGED-"+str(i), SIZE="DN50",
                                      VENDOR_PRIVATE="retain {vendor} \\P "+str(i)))
            ref.set_xdata("FOREIGN_VENDOR", [(1000, "foreign identity "+str(i)), (1040, 4.125)])
            if version != "R12":
                record = ref.new_extension_dict().add_xrecord("FOREIGN_RECORD")
                record.reset([(1, "retained model-irrelevant text"), (40, 12.5), (70, 7)])
            changes.append(dict(id=identity, attribute="MODEL", before=before, after=after,
                                reason="Authored qualification edit, not an installed equipment claim"))
        msp = doc.modelspace()
        msp.add_line((0, 20), (110, 20), dxfattribs={"layer": "PIPE"})
        msp.add_arc((45, 32), 7, 20, 300)
        if version == "R12":
            msp.add_polyline2d([(0, 0), (8, 4), (18, 0)])
        else:
            msp.add_lwpolyline([(0, 0, 0.2), (8, 4, -0.3), (18, 0, 0)], format="xyb")
            hatch = msp.add_hatch(color=5)
            hatch.paths.add_polyline_path([(70, 0), (80, 0), (80, 6), (70, 6)], is_closed=True)
        source = dest / (name + ".dxf")
        doc.saveas(source)
        raw = source.read_bytes().replace(b"\r\n", b"\n")
        raw = raw.replace(b"  0\nEOF", b"999\nUnfamiliar retained raw comment: do not resave me\n  0\nEOF")
        if newline == "crlf":
            raw = raw.replace(b"\n", b"\r\n")
        elif newline == "mixed":
            raw = b"".join(line + (b"\r\n" if i % 3 else b"\n")
                           for i, line in enumerate(raw.split(b"\n")[:-1]))
        source.write_bytes(raw)
        plan = {"schema": "cad-edit-plan-1", "source_sha256": sha(raw), "changes": changes}
        planpath = dest / (name + ".plan.json")
        planpath.write_text(json.dumps(plan, indent=2, ensure_ascii=True)+"\n", encoding="utf-8", newline="\n")
        cases.append(dict(id=name, split=split, source=source.name, source_sha256=sha(raw),
                          plan=planpath.name, plan_sha256=sha(planpath.read_bytes()), version=version,
                          encoding=encoding, newline=newline, assets=count,
                          provenance="Authored fixtures generated with ezdxf, no independent plant truth"))
    manifest = {"schema": "cad-qualification-fixtures-1", "ezdxf": ezdxf.__version__,
                "generator_sha256_lf": sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
                "exposure": "Configurations authored before candidate implementation. Reserved results must remain unopened until method freeze.",
                "cases": cases}
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8", newline="\n")
    print("Frozen", len(cases), "authored cases; no candidate run")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    generate(ap.parse_args().out)
