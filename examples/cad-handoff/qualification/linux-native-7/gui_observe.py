"""Observed Linux X11 GUI recipe, not a QCAD document/edit/export API.

Run inside the isolated desktop after observing the file dialog and Block List.
Capture native model and declared paper views; exit on a GUI timeout, never restart.
Screenshots still require inspection and do not prove equivalence or readability.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=6)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=False)
    actions = []

    def run(*command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        actions.append(dict(at=datetime.now(timezone.utc).isoformat(), command=list(command),
                            exit=result.returncode, stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            raise RuntimeError(f"GUI command failed: {command[0]}: {result.stderr}")
        return result.stdout

    def shot(name):
        time.sleep(.6)  # allow native repaint, not an assertion of completion
        run("scrot", str(args.out / name))

    rows = json.loads(args.cases.read_text(encoding="utf-8"))[args.start:args.start + args.count]
    try:
        for row in rows:
            source = Path(row["path"])
            original = source.read_bytes()
            run("xdotool", "mousemove", "500", "9", "click", "1", "key", "Escape", "Escape", "ctrl+o")
            time.sleep(.3)
            run("xdotool", "key", "ctrl+a", "type", "--clearmodifiers", "--", str(source))
            run("xdotool", "key", "Tab", "Return")
            for _ in range(30):
                if source.name + " - QCAD" in run("wmctrl", "-l"):
                    break
                time.sleep(.2)
            else:
                shot(row["id"] + "-" + row["kind"] + "-TIMEOUT.png")
                raise RuntimeError("Native title did not confirm the requested file")
            # Block List coordinates and ZA shortcut observed in this desktop.
            run("xdotool", "mousemove", "950", "168", "click", "--repeat", "2", "--delay", "100", "1", "key", "z", "a")
            shot(row["id"] + "-" + row["kind"] + "-model.png")
            if row["paper"]:
                # Third Block List row is the declared named layout on these six cases.
                run("xdotool", "mousemove", "950", "205", "click", "--repeat", "2", "--delay", "100", "1", "key", "z", "a")
                shot(row["id"] + "-" + row["kind"] + "-paper.png")
            run("xdotool", "mousemove", "500", "9", "click", "1", "key", "ctrl+w")
            if source.read_bytes() != original:
                raise RuntimeError("Opening/viewing changed source bytes")
            row["sha256_after_view"] = hashlib.sha256(original).hexdigest()
            row["observation"] = "GUI commands/capture completed; inspect screenshots, no visual pass inferred"
    finally:
        (args.out / "actions.json").write_text(json.dumps(actions, indent=2) + "\n", encoding="utf-8")
        (args.out / "cases.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
