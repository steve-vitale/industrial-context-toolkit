"""Control loops and signal relations for a drawing-set bundle: ISA-5.1 loop identity, roles, traced signal lines.

Round 6 increment 3 (docs/GOAL_ROUND6.md). scripts/import_drawing_set.py calls assemble() on the model it has built
(after the line layers) and writes the result to plant_model.json as `control_loops`. Nothing here calls a model.

The idea of assembling loops by grouping instruments on their ISA-5.1 loop number and then following the signal
lines, and chaining cascades from controller to controller, comes from the public pid-to-kg skill
(github.com/ScottDuncanAI/PID-to-Knowledge-Graph, MIT; measured against this repository in A409). This module is our
own code; it does not use or depend on that tool.

Three kinds of evidence, kept apart on every record:
  tag_grouping      two instruments share an ISA-5.1 loop identity: the same scope and loop number, a one-letter
                    suffix ignored (AIC 123A and AT 123 share loop 123). The scope is the tag's area prefix (10-FIC-101),
                    else the sheet's system code; with neither, the number is read plant-wide unless the same tag
                    appears on two sheets (two units reusing a number), and then each sheet is its own scope. Read from
                    the tags the reader wrote; it proposes membership and never asserts a relation by itself.
  traced_line       a drawn line joins the two symbols: a dashed signal line traced from the sheet image by
                    dashed_signal_lines(), or an instrument line of the bundle's line layer (scripts/line_layers.py)
                    with an instrument at both ends. A traced line ends at the first symbol box it reaches; a line end
                    in reach of two boxes attaches to neither and leaves its network unresolved.
  cross_sheet_flag  traced signal lines that end on two off-page connectors the bundle paired across sheets (every line
                    at either connector joins).

Roles come from the ISA-5.1 letters only (role_of): final element (letters ending in V), controller (C after the
first letter), transmitter or primary element (T or E), switch (S after the first letter), relay (Y), indicator
(I, R or A, with H, L or M levels, only). A relief valve (PSV, TSV, PRV, PSE) is a relief_device and a hand switch
(HS) a hand_switch: neither is a loop's final element or measurement. Letters out of ISA order (LVC) and a
plant-coded tag the reader did not read as ISA letters (build_twin.plant_coded) get no role.

What is asserted, and on what evidence:
  signal_to       a traced signal between two instruments whose roles are sender and next receiver (NEXT: a
                  measurement to a controller, a controller to a final element or relay, a relay to a final element),
                  from sender to receiver. A two-member dashed line whose roles skip a step or give no order keeps
                  direction "unknown"; a line between two items of one role other than two controllers (two
                  valves, two measurements, one item read twice) is not a signal; a solid instrument line, or a dashed one of fewer than min_dashes dashes, that
                  does so is a shared leader or a valve's own transmitter and is not read as a signal. A branching
                  network is resolved only when one sender reaches only next receivers (one transmitter feeding
                  controllers, one controller feeding final elements); otherwise it is listed as unresolved.
  controls        controller -> final element, only when the loop is confirmed: a traced signal into the
                  controller from a measurement and a traced signal out of it to that final element.
  sets_point_of   outer controller -> inner controller, when a traced signal joins two controllers and only one of
                  them is nearer a final element along traced controller-to-controller signals (the inner one), and
                  the would-be outer controller has no untraced final element of its own loop identity.
Tag grouping without a traced line is recorded on the loop as unconfirmed members, never as a relation. A traced
line that contradicts the tag grouping (a transmitter traced to another loop's controller) is kept as a conflict.
Nothing is taken from layout: no relation comes from where symbols sit, only from drawn lines and printed tags.
Confidence is an ordinal tier, not a calibrated probability: traced_and_grouped, traced, traced_cross_sheet, and
traced_direction_inferred for a cascade, whose direction comes from graph distance to a final element.
"""
import re
from pathlib import Path
from collections import defaultdict

SCHEMA = "control-loops-1"
# ISA-5.1 tag with an optional area prefix: "FIC 101", "FIC-101", "10-FIC-101", "U1 FT 101", "AIC 123A", "PT 4712.02"
LOOP_TAG = re.compile(r"^(?:(?P<area>[0-9][0-9A-Z]{0,5}|[A-Z]{1,3}[0-9]{1,4})[\s-]+)?"
                      r"(?P<letters>[A-Z]{1,6})[\s-]*(?P<number>[0-9]+(?:\.[0-9]+)?)(?P<suffix>[A-Z]?)$")
ROLES = ("controller", "final_element", "transmitter", "primary_element", "switch", "relay", "indicator",
         "relief_device", "hand_switch")
SENSORS = ("transmitter", "primary_element")
MEASUREMENTS = SENSORS + ("switch", "indicator")
CONFIDENCE = ("traced_and_grouped", "traced", "traced_cross_sheet", "traced_direction_inferred")
# Which role a signal may go to next: a measurement to a controller (or a transmitter to its indicator or switch), a
# controller to a final element or relay, a relay to a final element. Controller to controller is a cascade.
NEXT = {"transmitter": {"controller", "indicator", "switch"}, "primary_element": {"controller", "indicator", "switch"},
        "switch": {"controller"}, "indicator": {"controller"}, "controller": {"final_element", "relay"},
        "relay": {"final_element"}}

