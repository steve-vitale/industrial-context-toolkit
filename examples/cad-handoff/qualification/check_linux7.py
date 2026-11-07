"""Replay retained Linux native GUI evidence offline; does not launch or re-run CAD."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import recheck
import correspondence5
import cad_value_patch
from verify_bytes import verify

require = recheck.require
read = recheck.read
ch = recheck.ch


def expected_attributes(source, plan):
    before = ch.snapshot(source)
    require(len(before["assets"]) == 1, "Expected the single exposed valve")
    values = copy.deepcopy(before["assets"][0]["attributes"])
    for change in plan["changes"]:
        values[change["attribute"]] = change["after"]
    return values


def labeled_fields(tree):
    result = {}
    def visit(node):
        children = node.get("children", [])
        if children and children[0].get("name") == "Attributes":
            for label, field in zip(children[1::2], children[2::2]):
                require(label["role"] == "label" and label["name"].endswith(":"), "Native attribute label missing")
                result[field["path"]] = label["name"][:-1]
        for child in children:
            visit(child)
    visit(tree)
    return result


def ui_values(rows, expected, labels):
    require(len(rows) == len(expected), "Native field observation omitted or added a field")
    require(set(labels.values()) == set(expected) and set(labels) == {r["path"] for r in rows}, "Native label binding differs")
    require(all(row["text"] == expected[labels[row["path"]]] for row in rows),
            "Native observed values differ from planned and unchanged source attributes")
    require(all(row["editable"] is True and row["enabled"] is True for row in rows),
            "Native fields are not all observed enabled/editable")


def view_coverage(rows, cases):
    require([(r["id"], r["kind"]) for r in rows] ==
            [(c["id"], kind) for c in cases for kind in ("source", "candidate")],
            "Native source/candidate view cohort omitted, duplicated or reordered")
    require(all("sha256_after_view" in row for row in rows), "Native view producer did not finish")


def check():
    from PIL import Image, ImageChops

    base = HERE / "linux-native-7"
    summary = read(base / "summary.json")
    recheck.method_bindings()
    environment = read(base / "ENVIRONMENT.json")
    for name, pin in environment["methods"].items():
        require(recheck.text_hash(base / name) == pin, "Native environment recipe changed: " + name)
    require(summary["whole_cad_qualified"] is False, "Partial GUI observation promoted to qualification")
    with tempfile.TemporaryDirectory(prefix="ict-linux-native-replay-") as temporary:
        root = Path(temporary)
        raw, _ = recheck.unpack(base, root / "unpacked")
        terminal = read(raw / "infrastructure/terminal-inspect.stdout")[0]["State"]
        require(terminal["Status"] == "exited" and terminal["Running"] is False and terminal["ExitCode"] == 0,
                "Final native process exit not retained")
        for name, member in summary["published_images"].items():
            require((base / name).read_bytes() == (raw / member).read_bytes(), "Published screenshot differs")
        source = raw / "original-valve.dxf"
        plan = read(raw / "edit-plan.json")
        returned = raw / "ui-returned-default.dxf"
        require(source.read_bytes() == (ROOT / "examples/cad-handoff/source/valve.dxf").read_bytes(),
                "GUI source differs from original exposed valve")
        require(plan == read(ROOT / "examples/cad-handoff/source/edit-plan.json"), "GUI plan changed")
        for name, path in (("source", source), ("returned", returned)):
            require(ch.digest(path) == summary[name + "_sha256"], "Native input/returned-file hash differs")
        before, after = ch.snapshot(source), ch.snapshot(returned)
        strict = ch.compare(before, after, plan)
        require(strict == read(raw / "ui-default-comparison.json"), "Native full-save comparison differs")
        require(len(strict["unexpected"]) == summary["native_full_save_strict_differences"] == 287,
                "Native full-save failure omitted or changed")
        diagnostic = correspondence5.audit(before, after, plan)
        require(diagnostic == read(raw / "ui-default-correspondence.json"), "Correspondence diagnostic changed")
        require(diagnostic["counts"] == summary["correspondence_counts"], "Correspondence totals changed")
        review = ch.review_data(before, after, strict, ch.load(source), ch.load(returned), plan)
        require(review == read(raw / "receiving-review/review.json"), "Receiving review does not reproduce")
        cad_value_patch.apply(source, plan, root / "candidate")
        candidate = root / "candidate/candidate.dxf"
        require(candidate.read_bytes() == (raw / "value-packet/candidate.dxf").read_bytes(), "Candidate differs")
        require(verify(source, candidate, plan) == summary["candidate_byte_check"], "Byte reconstruction differs")
        require(ch.compare(before, ch.snapshot(candidate), plan)["unexpected"] == [], "Candidate strict failure")
        expected = expected_attributes(source, plan)
        require(len(after["assets"]) == 1 and after["assets"][0]["attributes"] == expected, "Returned stored values differ")
        observed = read(raw / "24-editability.json")
        labels = labeled_fields(read(raw / "24-current-tree.json"))
        ui_values(observed, expected, labels)

        cases = recheck.cohort()
        manifest = read(raw / "cohort/MANIFEST.json")
        require([c["id"] for c in manifest["cases"]] == [c["id"] for c in cases], "Changed source cohort")
        for case in cases:
            retained = raw / "cohort" / case["id"]
            require((retained / "source.dxf").read_bytes() == case["source"].read_bytes(), "Changed cohort source")
            require(read(retained / "plan.json") == read(case["plan"]), "Changed cohort plan")
            cad_value_patch.apply(case["source"], read(case["plan"]), root / case["id"])
            proposed = root / case["id"] / "candidate.dxf"
            require(proposed.read_bytes() == (retained / "packet/candidate.dxf").read_bytes(), "Cohort candidate differs")
            verify(case["source"], proposed, read(case["plan"]))
        views, model_count, paper_count = [], 0, 0
        for folder in summary["valid_view_batches"]:
            view_root = raw / folder
            batch = read(view_root / "cases.json")
            views.extend(batch)
            actions = read(view_root / "actions.json")
            for row in batch:
                kind = "source.dxf" if row["kind"] == "source" else "packet/candidate.dxf"
                require(ch.digest(raw / "cohort" / row["id"] / kind) == row["sha256_after_view"], "Viewed input changed")
                require((raw / "visual-inputs" / Path(row["path"]).name).read_bytes() ==
                        (raw / "cohort" / row["id"] / kind).read_bytes(), "Actual GUI input differs from declared source/candidate")
                for view in ("model", "paper") if row["paper"] else ("model",):
                    name = row["id"] + "-" + row["kind"] + "-" + view
                    image = view_root / (name + ".png")
                    frames = [a for a in actions if a.get("frame", "").startswith(name + "-frame-")]
                    require(len(frames) >= 2 and frames[-1]["filtered_image_sha256"] == frames[-2]["filtered_image_sha256"],
                            "Native image data not recorded stable")
                    require(image.read_bytes() == (view_root / frames[-1]["frame"]).read_bytes(), "Published frame differs")
                    for frame in frames[-2:]:
                        # The original producer hashes decompressed PNG filtered rows.
                        import struct
                        import zlib
                        data, offset, chunks = (view_root / frame["frame"]).read_bytes(), 8, []
                        while offset < len(data):
                            size = struct.unpack(">I", data[offset:offset + 4])[0]
                            if data[offset + 4:offset + 8] == b"IDAT":
                                chunks.append(data[offset + 8:offset + 8 + size])
                            offset += size + 12
                        require(hashlib.sha256(zlib.decompress(b"".join(chunks))).hexdigest() == frame["filtered_image_sha256"],
                                "Recorded image data hash differs")
                    model_count += view == "model"
                    paper_count += view == "paper"
        view_coverage(views, cases)
        require((model_count, paper_count) == (42, 12), "View totals differ")
        left = Image.open(raw / "34-source-same-session.png").convert("RGB").crop((113, 175, 807, 780))
        right = Image.open(raw / "32-value-candidate-open.png").convert("RGB").crop((113, 175, 807, 780))
        delta = ImageChops.difference(left, right)
        pixels = sum(delta.getpixel((x, y)) != (0, 0, 0) for x in range(delta.width) for y in range(delta.height))
        require(list(delta.getbbox()) == summary["valve_canvas_delta"]["bbox"] and
                pixels == summary["valve_canvas_delta"]["changed_pixels"] == 425, "Native canvas diagnostic differs")
        repeat = read(raw / "repeat-source-control/cases.json")
        require(len(repeat) == 2 and repeat[0]["path"] == repeat[1]["path"] and
                repeat[0]["sha256_after_view"] == repeat[1]["sha256_after_view"] ==
                ch.digest(raw / "cohort/text_in_viewports/source.dxf"), "Same-original rendering control changed input")
        diagnostic = read(raw / "paper-repeat-diagnostic.json")
        for row in diagnostic["comparisons"]:
            a = Image.open(raw / row["before"]).convert("RGB").crop(diagnostic["crop"])
            b = Image.open(raw / row["after"]).convert("RGB").crop(diagnostic["crop"])
            diff = ImageChops.difference(a, b)
            bbox = diff.getbbox()
            require((list(bbox) if bbox else None) == row["bbox"] and
                    sum(diff.getpixel((x, y)) != (0, 0, 0) for x in range(diff.width) for y in range(diff.height)) == row["different_pixels"],
                    "Same-original rendering diagnostic differs")
        require([r["different_pixels"] for r in diagnostic["comparisons"]] == [13556, 13556, 0, 0, 13556, 13556],
                "Observed receiver-state difference no longer reproduces")

        # Semantic receiving controls run after integrity verification, not just ZIP bit flips.
        for index, mutation in enumerate(("planned value", "foreign value", "editability", "swapped fields")):
            bad = copy.deepcopy(observed)
            target = next(r for r in bad if r["text"] == ("SRC-3" if index != 1 else expected["VENDOR_NOTE"]))
            if index == 3:
                other = next(r for r in bad if r["text"] == "AV-88412")
                target["text"], other["text"] = other["text"], target["text"]
            elif index == 2:
                target["editable"] = False
            else:
                target["text"] = "SRC-2" if index == 0 else "silently lost foreign data"
            try:
                ui_values(bad, expected, labels)
            except ValueError:
                pass
            else:
                raise ValueError("Corrupted native observation accepted: " + mutation)
        try:
            view_coverage(views[:-1], cases)
        except ValueError:
            pass
        else:
            raise ValueError("Omitted source/candidate view accepted")
    print("PASS: exact native return/review/287 strict failures, 21 candidate rebuilds, 42 model/12 paper view records, 5 receiving controls")
    print("Retained observations reproduce; CAD GUI execution, complete label readability and engineering acceptance are not rerun or inferred")
    return summary


if __name__ == "__main__":
    check()
