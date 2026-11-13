"""Fetch one acquired public-source group's pinned files into data/external/<group>/ (gitignored), by hash.

  python scripts/fetch_public_group.py nestor-excavators [--max-mb 2]

The groups are the download groups of the acquisition registries (data/public_sources_*.json), pinned file by file in
data/corpus_pins.json. This registers only the named group with the unchanged pin-checking engine in
scripts/fetch_corpus.py for this process and fetches only what is missing or differs from its pin; a file already on
disk that matches its pin is not fetched again, so a re-run with everything present needs no network. Changed upstream
bytes are refused, never saved. Rights stay as recorded at acquisition: a group whose terms are unresolved is fetched
for local use only and none of its originals may be committed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_corpus  # noqa: E402

USER_AGENT = ("industrial-context-toolkit public-data acquisition "
              "https://github.com/steve-vitale/industrial-context-toolkit")


def groups(root=ROOT):
    """Group id -> acquisition record, across every acquisition registry."""
    out = {}
    for path in sorted((root / "data").glob("public_sources_*.json")):
        sources = json.loads(path.read_text(encoding="utf-8"))["sources"]
        for sid, record in sources.items():
            if record.get("kind") == "pinned-files":
                out[sid] = record
    return out


def fetch(sid, max_mb, dest=None, transport=None):
    known = groups()
    if sid not in known:
        raise SystemExit(f"unknown pinned-file group {sid!r}; known: {', '.join(sorted(known))}")
    fetch_corpus.FILE_SOURCES[sid] = known[sid]
    fetch_corpus.USER_AGENT = USER_AGENT
    problems = fetch_corpus.validate_file_pins(fetch_corpus.load_pins(), {sid: known[sid]})
    if problems:
        raise SystemExit("pin table malformed: " + "; ".join(problems))
    dest = Path(dest) if dest else fetch_corpus.EXTERNAL / sid
    dest.mkdir(parents=True, exist_ok=True)
    try:
        return fetch_corpus.fetch_pinned(sid, max_mb, dest, fetch=transport)
    except fetch_corpus.PinError as e:
        raise SystemExit(f"refused: {e}") from None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("group")
    ap.add_argument("--max-mb", type=float, default=125)
    a = ap.parse_args(argv)
    receipt = fetch(a.group, a.max_mb)
    print(json.dumps(receipt, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