# Dashed-line tracer settings, all relative to the median symbol side on the sheet (as trace_connections.py).
DASH = {
    "line_frac": 0.6,      # a straight run at least this long is a solid line, not a dash (trace_connections line_frac)
    "max_gap_frac": 0.3,   # the largest gap bridged between two dashes, or a dash and a symbol box
    "max_width_frac": 0.12,  # a dash is a stroke no thicker than this (min 3 px)
    "min_dash_frac": 0.08,   # ...and at least this long (min 3 px)
    "min_dashes": 3,         # a signal line has at least this many dashes
    "guard_px": 2,           # symbol boxes are erased this far beyond their edge
}


# ---------------------------------------------------------------- tags and roles

def loop_identity(tag):
    """(area, number, suffix, letters) for an ISA-5.1 instrument tag, or None. The loop identity is (area, number)."""
    if not tag:
        return None
    m = LOOP_TAG.match(" ".join(str(tag).upper().split()).strip(" -"))
    if not m:
        return None
    return m.group("area") or "", m.group("number"), m.group("suffix") or "", m.group("letters")


def letters_out_of_order(letters):
    """True when the letters do not read in ISA-5.1 order: a valve letter V anywhere but last (LVC)."""
    return bool(letters) and "V" in letters[1:-1]


def role_of(letters):
    """The loop role ISA-5.1 letters give, or None. The first letter is the measured variable; the rest decide.
    A relief valve (PSV, TSV, PRV, a rupture disc PSE) is a relief_device and a hand switch (HS) a hand_switch: neither
    is a loop's final element or measurement. Letters out of ISA order (LVC) get no role."""
    if not letters or letters_out_of_order(letters):
        return None
    rest = letters[1:]
    if letters.endswith(("SV", "RV", "SE")):
        return "relief_device"
    if letters[0] == "H" and rest.startswith("S"):
        return "hand_switch"
    if letters.endswith("V"):
        return "final_element"
    if "C" in rest:
        return "controller"
    if "T" in rest:
        return "transmitter"
    if "E" in rest:
        return "primary_element"
    if "S" in rest:
        return "switch"
    if "Y" in rest:
        return "relay"
    if set(rest) - set("HLM") and set(rest) - set("HLM") <= set("IRA"):  # H, L, M: alarm or switch levels
        return "indicator"
    return None


def candidates(model):
    """{asset id: record} for the items whose tag reads as an ISA-5.1 instrument tag with a loop role: instruments,
    and tagged in-line items (a control valve the reader drew as a valve). A plant-coded tag (build_twin.py read its
    leading letters as a system code) is listed with no role."""
    codes = {sy.get("id"): sy.get("system_code") for sy in model.get("systems", [])}
    out = {}
    for key in ("instruments", "line_items"):
        for it in model.get(key, []):
            ident = loop_identity(it.get("tag"))
            if not ident:
                continue
            area, number, suffix, letters = ident
            plant_coded = str(it.get("variable_method") or "").startswith("none: plant tag") or \
                it.get("instrument_kind") == "operated valve"
            role = None if plant_coded else role_of(letters)
            if key == "line_items" and role != "final_element":
                continue
            sheets = sorted({str(p["sheet"]) for p in it.get("provenance", [])}, key=lambda x: (len(x), x))
            scope = area or codes.get(it.get("system")) or ""
            out[it["id"]] = {"id": it["id"], "tag": it["tag"], "letters": letters, "area": area, "number": number,
                             "suffix": suffix, "scope": scope, "role": role, "sheets": sheets,
                             **({"no_role": "plant-coded tag: its letters are a system code, not ISA-5.1"}
                                if plant_coded else {}),
                             **({"letters_not_isa_order": True} if letters_out_of_order(letters) else {})}
    # A loop number with no area prefix or system code is read plant-wide, unless the same tag appears on two sheets:
    # then the number is reused by two units, and each sheet is its own scope.
    groups = defaultdict(list)
    for c in out.values():
        groups[(c["scope"], c["number"])].append(c)
    for (scope, _), cs in groups.items():
        tags = [compact(c["tag"]) for c in cs]
        if not scope and len(set(tags)) < len(tags):
            for c in cs:
                c["scope"] = f"S{c['sheets'][0]}" if c["sheets"] else ""
    for c in out.values():
        c["loop_identity"] = f"{c['scope']}-{c['number']}" if c["scope"] else c["number"]
    return out



# ---------------------------------------------------------------- dashed signal lines from the image

