"""Fetch one new public source group through the unchanged common pin-checking engine."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_corpus  # noqa: E402

REGISTRY = ROOT / "data/public_sources_20261107.json"


def register():
    """Register only for this opt-in process; historical matrix code remains unchanged."""
    sources = json.loads(REGISTRY.read_text(encoding="utf-8"))["sources"]
    fetch_corpus.FILE_SOURCES.update(sources)
    fetch_corpus.USER_AGENT = ("industrial-context-toolkit public-data acquisition "
                              "https://github.com/steve-vitale/industrial-context-toolkit")
    return sources


def main(argv=None):
    sources = register()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", choices=sorted(sources))
    ap.add_argument("--max-mb", type=float, default=125)
    args = ap.parse_args(argv)
    problems = fetch_corpus.validate_file_pins(fetch_corpus.load_pins(), sources)
    if problems:
        ap.error("; ".join(problems))
    dest = fetch_corpus.EXTERNAL / args.source
    receipt = fetch_corpus.fetch_pinned(args.source, args.max_mb, dest)
    (dest / "FETCH_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
