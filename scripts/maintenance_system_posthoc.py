"""Post-hoc figures for the Nestor system-grouping task (A420), added after the sealed held-out run at review.

Nothing here changes the frozen method or scorer (examples/maintenance-history/nestor/FREEZE.json). Two additions:

- `strict_rates`: precision and F1 with every record the key gives no system, but the answer gives a class, counted
  as a false positive. The frozen scorer leaves those records out of precision and reports their count separately.
- the key-free control: the same tool run (`maintenance_history.py` `derive`) with a vocabulary made only from the
  class names themselves, no development reading: each class's own name words, whole-word, "and" dropped, in the
  frozen vocabulary's rule order. It asks how much of the score a user could reach without reading any key. It is
  defined literally; plural forms or resolving the shared word HYDRAULIC give other values (reported in the README).

  python scripts/maintenance_system_posthoc.py --split development --out NEW_FILE.json   # the control's saved answer

Stdlib only; reads the local pinned originals through examples/maintenance-history/nestor.py.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples" / "maintenance-history"))
import maintenance_history as mh  # noqa: E402

VOCABULARY = ROOT / "examples/maintenance-history/nestor/system_vocabulary.json"
CONTROL = "key-free class-name words (post hoc)"


def strict_rates(entry, metric="orders"):
    """Rates with no-key records given a class counted as false positives (orders only; groups are unaffected)."""
    c = entry["counts"][metric]
    extra = entry.get("assigned_without_key_system", 0) if metric == "orders" else 0
    pred = c["predicted"] + extra
    return dict(precision=round(c["tp"] / pred, 4) if pred else None,
                recall=round(c["tp"] / c["truth"], 4) if c["truth"] else None,
                f1=round(2 * c["tp"] / (pred + c["truth"]), 4) if pred + c["truth"] else None)


def classname_rules(vocabulary=None):
    vocabulary = vocabulary or json.loads(VOCABULARY.read_bytes())
    rules = []
    for rule in vocabulary["rules"]:
        terms = [w for w in mh.words(rule["value"]).split() if w != "AND"]
        if terms:
            rules.append(dict(value=rule["value"], terms=terms))
    return rules


def keyfree_answer(split, source=None):
    """Record number -> class from the tool with the class-name vocabulary, on one split."""
    import nestor
    source = Path(source or ROOT / "data" / "external" / nestor.GROUP)
    with tempfile.TemporaryDirectory(prefix="keyfree-") as tmp:
        prof = nestor.profile(source, split, Path(tmp) / "profile")
        p = json.loads(prof.read_bytes())
        p["sources"]["work_orders"]["derive"]["work_class"].update(
            rules=classname_rules(), basis="Post-hoc key-free control: class-name words only; no development reading.")
        mh.dump(prof, p)
        result = mh.run(prof, Path(tmp) / "packet")
        return nestor.answer(result)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", required=True, choices=["development", "held-out"])
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    mh.require(not a.out.exists(), "Choose a new output file")
    assigned = keyfree_answer(a.split)
    a.out.write_text(json.dumps({"schema": "maintenance-system-answer-1",
                                 "produced_by": "python scripts/maintenance_system_posthoc.py --split " + a.split +
                                                " (" + CONTROL + "; scripts/maintenance_history.py derive)",
                                 "assigned": dict(sorted(assigned.items(), key=lambda kv: int(kv[0])))},
                                indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