def dashed_signal_lines(image_path, symbols, debug=None, **opt):
    """Signal lines between symbols on one sheet, traced from the image. symbols: [{id, box (0-1000), class}].
    Returns {"lines": [{"members": [symbol ids], "dashes": n, "box_0_1000": [...]}], "side_px", "settings"}.

    1. Every symbol box is erased (a line ends at a symbol), then every straight run at least line_frac of a symbol
       side long is removed: solid lines, so a dashed line crossing a pipe is not joined to it.
    2. What is left is split into pieces. A dash is a thin straight stroke; a thin corner piece is two arms already
       joined. Anything else (text, a crossing where two dashes overlap, arrowheads) is not a dash.
    3. Dashes on one axis whose facing ends are within max_gap_frac of a symbol side, offset no more than a stroke
       width, form one straight run. Where other ink lies in the gap (a solid line crossing, or the piece two dashes
       make where dashed lines cross) the gap may be twice that, so a run keeps going straight through a crossing.
    4. Runs join only where one ENDS: a corner (two runs ending at one point) or a tee (a run ending on the side of
       another). Two runs that both pass through the meeting point cross and are not joined, as line_layers.py treats
       an unmarked crossing.
    5. A network of runs with min_dashes dashes or more is a signal line; it joins the symbols its free run ends point
       at, within the gap of the box edge. A run end at a symbol box is terminal and is never joined to another run in
       step 4, so a controller's input and output stay two lines. An end in reach of two boxes attaches to neither:
       the line lists the boxes under ambiguous_ends instead. A shorter one counts only between two instrument bubbles (a signal drawn
       across the short gap between two stacked controllers). Text strokes can look like dashes; a network is kept
       only where it reaches two symbols."""
    import cv2
    import numpy as np
    import trace_connections as tc
    o = {**DASH, **opt}
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise FileNotFoundError(image_path)
    H, W = gray.shape
    ink = tc.binarize(gray)
    boxes, cls = {}, {}
    for s in symbols:
        b = tc.symbol_box(s)
        if b is None:
            continue
        x0, y0 = int(np.floor(b[0] / 1000 * W)), int(np.floor(b[1] / 1000 * H))
        x1, y1 = int(np.ceil(b[2] / 1000 * W)), int(np.ceil(b[3] / 1000 * H))
        if x1 > x0 and y1 > y0:
            boxes[str(s["id"])] = (max(0, x0), max(0, y0), min(W - 1, x1), min(H - 1, y1))
            cls[str(s["id"])] = s.get("class")
    if len(boxes) < 2:
        return {"lines": [], "side_px": None, "settings": o}
    side = float(np.median([min(b[2] - b[0], b[3] - b[1]) for b in boxes.values()]))
    g = o["guard_px"]
    for x0, y0, x1, y1 in boxes.values():
        ink[max(0, y0 - g):y1 + g + 1, max(0, x0 - g):x1 + g + 1] = 0
    L = max(5, int(round(o["line_frac"] * side)))
    solid = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (L, 1))) | \
        cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, L)))
    solid = cv2.dilate(solid, np.ones((3, 3), np.uint8))
    res = ink & (1 - solid)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(res, connectivity=8)
    tmax = max(3, int(round(o["max_width_frac"] * side)))
    dmin = max(3, int(round(o["min_dash_frac"] * side)))
    gap = max(3, int(round(o["max_gap_frac"] * side)))
    strokes = []  # (axis, across, lo, hi, piece) on the pixel grid
    corner_pairs = []  # (h stroke, v stroke, which end of the h arm is the vertex, which end of the v arm)
    npieces = 0
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[i])
        x1, y1 = x + w - 1, y + h - 1
        if max(w, h) < dmin or max(w, h) >= L:
            continue
        if min(w, h) <= tmax:
            if area < 0.5 * max(w, h):
                continue
            strokes.append(("h", (y + y1) / 2, x, x1, npieces) if w >= h else ("v", (x + x1) / 2, y, y1, npieces))
            npieces += 1
            continue
        if area > 1.5 * tmax * (w + h):
            continue
        sub = lab[y:y1 + 1, x:x1 + 1] == i
        k = tmax
        corners = {(0, 0): sub[:k, :k].sum(), (1, 0): sub[:k, -k:].sum(), (0, 1): sub[-k:, :k].sum(),
                   (1, 1): sub[-k:, -k:].sum()}
        (cx, cy), _ = max(sorted(corners.items()), key=lambda kv: kv[1])
        band_h = np.zeros_like(sub)
        band_h[(h - k if cy else 0):(h if cy else k), :] = True
        band_v = np.zeros_like(sub)
        band_v[:, (w - k if cx else 0):(w if cx else k)] = True
        arm_h, arm_v = sub & band_h, sub & band_v
        if arm_h.any(axis=0).sum() < 0.8 * w or arm_v.any(axis=1).sum() < 0.8 * h or (sub & ~(band_h | band_v)).any():
            continue  # ink off the two arms: not a corner (a crossing, a tee, a letter)
        hy = float(np.nonzero(arm_h.any(axis=1))[0].mean() + y)
        vx = float(np.nonzero(arm_v.any(axis=0))[0].mean() + x)
        strokes.append(("h", hy, x, x1, npieces))
        strokes.append(("v", vx, y, y1, npieces))
        corner_pairs.append((len(strokes) - 2, len(strokes) - 1, "hi" if cx else "lo", "hi" if cy else "lo"))
        npieces += 1
    parent = list(range(len(strokes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    by_axis = defaultdict(list)
    for si, st in enumerate(strokes):
        by_axis[st[0]].append(si)
    for ax, ids in by_axis.items():  # 3. straight runs
        ids.sort(key=lambda si: (strokes[si][2], strokes[si][1]))
        for a_i, si in enumerate(ids):
            _, c, lo, hi, _ = strokes[si]
            best = None
            for sj in ids[a_i + 1:]:
                _, c2, lo2, hi2, _ = strokes[sj]
                if lo2 - hi > 2 * gap + 1:
                    break
                if abs(c2 - c) <= tmax and lo2 > hi and (best is None or lo2 < strokes[best][2]):
                    best = sj
            if best is None:
                continue
            nxt = strokes[best][2]
            d = nxt - hi
            if d > gap + 1:  # a wider gap only where another line crosses it
                crossed = _ink_between(solid | res, ax, c, hi, nxt) or any(
                    st[0] != ax and st[2] - tmax <= c <= st[3] + tmax and hi < st[1] < nxt for st in strokes)
                if not crossed:
                    continue
            parent[find(si)] = find(best)
    run_info = {}
    for si in range(len(strokes)):
        r = find(si)
        ri = run_info.setdefault(r, {"axis": strokes[si][0], "cs": [], "lo": strokes[si][2], "hi": strokes[si][3],
                                     "pieces": set()})
        ri["cs"].append(strokes[si][1])
        ri["lo"], ri["hi"] = min(ri["lo"], strokes[si][2]), max(ri["hi"], strokes[si][3])
        ri["pieces"].add(strokes[si][4])
    for ri in run_info.values():
        ri["c"] = sum(ri["cs"]) / len(ri["cs"])
    net = {r: r for r in run_info}

    def nfind(a):
        while net[a] != a:
            net[a] = net[net[a]]
            a = net[a]
        return a

    def end_pt(r, e):
        ri = run_info[r]
        p = ri["lo"] if e == "lo" else ri["hi"]
        return (p, ri["c"]) if ri["axis"] == "h" else (ri["c"], p)
    used = set()  # (run, "lo" | "hi"): a run end that meets another run
    reach = gap + g

    def boxes_at(r, e):
        """The symbol boxes a run end points into, within reach of the box edge."""
        ri, sg = run_info[r], (-1 if e == "lo" else 1)
        ex, ey = end_pt(r, e)
        out = []
        for sid, (x0, y0, x1, y1) in boxes.items():
            if ri["axis"] == "h":
                d = ((x0 if sg > 0 else x1) - ex) * sg
                across = y0 - tmax <= ey <= y1 + tmax
            else:
                d = ((y0 if sg > 0 else y1) - ey) * sg
                across = x0 - tmax <= ex <= x1 + tmax
            if -tmax <= d <= reach and across:
                out.append(sid)
        return sorted(out)
    # An end at a symbol box is terminal: a line ends at the symbol, so it is never joined to another line there (two
    # lines meeting at one bubble, its input and its output, stay two lines).
    terminal = {(r, e): boxes_at(r, e) for r in run_info for e in ("lo", "hi")}
    terminal = {k: v for k, v in terminal.items() if v}
    for hs, vs, he, ve in corner_pairs:  # 4. corners drawn as one piece
        a, b = find(hs), find(vs)
        ends = [(run, e) for run, stroke, e in ((a, hs, he), (b, vs, ve))
                if strokes[stroke][2 if e == "lo" else 3] == run_info[run][e]]
        if not ends:  # both runs carry on past the piece: two lines crossing, not joined
            continue
        net[nfind(a)] = nfind(b)
        used.update(ends)  # a run that carries on past the vertex meets the other at a tee, its ends stay free
    rl = sorted(run_info)
    for r in rl:  # corners and tees across a gap
        ri = run_info[r]
        for e, sg in (("lo", -1), ("hi", 1)):
            if (r, e) in used or (r, e) in terminal:
                continue
            ex, ey = end_pt(r, e)
            at = ey if ri["axis"] == "h" else ex
            for q in rl:
                qi = run_info[q]
                if q == r or qi["axis"] == ri["axis"]:
                    continue
                d = ((qi["c"] - ex) if ri["axis"] == "h" else (qi["c"] - ey)) * sg
                if not (-tmax <= d <= gap + tmax and qi["lo"] - gap <= at <= qi["hi"] + gap):
                    continue
                qe = min(("lo", "hi"), key=lambda k: abs(at - qi[k]))
                corner = abs(at - qi[qe]) <= gap + tmax
                if corner and (q, qe) in terminal:
                    continue  # q ends at a symbol here: no corner through a symbol
                net[nfind(r)] = nfind(q)
                used.add((r, e))
                if corner:  # q ends here too
                    used.add((q, qe))
                break
    networks = defaultdict(list)
    for r in run_info:
        networks[nfind(r)].append(r)
    if debug is not None:
        debug.update(strokes=strokes, runs=run_info, networks=dict(networks), used=used, boxes=boxes)
    lines = []
    for rs in networks.values():  # 5. what each network reaches; an end in reach of two boxes attaches to neither
        pieces = set().union(*(run_info[r]["pieces"] for r in rs))
        hit, ambiguous = set(), []
        for r in rs:
            for e in ("lo", "hi"):
                if (r, e) in used or (r, e) not in terminal:
                    continue
                at = terminal[(r, e)]
                if len(at) == 1:
                    hit.add(at[0])
                elif at not in ambiguous:
                    ambiguous.append(at)
        if len(hit) + len(ambiguous) < 2:
            continue
        if not ambiguous and len(pieces) < o["min_dashes"] and \
                not (len(hit) == 2 and all(cls.get(m) == "instrumentation" for m in hit)):
            continue
        pts = [p for r in rs for p in (end_pt(r, "lo"), end_pt(r, "hi"))]
        x0, x1 = min(p[0] for p in pts) - tmax / 2, max(p[0] for p in pts) + tmax / 2  # a line has a stroke width
        y0, y1 = min(p[1] for p in pts) - tmax / 2, max(p[1] for p in pts) + tmax / 2
        lines.append({"members": sorted(hit), "dashes": len(pieces),
                      **({"ambiguous_ends": sorted(ambiguous)} if ambiguous else {}),
                      "box_0_1000": [round(max(0.0, 1000 * x0 / W), 1), round(max(0.0, 1000 * y0 / H), 1),
                                     round(min(1000.0, 1000 * x1 / W), 1), round(min(1000.0, 1000 * y1 / H), 1)]})
    lines.sort(key=lambda x: (x["members"], x["box_0_1000"]))
    return {"lines": lines, "side_px": round(side, 1), "settings": o}


def _ink_between(ink, ax, c, a, b):
    """True when other ink (a solid line, or two dashes overlapping where lines cross) lies in the gap between a and b
    on a run at `c`."""
    c = int(round(c))
    seg = ink[c, a + 1:b] if ax == "h" else ink[a + 1:b, c]
    return bool(seg.any())


# ---------------------------------------------------------------- signal lines and networks in a bundle

def sheet_signal_lines(model, source):
    """[{id, sheet, line_kind, members (asset ids), ...}] for every traced signal line in the bundle: dashed lines
    traced from each sheet image (dashed_signal_lines, line_kind dashed_signal_line), and the line layer's instrument
    lines with an instrument at both ends, joined only through instrument line junctions, never through a pipe tap
    (line_kind instrument_line)."""
    import line_layers as ll
    syms = ll._sheet_symbols(model)
    out = []
    for sheet in sorted(syms, key=lambda s: (len(s), s)):
        r = dashed_signal_lines(Path(source) / f"{sheet}.png",
                                [{"id": k, "box": v["box"], "class": v["class"]} for k, v in syms[sheet].items()])
        for line in r["lines"]:
            members = sorted({syms[sheet][m]["asset"] for m in line["members"]})
            ambiguous = [sorted({syms[sheet][m]["asset"] for m in a}) for a in line.get("ambiguous_ends", [])]
            if len(members) >= 2 or ambiguous:  # an ambiguous end is kept so its network is listed unresolved
                out.append({"sheet": sheet, "line_kind": "dashed_signal_line", "members": members,
                            "box_0_1000": line["box_0_1000"], "dashes": line["dashes"],
                            **({"ambiguous_ends": ambiguous} if ambiguous else {})})
    layers = model.get("line_layers") or {}
    inst = {i["id"] for i in model.get("instruments", [])}
    joins = {j["id"] for j in layers.get("junctions", []) if j.get("junction_kind") == "instrument_line_junction"}
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    kept = [il for il in layers.get("instrument_lines", [])
            if all(e in inst or e in joins for e in (il["from"], il["to"]))]
    for il in kept:
        parent[find(il["from"])] = find(il["to"])
    groups = defaultdict(lambda: {"members": set(), "lines": [], "sheet": None})
    for il in kept:
        g = groups[find(il["from"])]
        g["members"] |= {e for e in (il["from"], il["to"]) if e in inst}
        g["lines"].append(il["id"])
        g["sheet"] = il["sheet"]
    for g in groups.values():
        if len(g["members"]) >= 2:
            out.append({"sheet": g["sheet"], "line_kind": "instrument_line", "members": sorted(g["members"]),
                        "lines": sorted(g["lines"])})
    out.sort(key=lambda x: (len(x["sheet"]), x["sheet"], x["members"], x["line_kind"]))
    for n, x in enumerate(out, 1):
        x["id"] = f"S{x['sheet']}-SL{n:03d}"
    return [{"id": x.pop("id"), **x} for x in out]


RANK = {"transmitter": 0, "primary_element": 0, "switch": 1, "indicator": 1, "controller": 2, "relay": 3,
        "final_element": 4}


def compact(text):
    return re.sub(r"[\s\-_]", "", str(text or "")).upper()


def signal_networks(model, lines):
    """Traced signal lines as networks: each line alone, except that lines ending on two off-page connectors the
    bundle paired across sheets are joined (a signal continued on another sheet). Returns [{members (item ids, connectors left out),
    lines, flags}]. A flag records the pair used and where a connector's printed text names an instrument the joined
    lines reach ("TO FIC 104"): corroboration, never a link by itself."""
    conn = {c["id"]: c for c in model.get("offpage_connectors", [])}
    tag = {it["id"]: it.get("tag") for key in ("instruments", "line_items", "units") for it in model.get(key, [])}
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for x in lines:  # an instrument ends a line: two lines at one bubble are two signals, never one network
        find(("line", x["id"]))
    used = []
    for p in model.get("offpage_pairs", []):
        here = [x for x in lines if p["a"] in x["members"]]
        there = [x for x in lines if p["b"] in x["members"]]
        if here and there:  # every line at either connector joins: a branch there is resolved by roles, or not at all
            for x in here + there:
                parent[find(("line", x["id"]))] = find(("line", here[0]["id"]))
            used.append(p)
    nets = defaultdict(lambda: {"lines": [], "flags": []})
    for x in lines:
        nets[find(("line", x["id"]))]["lines"].append(x)
    for p in used:
        nets[find(("line", next(x for x in lines if p["a"] in x["members"])["id"]))]["flags"].append(p)
    out = []
    for net in nets.values():
        members = sorted({m for x in net["lines"] for m in x["members"] if m not in conn})
        flags = []
        for p in net["flags"]:
            names = [{"connector": cid, "names": tag[m]} for cid in (p["a"], p["b"]) for m in members
                     if tag.get(m) and re.search(r"(?:TO|FROM)" + re.escape(compact(tag[m])) + r"$",
                                                 compact(conn[cid].get("text")))]
            flags.append({"kind": "cross_sheet_flag", "pair": p["id"], "connectors": [p["a"], p["b"]],
                          "sheets": [p["sheet_a"], p["sheet_b"]], "texts": [p.get("text_a"), p.get("text_b")],
                          "pair_method": p.get("method"),
                          "pair_status": (p.get("verification") or {}).get("status"),
                          "text_names_reached_instrument": names})
        out.append({"members": members, "lines": net["lines"], "flags": flags})
    return out


def _line_evidence(lines):
    return [{"kind": "traced_line", "line": x["id"], "line_kind": x["line_kind"], "sheet": x["sheet"],
             **({"box_0_1000": x["box_0_1000"], "dashes": x["dashes"]} if "box_0_1000" in x else {}),
             **({"instrument_lines": x["lines"]} if "lines" in x else {})} for x in lines]


def _directed_links(nets, cand, role):
    """[(from, to, directed, evidence)] and the unresolved networks, from the roles alone (module docstring)."""
    links, unresolved = [], []
    for net in nets:
        ms = [m for m in net["members"] if m in cand]
        evidence = _line_evidence(net["lines"]) + net["flags"]
        ambiguous = [a for x in net["lines"] for a in x.get("ambiguous_ends", [])]
        if ambiguous:
            unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                               "ambiguous_ends": ambiguous,
                               "why": "a line end in reach of two or more symbols; which one it reaches is not read, "
                                      "so no signal_to is asserted on this network"})
            continue
        if len(ms) < 2:
            continue
        ranks = {m: RANK.get(role[m]) for m in ms}
        if all(r is None for r in ranks.values()):
            unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                               "why": "no item on this line has a loop role (plant-coded valves, relief devices, hand "
                                      "switches); not read as a signal"})
            continue
        weak = all(x["line_kind"] == "instrument_line" or x.get("dashes", 0) < DASH["min_dashes"]
                   for x in net["lines"])
        if weak and not any(role[m] in ("controller", "relay", "final_element") for m in ms):
            unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                               "why": "a solid or very short line joining measuring instruments only (a shared "
                                      "leader or impulse line, as redundant transmitters are drawn); not read as a "
                                      "signal"})
            continue
        if len(ms) == 2:
            a, b = ms if (ranks[ms[0]] or 0) <= (ranks[ms[1]] or 0) else ms[::-1]
            if role[b] in NEXT.get(role[a], ()) and ranks[a] != ranks[b]:
                links.append({"from": a, "to": b, "directed": True, "evidence": evidence})
            elif role[a] == role[b] != "controller" or ranks[a] == ranks[b] != RANK["controller"]:
                unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                                   "why": "a line between two items of one role (two valves, two measurements, or "
                                          "one item read twice): neither signals the other; not read as a signal"})
            elif weak and not role[a] == role[b] == "controller":  # two controllers: a cascade, ordered below
                unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                                   "why": "a solid or very short line whose roles are not sender and next receiver "
                                          "(a position transmitter on its valve, say); not read as a signal"})
            else:
                links.append({"from": ms[0], "to": ms[1], "directed": False, "evidence": evidence})
            continue
        low = min((r for r in ranks.values() if r is not None), default=None)
        senders = [m for m in ms if ranks[m] == low]
        if low is None or len(senders) != 1 or any(role[m] not in NEXT.get(role[senders[0]], ())
                                                   for m in ms if m != senders[0]):
            unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                               "why": "a branching signal line whose roles leave no single sender, or whose sender "
                                      "would skip a role (a transmitter straight to a valve); no signal_to is "
                                      "asserted between its members"})
            continue
        links += [{"from": senders[0], "to": m, "directed": True, "evidence": evidence} for m in ms if m != senders[0]]
    return links, unresolved


