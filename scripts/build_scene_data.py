"""Tennessee Eastman model -> 3D scene data. PROOF OF CONCEPT, built to iterate on; not a validated deliverable.

The 3D operator-orientation tour (drafts/3d-tour/) is rendered by a prototype that is not in this repository yet.
This file is the data contract that sits between the process model and any 3D renderer: which equipment exists,
which tags sit on it, which pipes join it, and which control valves a lockout/tagout (LOTO) mockup must mark as
not positive isolation.
It is generated from data/te_process_model.json only, so a correction to the model reaches the scene by
regenerating, never by editing the scene.

What is data and what is placeholder:
  - equipment, tags, tag ownership and stream end points: copied from the model, with each item's provenance
    (scripts/provenance.py). Nothing is upgraded on the way;
  - positions: the model's 2D layout scaled to metres. Sizes and elevations: fixed placeholders per equipment type.
    Neither comes from a plant;
  - LOTO valve crossings: INFERRED. Every final element the model places on a stream that touches a unit is a
    control valve, listed for that unit as NOT positive isolation so that no view takes it for an isolating device.
    The model holds no block valves, so which device isolates a unit is not assessed. This is a mockup input, not a
    procedure (docs/GOAL_ISOLATION_POC.md; the site's energy-control program, OSHA 29 CFR 1910.147).

Deterministic: no timestamps; sorted output. Stdlib only.
Usage:  python scripts/build_scene_data.py [model.json] [out.json]
"""
import hashlib
import json
import sys
from pathlib import Path

from isolation_wording import MOCKUP_STATUS, NOT_POSITIVE
from provenance import element

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data" / "te_process_model.json"
OUT = ROOT / "out" / "scene" / "te_scene.json"
SCALE = 0.02  # model layout units -> metres (placeholder)
SIZE_M = {"reactor": [3.0, 6.0, 3.0], "separator": [2.5, 5.0, 2.5], "stripper": [2.0, 9.0, 2.0],
          "condenser": [4.0, 1.5, 1.5], "compressor": [2.5, 2.0, 2.0], "feed_header": [1.0, 1.0, 6.0]}


def sha256_text(path):
    """Hash with line endings normalised, so a Windows checkout and a Linux checkout agree."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build(model, source_hash):
    items = model["instruments"] + model["final_elements"]
    units = []
    for u in sorted(model["units"], key=lambda x: x["id"]):
        layout = u.get("layout") or {}
        tags = [{"tag": i["tag"], "description": i["description"], "uom": i["uom"],
                 "kind": "output (recorded %, not valve position)" if "xmv" in i else "measurement",
                 "stream": i.get("stream"), "provenance": element(i)}
                for i in sorted(items, key=lambda x: x["tag"]) if i["unit"] == u["id"]]
        units.append({"id": u["id"], "name": u["name"], "type": u["type"],
                      "position_m": [round(layout.get("x", 0) * SCALE, 2), 0.0, round(layout.get("y", 0) * SCALE, 2)],
                      "size_m": SIZE_M.get(u["type"], [2.0, 2.0, 2.0]),
                      "geometry": "placeholder", "provenance": element(u), "tags": tags})
    pipes = [{"stream": s["id"], "name": s["name"], "from": s["from"], "to": s["to"],
              "direction": s.get("direction", "as listed in the model (from -> to); not separately verified"),
              "route": "placeholder: straight run between unit positions",
              "tags_on_stream": sorted(i["tag"] for i in items if i.get("stream") == s["id"]),
              "provenance": element(s)}
             for s in model["streams"]]
    streams = {s["id"]: s for s in model["streams"]}
    loto = []
    for u in sorted(model["units"], key=lambda x: x["id"]):
        for fe in sorted(model["final_elements"], key=lambda x: x["tag"]):
            s = streams.get(fe.get("stream"))
            if s and u["id"] in (s["from"], s["to"]):
                loto.append({"unit": u["id"], "control_valve": fe["tag"], "stream": s["id"],
                             "isolation": NOT_POSITIVE + " (a control valve; which device isolates the stream is "
                                                         "not assessed)",
                             "valve_owner_in_model": fe["unit"], "inferred": True,
                             "basis": f"final element on stream {s['id']} ({s['from']} -> {s['to']}) in the model",
                             "provenance": element(fe)})
    return {
        "meta": {
            "kind": "proof_of_concept",
            "status": "built to iterate on; not a validated deliverable and not reviewed by operations",
            "generated_by": "scripts/build_scene_data.py",
            "source": "data/te_process_model.json",
            "source_sha256": source_hash,
            "inherits": "every element carries the provenance of the model item it came from; geometry adds none",
            "geometry": "positions are the model's 2D layout scaled to metres; sizes, elevations and routes are placeholders",
            "loto": MOCKUP_STATUS,
        },
        "units": units, "pipes": pipes, "loto_valve_crossings": loto,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    model_path = Path(argv[0]) if argv else MODEL
    out = Path(argv[1]) if len(argv) > 1 else OUT
    model = json.loads(model_path.read_text(encoding="utf-8"))
    scene = build(model, sha256_text(model_path))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scene, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT).as_posix() if out.is_relative_to(ROOT) else out}: "
          f"{len(scene['units'])} units, {len(scene['pipes'])} pipes, "
          f"{len(scene['loto_valve_crossings'])} control valves marked not positive isolation (proof of concept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
