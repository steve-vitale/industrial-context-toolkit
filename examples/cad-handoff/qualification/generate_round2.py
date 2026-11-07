"""Freeze replacement authored cases; no candidate import or run."""
import argparse
import hashlib
import json
from pathlib import Path

import ezdxf
import generate_fixtures as base

CASES = [
    ("validation-r12", "reserved-authored", "R12", "cp1252", "lf", 2, 19, "Rev-A", "Rev-B"),
    ("validation-cp1251", "reserved-authored", "R2000", "cp1251", "mixed", 2, 210, "Двигатель", "Мотор"),
    ("validation-long", "reserved-authored", "R2004", "cp1252", "crlf", 1, 0, "A" * 81, "B" * 107),
    ("validation-unicode", "reserved-authored", "R2007", "utf8", "crlf", 3, 77, "Valve Ω", "Válvula Ж"),
    ("validation-braces", "reserved-authored", "R2013", "utf8", "lf", 2, 346, "Assembly {C}", "Assembly {D}"),
    ("validation-foreign", "reserved-authored", "R2018", "utf8", "mixed", 3, 123, "V-5", "V-6"),
]


def generate(dest):
    base.CASES = CASES
    base.generate(dest)
    manifest_path = dest / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Extra varied geometry is authored before a corrected method or reserved run.
    for case in manifest["cases"]:
        path = dest / case["source"]
        doc = ezdxf.readfile(path)
        if case["version"] == "R12":
            doc.modelspace().add_polyline2d([(3, -8), (17, -3), (30, -9), (3, -8)])
        else:
            doc.modelspace().add_ellipse((18, 38), major_axis=(8, 2, 0), ratio=0.4)
            doc.layouts.new("Qualification sheet").add_viewport(center=(65, 40), size=(100, 70),
                view_center_point=(50, 15), view_height=80)
        doc.saveas(path)
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        raw = raw.replace(b"  0\nEOF", b"999\nRound two raw payload remains part of the source\n  0\nEOF")
        if case["newline"] == "crlf":
            raw = raw.replace(b"\n", b"\r\n")
        elif case["newline"] == "mixed":
            raw = b"".join(line + (b"\r\n" if i % 4 else b"\n")
                           for i, line in enumerate(raw.split(b"\n")[:-1]))
        path.write_bytes(raw)
        case["source_sha256"] = base.sha(raw)
        planpath = dest / case["plan"]
        plan = json.loads(planpath.read_text(encoding="utf-8"))
        plan["source_sha256"] = case["source_sha256"]
        planpath.write_text(json.dumps(plan, indent=2, ensure_ascii=True)+"\n", encoding="utf-8", newline="\n")
        case["plan_sha256"] = base.sha(planpath.read_bytes())
    manifest["replacement_generator_sha256_lf"] = base.sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))
    manifest["exposure"] = "Round-1 cohort is exposed development/regression. These six replacement configurations and extra geometry are frozen before the corrected method; same-author procedural validation, not independent plant evidence."
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    generate(parser.parse_args().out)
