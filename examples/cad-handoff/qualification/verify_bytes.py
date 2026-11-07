"""Independently rebuild the expected DXF from the source and plan, ignoring patch receipts.

Uses a separate offset-free raw-line implementation, plus the existing source asset profile
and ezdxf encoding. This is a second software check by the same author, not human review.
"""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import cad_handoff as ch
from ezdxf.lldxf.encoding import encode


def verify(source, candidate, plan):
    source, candidate = Path(source), Path(candidate)
    before = ch.snapshot(source)
    edits = {k.upper(): v for k, v in ch.validate_plan(before, plan).items()}
    raw = source.read_bytes()
    # Unlike the patcher, this has no byte offsets and consumes none of its span/audit records.
    lines = [m.group(0) for m in re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", raw) if m.group(0)]
    if len(lines) % 2:
        raise ValueError("Incomplete source line pairs")
    groups, current = [], []
    for i in range(0, len(lines), 2):
        code = int(lines[i].strip())
        if code == 0 and current:
            groups.append(current)
            current = []
        current.append((i, code, lines[i+1].rstrip(b"\r\n")))
    groups.append(current)
    expected = list(lines)
    observed, encoding = set(), ch.load(source).output_encoding
    original_values = {}
    for group in groups:
        handles = [v.strip().decode("ascii").upper() for _, code, v in group if code == 5]
        targets = set(handles) & set(edits)
        if not targets:
            continue
        if len(handles) != 1 or group[0][1:] != (0, b"ATTRIB"):
            raise ValueError("Ambiguous target record")
        handle = handles[0]
        values = [(i, v) for i, code, v in group if code == 1]
        if len(values) != 1 or handle in observed:
            raise ValueError("Target value is not unique")
        i, value = values[0]
        after = edits[handle]["after"]
        if re.search(r"[\x00-\x1f\x7f\x85\u2028\u2029]|\\[PX]", after):
            raise ValueError("Plan is not a plain single-line attribute edit")
        oldline = lines[i+1]
        newline = oldline[len(value):]
        replacement = encode(after, encoding)
        if len(replacement) > 250:
            raise ValueError("Encoded target exceeds the declared value limit")
        expected[i+1] = replacement + newline
        original_values[i+1] = oldline
        observed.add(handle)
    if observed != set(edits):
        raise ValueError("Missing planned attribute")
    actual = candidate.read_bytes()
    if b"".join(expected) != actual:
        raise ValueError("Candidate differs from independent source-plus-plan reconstruction")
    for index, value in original_values.items():
        expected[index] = value
    if b"".join(expected) != raw:
        raise ValueError("Reverse source reconstruction failed")
    return {"status": "pass", "values": len(observed), "unplanned_byte_changes": 0,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "candidate_sha256": hashlib.sha256(actual).hexdigest(),
            "check": "independent source/plan reconstruction, no candidate span receipt consumed",
            "review": "same-author software check; not independent engineering review"}
