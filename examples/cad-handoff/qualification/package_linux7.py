"""Retain declared Linux GUI attempts, excluding CAD software, fonts, settings and session addresses."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import io


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    archive = args.out / "evidence.tar.xz"
    if archive.exists() or (args.out / "INVENTORY.json").exists():
        parser.error("Evidence exists; retain earlier archive")
    allowed = {".json", ".dxf", ".png", ".py", ".md", ".txt", ".log", ".tsv", ".stdout", ".stderr"}
    files = []
    for path in sorted(args.work.rglob("*")):
        relative = path.relative_to(args.work)
        if (not path.is_file() or any(p in {"qcad-config", "__pycache__"} for p in relative.parts)
                or path.name == "dbus-address.txt" or path.name.startswith(("~", "."))
                or path.suffix not in allowed):
            continue
        if path.is_symlink():
            raise ValueError("Do not package linked evidence")
        files.append(path)
    for name in ("MANUAL-ACTIONS.json", "ui-returned-default.dxf", "24-editability.json",
                 "paper-repeat-diagnostic.json", "infrastructure/terminal-inspect.stdout"):
        if args.work / name not in files:
            raise ValueError("Missing required observation: " + name)
    pins = {}
    with tarfile.open(archive, "w:xz", preset=6) as packed:
        for path in files:
            raw = path.read_bytes()
            name = "raw/" + path.relative_to(args.work).as_posix()
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(raw), 1794009600, 0o600
            packed.addfile(info, io.BytesIO(raw))
            pins[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    inventory = dict(schema="cad-linux-evidence-tar-xz-1", role="Retained native GUI observations and failed attempts; incomplete CAD qualification",
                     raw_bytes=sum(p["bytes"] for p in pins.values()), files=pins,
                     archive=dict(path=archive.name, bytes=archive.stat().st_size,
                                  sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                     exclusions=["CAD package/executable/font binaries", "QCAD settings", "DBus session address", "automatic backups/autosaves", "Python caches"],
                     packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest())
    (args.out / "INVENTORY.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(len(files), "exact records;", inventory["archive"]["bytes"], "archive bytes")


if __name__ == "__main__":
    main()
