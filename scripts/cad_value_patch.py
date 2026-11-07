"""Propose single-line DXF attribute edits while retaining every other source byte.

Explicit ASCII-DXF ICT_ID/TAG profile only. This route does not import changes from a
native CAD return, resave geometry, qualify a CAD editor, or promote installed authority.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import cad_handoff as ch
from ezdxf.lldxf.encoding import decode_dxf_unicode, encode


def body(line):
    if line.endswith(b"\r\n"):
        return line[:-2]
    if line.endswith((b"\n", b"\r")):
        return line[:-1]
    return line


def source_tags(raw):
    """Ordered (code, raw value, value-body start/end), without decoding unrelated data."""
    if raw.startswith(b"AutoCAD Binary DXF") or b"\x00" in raw:
        raise ch.InputError("Binary DXF is outside this value-span route")
    lines = raw.splitlines(keepends=True)
    if len(lines) % 2:
        raise ch.InputError("DXF must contain complete group-code/value line pairs")
    tags, offset = [], 0
    for i in range(0, len(lines), 2):
        code = body(lines[i]).strip()
        if not re.fullmatch(rb"[0-9]{1,4}", code):
            raise ch.InputError("Non-ASCII or malformed group-code line")
        start = offset + len(lines[i])
        value = body(lines[i+1])
        tags.append((int(code), value, start, start+len(value)))
        offset = start + len(lines[i+1])
    if not tags or tags[-1][:2] != (0, b"EOF"):
        raise ch.InputError("A complete explicit DXF EOF record is required")
    return tags


def replacements(raw, doc, edits):
    tags = source_tags(raw)
    records, record = [], []
    for tag in tags:
        if tag[0] == 0 and record:
            records.append(record)
            record = []
        record.append(tag)
    if record:
        records.append(record)
    found = {}
    target_handles = {h.upper() for h in edits}
    for record in records:
        handles = [t[1].strip().decode("ascii", errors="strict").upper() for t in record if t[0] == 5]
        relevant = set(handles) & target_handles
        if not relevant:
            continue
        if len(handles) != 1 or len(relevant) != 1 or record[0][:2] != (0, b"ATTRIB"):
            raise ch.InputError("Target handle is not one unambiguous ATTRIB record")
        handle = handles[0]
        if handle in found:
            raise ch.InputError("Target handle occurs in more than one raw record")
        values = [t for t in record if t[0] == 1]
        names = [t[1] for t in record if t[0] == 2]
        if (len(values) != 1 or len(names) != 1 or any(t[0] in {3, 101} for t in record)
                or any(t[0] == 100 and t[1] == b"AcDbMText" for t in record)):
            raise ch.InputError("Multiline/ambiguous target serialization is unsupported")
        change = next(c for h, c in edits.items() if h.upper() == handle)
        if names[0].decode(doc.output_encoding) != change["attribute"]:
            raise ch.InputError("Raw attribute name disagrees with the inspected target")
        value = values[0]
        if decode_dxf_unicode(value[1].decode(doc.output_encoding)) != change["before"]:
            raise ch.InputError("Raw attribute value is not the declared before value")
        after = change["after"]
        if (any(ord(c) < 32 or ord(c) == 127 or c in "\x85\u2028\u2029" for c in after)
                or "\\P" in after or "\\X" in after):
            raise ch.InputError("Only plain single-line attribute values are supported")
        encoded = encode(after, doc.output_encoding)
        if (len(encoded) > 250 or decode_dxf_unicode(encoded.decode(doc.output_encoding)) != after):
            raise ch.InputError("Replacement does not round-trip as a bounded single-line value")
        found[handle] = {"handle": handle, "id": change["id"], "attribute": change["attribute"],
                         "source_start": value[2], "source_end": value[3],
                         "before_hex": value[1].hex(), "after_hex": encoded.hex()}
    if set(found) != target_handles:
        raise ch.InputError("Not every declared attribute has one unique raw value span")
    return sorted(found.values(), key=lambda v: v["source_start"])


def patch_bytes(raw, spans):
    chunks, cursor, shift = [], 0, 0
    for span in spans:
        start, end = span["source_start"], span["source_end"]
        before, after = bytes.fromhex(span["before_hex"]), bytes.fromhex(span["after_hex"])
        if start < cursor or raw[start:end] != before:
            raise ch.InputError("Invalid or overlapping value spans")
        chunks.extend([raw[cursor:start], after])
        span["candidate_start"] = start + shift
        span["candidate_end"] = start + shift + len(after)
        shift += len(after) - len(before)
        cursor = end
    chunks.append(raw[cursor:])
    candidate = b"".join(chunks)
    # Reconstruct the source from candidate using the declared edits, before publishing.
    restored = candidate
    for span in reversed(spans):
        a, b = span["candidate_start"], span["candidate_end"]
        if restored[a:b] != bytes.fromhex(span["after_hex"]):
            raise ch.InputError("Candidate value-span verification failed")
        restored = restored[:a] + bytes.fromhex(span["before_hex"]) + restored[b:]
    if restored != raw:
        raise ch.InputError("Bytes outside declared value spans changed")
    return candidate


def apply(source, plan, out):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ch.InputError("Output folder already exists; retain the earlier packet")
    raw = source.read_bytes()
    source_tags(raw)  # refuse binary/malformed streams before the library can repair them
    before = ch.snapshot(source)
    if hashlib.sha256(raw).hexdigest() != before["sha256"]:
        raise ch.InputError("Source changed during inspection")
    edits = ch.validate_plan(before, plan)
    spans = replacements(raw, ch.load(source), edits)
    candidate_bytes = patch_bytes(raw, spans)
    with tempfile.TemporaryDirectory(prefix="ict-cad-value-") as temporary:
        root = Path(temporary)
        retained = root / "retained.dxf"
        retained.write_bytes(raw)
        candidate = root / "candidate.dxf"
        candidate.write_bytes(candidate_bytes)
        after = ch.snapshot(candidate)
        report = ch.compare(before, after, plan)
        if report["unexpected"]:
            raise ch.InputError("Candidate changes more than the declared values; no packet emitted")
        packet = root / "packet"
        ch.write_packet(retained, before, packet)
        shutil.copyfile(candidate, packet / "candidate.dxf")
        ch.write_json(packet / "plan.json", plan)
        ch.write_json(packet / "comparison.json", report)
        ch.write_json(packet / "candidate.snapshot.json", after)
        ch.write_json(packet / "byte-edits.json", {"schema": "cad-value-spans-1", "spans": spans,
                      "source_sha256": before["sha256"], "candidate_sha256": after["sha256"],
                      "outside_spans": "identical bytes; source reconstruction passed",
                      "route": "source-preserving value edit; native-return changes are not imported",
                      "native_acceptance": "not established"})
        ch.write_packet(candidate, after, packet / "candidate-context")
        if ch.digest(source) != before["sha256"]:
            raise ch.InputError("Source changed during editing; proposal is stale")
        # copytree creates the destination exclusively, including against an empty-folder race.
        shutil.copytree(packet, out)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        report = apply(args.source, json.loads(Path(args.plan).read_text(encoding="utf-8-sig")), args.out)
        print(len(report["expected_edits"]), "proposed edits; zero unexpected strict differences; native acceptance open")
        return 0
    except (ch.InputError, OSError, ValueError, ch.ezdxf.DXFError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
