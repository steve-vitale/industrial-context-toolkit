"""This public repository stays vendor-neutral: no tracked file (or member of a tracked zip archive) names the
owner's private products. The foundation's destination is described as "a maintained company tool" or "a governed
service", never as a specific company product. Stdlib only; uses `git ls-files` when available, otherwise walks the
checkout.

The forbidden names are stored base64-encoded and decoded at run time, so this test does not itself contain the words
it forbids (a plain-text copy here would make the check fail on its own source, and would put the names back into the
public tree).
"""
import base64
import io
import os
import re
import subprocess
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENCODED = ("Y2hhbmdlcGlsb3Q=", "ZGVsdGFtYXJr")
PATTERN = re.compile(b"|".join(re.escape(base64.b64decode(e)) for e in ENCODED), re.IGNORECASE)


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        return [ROOT / p for p in out.decode("utf-8").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", "out", "data/external", "__pycache__"}
        found = []
        for base, dirs, names in os.walk(ROOT):
            rel = Path(base).relative_to(ROOT).as_posix()
            dirs[:] = [d for d in dirs if d not in skip and f"{rel}/{d}".lstrip("./") not in skip]
            found += [Path(base) / n for n in names]
        return found


def offences(path):
    rel = path.relative_to(ROOT).as_posix()
    found = []
    if PATTERN.search(rel.encode("utf-8")):
        found.append(rel + " (file name)")
    try:
        data = path.read_bytes()
    except OSError:
        return found
    if PATTERN.search(data):
        found.append(rel)
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    if PATTERN.search(info.filename.encode("utf-8")) or PATTERN.search(archive.read(info)):
                        found.append(f"{rel}!{info.filename}")
        except zipfile.BadZipFile:
            pass
    return found


class VendorNeutral(unittest.TestCase):
    def test_pattern_matches_any_case(self):
        for encoded in ENCODED:
            word = base64.b64decode(encoded)
            for variant in (word, word.upper(), word.title(), b"see " + word + b".example.com"):
                self.assertTrue(PATTERN.search(variant))
        self.assertIsNone(PATTERN.search(b"a maintained company tool or a governed service"))

    def test_no_tracked_file_names_a_private_product(self):
        files = tracked_files()
        self.assertGreater(len(files), 100, "expected to scan the repository's tracked files")
        bad = [hit for path in files if path.is_file() for hit in offences(path)]
        self.assertEqual(bad, [], "use 'a maintained company tool' or 'a governed service' instead")


if __name__ == "__main__":
    unittest.main()
