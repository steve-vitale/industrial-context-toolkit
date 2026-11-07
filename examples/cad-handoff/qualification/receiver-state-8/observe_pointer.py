"""Exposed-input X11 pointer controls; no CAD entity API or save operation.

Coordinates require observation of this native desktop before running. Every frame
and command is retained. This script records observations, not a visual pass.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
import zlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-id", required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(exist_ok=False)
    events, rows = [], []

    def run(*cmd):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        events.append(dict(at=datetime.now(timezone.utc).isoformat(), command=list(cmd),
                           exit=r.returncode, stdout=r.stdout, stderr=r.stderr))
        if r.returncode:
            raise RuntimeError(f"Native input/capture failure: {cmd[0]}")
        return r.stdout

    def shot(name):
        time.sleep(2)
        last = None
        for n in range(10):
            path = args.out / f"{name}-frame-{n}.png"
            run("scrot", str(path))
            raw, pos, data = path.read_bytes(), 8, []
            while pos < len(raw):
                length = struct.unpack(">I", raw[pos:pos+4])[0]
                if raw[pos+4:pos+8] == b"IDAT":
                    data.append(raw[pos+8:pos+8+length])
                pos += length + 12
            pixel_hash = hashlib.sha256(zlib.decompress(b"".join(data))).hexdigest()
            events.append(dict(frame=path.name, filtered_image_sha256=pixel_hash))
            if pixel_hash == last:
                (args.out / f"{name}.png").write_bytes(raw)
                return
            last = pixel_hash
            time.sleep(.6)
        raise RuntimeError("Native image did not stabilize")

    def wait_title(title):
        for _ in range(40):
            if title in run("wmctrl", "-l"):
                return
            time.sleep(.2)
        shot("title-timeout")
        raise RuntimeError(f"Native title not observed: {title}")

    try:
        for name, source in (("source-1", args.source), ("source-2", args.source),
                             ("candidate", args.candidate)):
            before = source.read_bytes()
            row = dict(id=name, path=str(source), before_sha256=hashlib.sha256(before).hexdigest())
            rows.append(row)
            run("wmctrl", "-ia", args.window_id)
            run("wmctrl", "-ir", args.window_id, "-b", "remove,maximized_vert,maximized_horz")
            run("wmctrl", "-ir", args.window_id, "-e", "0,0,0,1120,900")
            run("xdotool", "key", "Escape", "Escape", "ctrl+o")
            wait_title("Open Drawing")
            run("xdotool", "mousemove", "500", "604", "click", "1", "key", "ctrl+a",
                "type", "--clearmodifiers", "--", str(source))
            run("xdotool", "key", "Tab", "Return")
            wait_title(source.name + " - QCAD")
            run("xdotool", "mousemove", "950", "168", "click", "--repeat", "2", "--delay", "100", "1", "key", "z", "a")
            run("xdotool", "mousemove", "950", "187", "click", "--repeat", "2", "--delay", "100", "1", "key", "z", "a")
            shot(name + "-initial")
            for stage, xy in (("ellipse-1", (630,455)), ("clear-1", (790,745)),
                              ("concave", (300,630)), ("clear-2", (790,745)),
                              ("ellipse-2", (630,455)), ("clear-3", (790,745))):
                run("xdotool", "mousemove", str(xy[0]), str(xy[1]))
                time.sleep(.5)
                if stage.startswith("clear"):
                    run("xdotool", "mousemove", "1090", "900")
                shot(name + "-" + stage)
            run("wmctrl", "-ia", args.window_id)
            run("xdotool", "key", "ctrl+w")
            row["after_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            if source.read_bytes() != before:
                raise RuntimeError("Viewing changed input bytes")
            row["completed"] = True
    finally:
        (args.out / "actions.json").write_text(json.dumps(events, indent=2)+"\n", encoding="utf-8")
        (args.out / "cases.json").write_text(json.dumps(rows, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
