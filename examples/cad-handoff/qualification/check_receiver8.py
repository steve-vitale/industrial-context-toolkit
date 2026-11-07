"""Recompute exposed native pointer-state controls offline; no CAD/GUI run or qualification claim."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_linux7

require = check_linux7.require
read = check_linux7.read
BASE = HERE / "receiver-state-8"
STAGES = ("initial", "ellipse-1", "clear-1", "concave", "clear-2", "ellipse-2", "clear-3")
CASES = ("source-1", "source-2", "candidate")
CROP = (114, 176, 807, 787)


def pixels(path):
    with Image.open(path) as image:
        require(image.size == (1600, 1000), "Native desktop size differs")
        return image.convert("RGB").crop(CROP)


def difference(a, b):
    delta = ImageChops.difference(a, b)
    raw = delta.tobytes()
    return dict(different_pixels=sum(1 for r,g,b in zip(raw[0::3], raw[1::3], raw[2::3]) if r or g or b),
                bbox=list(delta.getbbox()) if delta.getbbox() else None)


def same(a, b):
    require(difference(a, b)["different_pixels"] == 0, "Native canvas states differ")


def observations(raw, freeze):
    rows = read(raw / "pointer-controls/cases.json")
    require([r["id"] for r in rows] == list(CASES), "Pointer cohort omitted/reordered")
    for row in rows:
        name = "text_in_viewports-" + ("candidate" if row["id"] == "candidate" else "source") + ".dxf"
        pin = freeze["inputs"]["raw/visual-inputs/" + name]
        require(row.get("completed") is True and row["before_sha256"] == row["after_sha256"] == pin["sha256"],
                "Native view input identity differs")
        data = (raw / name).read_bytes()
        require(len(data) == pin["bytes"] and hashlib.sha256(data).hexdigest() == pin["sha256"], "Changed input bytes")
    events = read(raw / "pointer-controls/actions.json")
    require(all(e["exit"] == 0 for e in events if "command" in e), "Failed native command")
    require(not any("ctrl+s" in str(e.get("command")) or "ctrl+shift+s" in str(e.get("command")) for e in events), "Unexpected save command")
    expected = [f"{case}-{stage}" for case in CASES for stage in STAGES]
    finals = sorted(p.stem for p in (raw / "pointer-controls").glob("*.png") if "-frame-" not in p.name)
    require(finals == sorted(expected), "Screenshot coverage differs")
    for name in expected:
        frames = sorted((raw / "pointer-controls").glob(name + "-frame-*.png"))
        require(2 <= len(frames) <= 10, "Stable frame observations omitted")
        # Compare full decoded RGB frames, not just their published hashes/crop.
        with Image.open(frames[-1]) as last, Image.open(frames[-2]) as previous:
            require(last.size == previous.size == (1600,1000), "Frame size differs")
            require(ImageChops.difference(last.convert("RGB"), previous.convert("RGB")).getbbox() is None,
                    "Last consecutive native frames differ")
        require((raw / "pointer-controls" / (name + ".png")).read_bytes() == frames[-1].read_bytes(), "Final screenshot differs")
        require(all(any(e.get("frame") == frame.name for e in events) for frame in frames), "Missing frame receipt")
    return rows


def normal_exit(state):
    require(state["Status"] == "exited" and state["Running"] is False and state["Pid"] == 0
            and state["ExitCode"] == 0 and state["OOMKilled"] is False and state["Error"] == "",
            "Native application did not exit normally")


def check():
    freeze = read(BASE / "FREEZE.json")
    require(hashlib.sha256((BASE / "observe_pointer.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == freeze["method_lf_sha256"], "Changed declared pointer method")
    require(read(HERE / "linux-native-7/INVENTORY.json")["archive"]["sha256"] == freeze["input_archive_sha256"], "Changed earlier evidence")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        raw = check_linux7.unpack(BASE, root / "new")
        old = check_linux7.unpack(HERE / "linux-native-7", root / "old")
        for public, captured in (("ellipse-hover.png", "source-1-ellipse-1.png"),
                                 ("pointer-neutral.png", "source-1-clear-1.png")):
            require((BASE / public).read_bytes() == (raw / "pointer-controls" / captured).read_bytes(),
                    "Published screenshot differs from retained native frame")
        require((raw / "observe_pointer.py").read_bytes() == (BASE / "observe_pointer.py").read_bytes().replace(b"\r\n", b"\n"), "Executed method differs")
        rows = observations(raw, freeze)
        state = read(raw / "terminal.json")
        normal_exit(state)
        setup = read(raw / "SETUP.json")
        require(setup["image"] == "sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8" and setup["plan_commit"] == "d627217" and setup["method_commit"] == "56ff36d", "Receiver/method identity differs")
        environment = read(BASE / "ENVIRONMENT.json")
        require(environment["Image"] == setup["image"] and environment["State"] == state,
                "Container image or terminal receipt differs")
        views = {(case,stage):pixels(raw / "pointer-controls" / f"{case}-{stage}.png") for case in CASES for stage in STAGES}
        clear = views["source-1", "clear-1"]
        old1 = pixels(old / "repeat-source-control/repeat-source-1-source-paper.png")
        old2 = pixels(old / "repeat-source-control/repeat-source-2-source-paper.png")
        for case in CASES:
            same(views[case,"initial"], old1)
            for stage in ("ellipse-1", "ellipse-2"):
                same(views[case,stage], old2)
            for stage in ("clear-1", "clear-2", "clear-3"):
                same(views[case,stage], clear)
            same(views[case,"concave"], views["source-1","concave"])
        old_diff = difference(old1, old2)
        observed = {stage:difference(clear, views["source-1",stage]) for stage in STAGES}
        require(old_diff["different_pixels"] == 13556 and observed["initial"]["different_pixels"] == 6788
                and observed["ellipse-1"]["different_pixels"] == 6768, "Earlier pointer discrepancy no longer reproduces")
        def refuses(fn):
            try:
                fn()
            except ValueError:
                return
            raise ValueError("Planted receiving error was admitted")
        controls = []
        # These in-memory negatives alter observations, never published screenshots.
        altered = clear.copy(); value = altered.getpixel((0,0)); altered.putpixel((0,0), ((value[0]+1)%256, value[1], value[2]))
        refuses(lambda:same(clear, altered)); controls.append("one_canvas_pixel_changed")
        refuses(lambda:same(clear, views["source-1","ellipse-1"])); controls.append("hover_state_substituted_for_clear")
        bad = copy.deepcopy(state); bad["ExitCode"] = 1
        refuses(lambda:normal_exit(bad)); controls.append("abnormal_receiver_exit")
        cases_path = raw / "pointer-controls/cases.json"; original = cases_path.read_bytes()
        for kind in ("omitted_case", "changed_input_identity"):
            bad_rows = copy.deepcopy(rows)
            if kind == "omitted_case": bad_rows.pop()
            else: bad_rows[0]["after_sha256"] = "0"*64
            cases_path.write_text(json.dumps(bad_rows), encoding="utf-8")
            try: refuses(lambda:observations(raw, freeze))
            finally: cases_path.write_bytes(original)
            controls.append(kind)
        result = dict(schema="cad-pointer-state-eight-replay-1", whole_cad_qualified=False,
            exposure="One already exposed public-adapted drawing; development, not fresh validation",
            native_paper_views=21, pointer_neutral_views=9, neutral_source_candidate_different_pixels=0,
            earlier_repeat_difference=old_diff, per_stage_difference_from_neutral=observed,
            receiving_refusals=controls, native_exit_code=state["ExitCode"],
            conclusion="The old two canvas states reproduce as pointer-highlight states; neutral traversal clears the discrepancy on these exact inputs",
            open_gates=["Complete readable layout/font acceptance", "Five original missing-main-viewport layout failures", "Native full-save preservation failures", "Fresh native validation", "Engineering/company acceptance"])
        expected = BASE / "summary.json"
        if expected.exists():
            require(read(expected) == result, "Published receiver-state summary differs from replay")
        return result


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
