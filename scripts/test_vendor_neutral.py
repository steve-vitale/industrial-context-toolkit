"""This public repository stays vendor-neutral: no tracked file (or member of a tracked zip archive) names the
owner's private products. The foundation's destination is described as "a maintained company tool" or "a governed
service", never as a specific company product. Stdlib only; uses `git ls-files` when available, otherwise walks the
checkout.

The forbidden names are stored only as salted SHA-256 hashes. Every word in every file (letters and digits,
lowercased), and every pair of adjacent words joined together, is hashed and compared. The test never contains the
names in a readable or reversible form.
"""
import functools
import hashlib
import io
import os
import re
import subprocess
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SALT = b"industrial-context-toolkit/vendor-neutral/v1:"
FORBIDDEN = frozenset({
    "b6580af9a8e2ccf68a137c64ab821f3805bf5c3a10a6c1d6e2a5e3b26935cc53",
    "e4e46387ae162c5aa87ddc84d08fa2980c6d2d398e1760665e212780363e4914",
})
WORD = re.compile(rb"[a-z0-9]{2,24}")


@functools.lru_cache(maxsize=None)
def digest(word):
    return hashlib.sha256(SALT + word).hexdigest()


def names_forbidden(data, forbidden=FORBIDDEN):
    words = WORD.findall(data.lower())
    candidates = set(words)
    candidates.update(a + b for a, b in zip(words, words[1:]))
    return any(digest(w) in forbidden for w in candidates if 4 <= len(w) <= 24)


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
    if names_forbidden(rel.encode("utf-8")):
        found.append(rel + " (file name)")
    try:
        data = path.read_bytes()
    except OSError:
        return found
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return found  # PNG pixel data is compressed and carries no readable words
    if names_forbidden(data):
        found.append(rel)
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    if names_forbidden(info.filename.encode("utf-8")) or names_forbidden(archive.read(info)):
                        found.append(f"{rel}!{info.filename}")
        except zipfile.BadZipFile:
            pass
    return found


class VendorNeutral(unittest.TestCase):
    def test_matching_catches_case_punctuation_and_split_words(self):
        planted = frozenset({digest(b"examplecorp")})
        for text in (b"ExampleCorp", b"EXAMPLECORP's tool", b"see examplecorp.example.com", b"Example Corp"):
            self.assertTrue(names_forbidden(text, planted), text)
        self.assertFalse(names_forbidden(b"a maintained company tool or a governed service", planted))

    def test_no_tracked_file_names_a_private_product(self):
        files = tracked_files()
        self.assertGreater(len(files), 100, "expected to scan the repository's tracked files")
        bad = [hit for path in files if path.is_file() for hit in offences(path)]
        self.assertEqual(bad, [], "use 'a maintained company tool' or 'a governed service' instead")


if __name__ == "__main__":
    unittest.main()