def _cascades(links, role, untraced_finals=None):
    """Direct controller-to-controller links outer -> inner: the inner controller is nearer a final element along
    traced controller-to-controller links. Equal or unknown distance leaves the link undirected, and so does a would-be
    outer controller that has a final element of its own loop identity no traced line reaches (it may be the inner
    one, with its output simply not traced). A direction found this way is inferred from graph distance, so its
    relations carry the tier traced_direction_inferred."""
    depth = {lk["from"]: 0 for lk in links if lk["directed"] and role.get(lk["from"]) == "controller"
             and role.get(lk["to"]) in ("final_element", "relay")}
    cc = [lk for lk in links if role.get(lk["from"]) == role.get(lk["to"]) == "controller"]
    changed = True
    while changed:
        changed = False
        for lk in cc:
            for x, y in ((lk["from"], lk["to"]), (lk["to"], lk["from"])):
                if y in depth and depth.get(x, 1 << 30) > depth[y] + 1:
                    depth[x] = depth[y] + 1
                    changed = True
    for lk in cc:
        a, b = lk["from"], lk["to"]
        if depth.get(a) is not None and depth.get(b) is not None and depth[a] != depth[b]:
            outer, inner = (a, b) if depth[a] > depth[b] else (b, a)
            if (untraced_finals or {}).get(outer):
                continue
            lk["from"], lk["to"] = outer, inner
            lk["directed"], lk["cascade"] = True, True


def assemble(model, lines, roles=None):
    """The control_loops block from the bundle's traced signal lines (sheet_signal_lines). roles: {item: role}
    replaces the ISA roles (only the scorer's shuffled-roles control uses it). Reads no image."""
    cand = candidates(model)
    if roles is not None:
        cand = {k: {**v, "role": roles.get(k)} for k, v in cand.items()}
    role = {k: v["role"] for k, v in cand.items()}
    ident = {k: (v["scope"], v["number"]) for k, v in cand.items()}
    links, unresolved = _directed_links(signal_networks(model, lines), cand, role)
    reached = {lk["to"] for lk in links if role.get(lk["to"]) == "final_element"}
    untraced_finals = {c: [k for k in cand if ident[k] == ident[c] and role[k] == "final_element"
                           and k not in reached] for c in cand if role[c] == "controller"}
    _cascades(links, role, untraced_finals)
    relations, seen = [], {}

    def add(typ, a, b, evidence, basis, loop=None, inferred=False):
        if (typ, a, b) in seen:
            return seen[(typ, a, b)]
        cross = any(e["kind"] == "cross_sheet_flag" for e in evidence)
        rec = {"id": None, "type": typ, "from": a, "to": b, "direction": "forward" if basis else "unknown",
               **({"direction_basis": basis} if basis else {}),
               "confidence": "traced_direction_inferred" if inferred else "traced_cross_sheet" if cross else
                             "traced_and_grouped" if ident[a] == ident[b] else "traced",
               "evidence": evidence, **({"loop": loop} if loop else {}),
               "provenance": [{"sheet": e["sheet"], "box_0_1000": e["box_0_1000"], "line": e["line"],
                               "source_run": "scripts/loop_assembly.py", "model": None}
                              for e in evidence if e["kind"] == "traced_line" and "box_0_1000" in e],
               "verification": {"status": "unverified"}, "layer": "control_loop"}
        relations.append(rec)
        seen[(typ, a, b)] = rec
        return rec
    for lk in links:
        a, b = lk["from"], lk["to"]
        basis = ("cascade: the receiving controller is nearer a final element along traced signals" if lk.get("cascade")
                 else f"ISA-5.1 roles: {role[a]} -> {role[b]}" if lk["directed"] else None)
        add("signal_to", a, b, lk["evidence"], basis, inferred=bool(lk.get("cascade")))
    into, outof = defaultdict(list), defaultdict(list)
    for lk in links:
        if lk["directed"]:
            outof[lk["from"]].append(lk)
            into[lk["to"]].append(lk)
    groups = defaultdict(list)
    for k in sorted(cand):
        groups[ident[k]].append(k)
    controllers = sorted((k for k in cand if role[k] == "controller"), key=lambda k: (ident[k], cand[k]["tag"]))
    reaches = defaultdict(set)  # item -> controllers a traced signal joins it to
    for c in controllers:
        for lk in into[c] + outof[c]:
            reaches[lk["from"] if lk["to"] == c else lk["to"]].add(c)
    for lk in links:
        if not lk["directed"]:
            for x, y in ((lk["from"], lk["to"]), (lk["to"], lk["from"])):
                if role.get(y) == "controller":
                    reaches[x].add(y)
    loops, conflicts = [], []
    for c in controllers:
        meas = [lk for lk in into[c] if role.get(lk["from"]) in MEASUREMENTS]
        finals = []
        for lk in outof[c]:
            if role.get(lk["to"]) == "final_element":
                finals.append((lk["to"], [lk]))
            elif role.get(lk["to"]) == "relay":
                finals += [(l2["to"], [lk, l2]) for l2 in outof[lk["to"]] if role.get(l2["to"]) == "final_element"]
        inner = [lk for lk in outof[c] if lk.get("cascade")]
        traced = {lk["from"] for lk in meas} | {f for f, _ in finals} | {lk["to"] for lk in inner}
        group = [m for m in groups[ident[c]] if role[m] in MEASUREMENTS + ("final_element", "relay")
                 and m not in traced]  # (AIC 123A and
        # AIC 123D share loop 123 as two controllers; neither is a member of the other's loop)
        status = ("confirmed" if meas and (finals or inner) else
                  "partly_confirmed" if meas or finals or inner else "unconfirmed")
        lid = f"LOOP-{cand[c]['loop_identity']}-{compact(cand[c]['tag'])}"
        if lid in {lp["id"] for lp in loops}:  # the same tag twice in one scope: keep both, ids apart
            lid = f"{lid}-{c}"
        loops.append({
            "id": lid, "loop_identity": cand[c]["loop_identity"], "controller": c, "controller_tag": cand[c]["tag"],
            "loop_type": "cascade" if inner else "control", "status": status,
            "measurements": [{"id": lk["from"], "tag": cand[lk["from"]]["tag"], "role": role[lk["from"]],
                              "same_loop_identity": ident[lk["from"]] == ident[c]} for lk in meas],
            "final_elements": [{"id": f, "tag": cand[f]["tag"], "via": [lk["to"] for lk in path[:-1]],
                                "same_loop_identity": ident[f] == ident[c]} for f, path in finals],
            "sets_point_of": [{"id": lk["to"], "tag": cand[lk["to"]]["tag"]} for lk in inner],
            "tag_grouping_unconfirmed": [{"id": m, "tag": cand[m]["tag"], "role": role[m]} for m in group
                                         if not reaches.get(m)],
            "tag_grouping_refuted": [{"id": m, "tag": cand[m]["tag"], "role": role[m],
                                      "traced_to": sorted(reaches[m])} for m in group if reaches.get(m)]})
        if status == "confirmed":
            for f, path in finals:
                ev = [e for lk in path for e in lk["evidence"]] + [
                    {"kind": "loop_confirmed", "loop": lid, "measured_by": sorted(lk["from"] for lk in meas)}]
                add("controls", c, f, ev, "the controller's traced output, in a loop whose measurement is traced "
                                          "into the controller", loop=lid)
        for lk in inner:
            add("sets_point_of", c, lk["to"], lk["evidence"], "cascade: a traced signal from this controller to a "
                                                               "controller nearer a final element", loop=lid,
                inferred=True)
        for kind, items in (("measurement", [lk["from"] for lk in meas]), ("final element", [f for f, _ in finals])):
            for m in items:
                if ident[m] != ident[c]:
                    conflicts.append({"kind": "loop_identity", "loop": lid, "item": m, "tag": cand[m]["tag"],
                                      "what": f"a traced signal makes {cand[m]['tag']} the {kind} of {cand[c]['tag']}, "
                                              f"but its tag reads as loop {cand[m]['loop_identity']}"})
        for x in loops[-1]["tag_grouping_refuted"]:
            conflicts.append({"kind": "tag_grouping_refuted", "loop": lid, "item": x["id"], "tag": x["tag"],
                              "what": f"{x['tag']} shares loop {cand[c]['loop_identity']} with {cand[c]['tag']} by its "
                                      f"tag, but a traced signal joins it to "
                                      + ", ".join(cand[y]["tag"] for y in x["traced_to"])})
    for f in sorted({x["id"] for lp in loops for x in lp["final_elements"]}):
        by = [lp["id"] for lp in loops if any(x["id"] == f for x in lp["final_elements"])]
        if len(by) > 1:
            conflicts.append({"kind": "final_element_shared", "item": f, "tag": cand[f]["tag"], "loops": by,
                              "what": "traced signals from more than one controller reach this final element"})
    no_ctrl = [{"loop_identity": cand[ms[0]]["loop_identity"],
                "members": [{"id": m, "tag": cand[m]["tag"], "role": role[m]} for m in ms],
                "why": "no controller carries this loop identity; no loop is asserted"}
               for _, ms in sorted(groups.items()) if len(ms) >= 2 and not any(role[m] == "controller" for m in ms)]
    order = {"signal_to": 0, "controls": 1, "sets_point_of": 2}
    relations.sort(key=lambda r: (order[r["type"]], r["from"], r["to"]))
    for n, r in enumerate(relations, 1):
        r["id"] = f"CL-{n:03d}"
    for lp in loops:
        for m in lp["measurements"]:
            m["relation"] = seen[("signal_to", m["id"], lp["controller"])]["id"]
    counts = {"loops": len(loops), **{s: sum(lp["status"] == s for lp in loops)
                                      for s in ("confirmed", "partly_confirmed", "unconfirmed")},
              "cascades": sum(lp["loop_type"] == "cascade" for lp in loops),
              **{t: sum(r["type"] == t for r in relations) for t in order},
              "signal_lines": len(lines), "unresolved_signal_networks": len(unresolved),
              "tag_groups_without_controller": len(no_ctrl), "conflicts": len(conflicts)}
    return {"schema": SCHEMA,
            "method": "scripts/loop_assembly.py: ISA-5.1 loop identity and roles from the read tags, confirmed or "
                      "refuted by traced signal lines",
            "idea_credit": "grouping instruments by ISA-5.1 loop number, then tracing signal lines and chaining "
                           "cascades, follows the public pid-to-kg skill (github.com/ScottDuncanAI/PID-to-Knowledge-Graph, "
                           "MIT; A409). This is independent code that does not use that tool.",
            "evidence_kinds": {"tag_grouping": "a shared ISA-5.1 loop identity (area prefix and loop number); "
                                               "proposes membership, never asserts a relation",
                               "traced_line": "a drawn signal line traced from the sheet image or the line layer",
                               "cross_sheet_flag": "an off-page pair joining traced signal lines across sheets"},
            "confidence_tiers": {"traced_direction_inferred": "a cascade: the line is traced, but which controller is "
                                                              "outer is inferred from graph distance to a final "
                                                              "element",
                                 "traced_and_grouped": "traced, and both ends share a loop identity",
                                 "traced": "traced; the loop identities differ",
                                 "traced_cross_sheet": "traced on both sheets and joined through an unverified "
                                                       "off-page pair"},
            "not_used": "no relation is taken from layout or from tag grouping alone",
            "counts": counts, "signal_lines": lines, "relations": relations, "loops": loops,
            "unresolved_signal_networks": unresolved, "tag_groups_without_controller": no_ctrl,
            "conflicts": conflicts}


def add_loops(model, source):
    """Assemble model["control_loops"] in place from the sheet images in `source`; return a status record (never
    raises for a skip). Nothing is written to the model when no item reads as an ISA-5.1 instrument with a loop role,
    so a bundle loops add nothing to is unchanged."""
    if not any(c["role"] for c in candidates(model).values()):
        return {"status": "nothing to assemble",
                "reason": "no item's tag reads as an ISA-5.1 instrument with a loop role"}
    try:
        lines = sheet_signal_lines(model, source)
    except ImportError as error:
        return {"status": "skipped", "reason": f"needs OpenCV and NumPy (pip install -r requirements.txt): {error}"}
    model["control_loops"] = assemble(model, lines)
    return {"status": "added", **model["control_loops"]["counts"]}
