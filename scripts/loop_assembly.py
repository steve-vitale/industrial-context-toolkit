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
                    dashed_signal_lines() (an instrument line of the bundle's line layer is listed for review but is
                    never signal evidence). A traced line ends at the first symbol box it reaches; a line end in reach
                    of two boxes attaches to neither.
  cross_sheet_flag  traced signal lines that end on two off-page connectors the bundle paired across sheets (every line
                    at either connector joins); a connector text that names an ISA tag must name one the lines reach.

Roles come from the ISA-5.1 letters only, read in order by parse_letters and role_of (first letter, first-letter
modifier, function letters, function modifiers): a final element ends in V, a controller has C or K among its
functions, then transmitter (T), switch (S; ZSC is a closed-position switch), relay (Y), primary element (E) and
indicator (I, R, A). Relief devices (PSV, TSV, PSE, PRV), hand switches (HS), plant-coded tags and letters that do
not parse (LVC) have no loop role, and no signal is read to or from them.

What is asserted, and on what evidence. The default is inverted: a relation is asserted only when every condition
of the positive list in signal_conditions() holds; a network failing any of them is listed under
unresolved_signal_networks with the conditions it failed, and nothing is asserted on it.
  signal_to       a traced signal between a sender and its next receiver (NEXT: a measurement to a controller, a
                  controller to a final element or relay, a relay to a final element), from sender to receiver, or
                  between two controllers (direction "unknown" until _cascades orders it). A branching network is
                  asserted only when one sender reaches only its next receivers.
  controls        controller -> final element, only when the loop is confirmed: a traced signal into the
                  controller from a measurement and a traced signal out of it to that final element (directly or
                  through a relay).
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
NEXT = {"transmitter": {"controller", "indicator", "switch"},
        "primary_element": {"transmitter", "controller", "indicator", "switch"},
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


# ISA-5.1 letters after the first: first-letter modifiers, succeeding (function) letters, function modifiers.
FIRST_MODIFIERS = set("DFQJ")       # differential, ratio, integrate or totalize, scan (PDIC, FFIC, FQIC)
FUNCTIONS = set("ABCEGIKLNORSTUVWXYZ")  # alarm ... valve, well, unclassified, relay or compute, driver
LEVEL_MODIFIERS = set("HLM")        # high, low, middle (PSHH, PAL), read at the end of the letters
SWITCH_MODIFIERS = set("OC") | LEVEL_MODIFIERS  # a switch's open or closed position (ZSO, ZSC), or its level


PASSIVE = set("ABEGILNOPRUWX")   # readout or passive functions: alarm, element, glass, indicate, record, well ...
OUTPUT = set("CKSTVYZ")          # output functions: control, control station, switch, transmit, valve, relay, driver
OUTPUTS = {"", "C", "K", "S", "T", "V", "Y", "Z", "CV", "SV"}  # one output, or a control or shut-off valve


def parse_letters(letters):
    """ISA-5.1 letters read in order: {variable, modifier, passive, output, relief}, or None when they do not parse.
    The first letter is the measured or initiating variable; then an optional first-letter modifier (D, F, Q, J);
    then readout or passive functions (I, R, E, ...); then at most one output function (C, T, S, Y, V, ...; CV and SV
    are one valve); then function modifiers: levels (H, L, M) at the end, and after a switch S its position too (in ZSC
    the C is "closed", not control), and an alarm A after an output (FICA). A valve takes no readout letter before it
    (FIV does not parse), an output comes after the readouts (FCI does not), and two outputs do not parse (FTC). A
    safety or relief valve or element on pressure, temperature, flow or level (PSV, TSE, PRV) is marked relief;
    ESDV, SDV and BDV are shut-down and blow-down valves."""
    if not letters or not letters.isalpha():
        return None
    first, rest = letters[0], letters[1:]
    modifier = None
    if first in "PTFL" and rest in ("SV", "SE", "RV"):
        return {"variable": first, "modifier": None, "passive": "", "output": rest, "relief": True}
    if rest == "SDV":  # ESDV: emergency shut-down valve
        rest = "V"
    if len(rest) > 1 and rest[0] in FIRST_MODIFIERS:
        modifier, rest = rest[0], rest[1:]
    if "S" in rest:
        k = rest.index("S")
        if rest[k + 1:] and set(rest[k + 1:]) <= SWITCH_MODIFIERS:
            rest = rest[:k + 1]
    while len(rest) > 1 and rest[-1] in LEVEL_MODIFIERS and rest[-2] in "ASIRT" + "HLM":
        rest = rest[:-1]
    if len(rest) > 1 and rest[-1] == "A" and rest[-2] in OUTPUT:
        rest = rest[:-1]
    if not rest:
        return None
    k = next((n for n, ch in enumerate(rest) if ch in OUTPUT), len(rest))
    passive, output = rest[:k], rest[k:]
    if set(passive) - PASSIVE or output not in OUTPUTS or (output.endswith("V") and passive):
        return None
    return {"variable": first, "modifier": modifier, "passive": passive, "output": output, "relief": False}


def letters_out_of_order(letters):
    """True when the letters are made of ISA-5.1 function letters but do not read in ISA order (LVC, FCI, FTC, FIV)."""
    return bool(letters) and len(letters) > 1 and parse_letters(letters) is None and \
        not set(letters[1:]) - (FUNCTIONS | FIRST_MODIFIERS | LEVEL_MODIFIERS)


def role_of(letters):
    """The loop role ISA-5.1 letters give, or None, from parse_letters:
      relief_device   a safety (S) or relief (R) valve or element on pressure, temperature, flow or level: PSV, TSV,
                      PSE, PRV, FSV. Self-acting, never a loop's final element.
      final_element   the output is a valve: FV, FCV, PCV, LCV, XV, HV, SDV, ESDV, and actuated shut-off valves
                      named ESV or SV (E or S is then the first letter, not a safety modifier).
      controller      C or K among the functions: FIC, FRC, PDIC, FFIC, FQIC, HIC, HC.
      transmitter     T: FT, PIT, AIT, PDT.          switch     S (H first: hand_switch): PSHH, ZSO, ZSC.
      relay           Y: FY, TY.                     primary_element  E: FE, TE.
      indicator       I, R or A only: PI, TR, LAH.
    Anything else (TW, FO, PID, LVC, PVC, FCI, FTC, FIV, MOV) has no loop role."""
    parsed = parse_letters(letters)
    if parsed is None:
        return None
    first, out, passive = parsed["variable"], parsed["output"], parsed["passive"]
    if parsed["relief"]:
        return "relief_device"
    if out.endswith("V"):
        return "final_element"
    if out in ("C", "K"):
        return "controller"
    if out == "T":
        return "transmitter"
    if out == "S":
        return "hand_switch" if first == "H" else "switch"
    if out == "Y":
        return "relay"
    if out:
        return None
    if "E" in passive:
        return "primary_element"
    if set(passive) <= set("IRA"):
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
       width, form one straight run. Where a solid line lies in the gap, the two sides join only when the dash pattern
       carries on in step through it (_in_phase): one line crossing a pipe, not two lines each drawn to it. The same
       holds where a dashed line or the piece two crossing dashes make lies in the gap (that gap may be twice as
       wide). A line joined this way is marked merged_through_crossing: being in step is evidence, not proof.
    4. Runs join only where one ENDS: a corner (two runs ending at one point) or a tee (a run ending on the side of
       another). Two runs that both pass through the meeting point cross and are not joined, as line_layers.py treats
       an unmarked crossing; two runs that end on one run from opposite sides at one point are not tees either.
    5. A network of runs with min_dashes dashes or more is a signal line; it joins the symbols its free run ends point
       at, within the gap of the box edge. A run end at a symbol box is terminal and is never joined to another run in
       step 4, so a controller's input and output stay two lines. An end in reach of two boxes attaches to neither:
       the line lists the boxes under ambiguous_ends instead. A shorter one counts only between two instrument bubbles (a signal drawn
       across the short gap between two stacked controllers). Text strokes can look like dashes; a network is kept
       only where it reaches two symbols.
    6. A straight line that ends at a box from both sides with its dashes carrying on inside it is drawn through the
       box: both sides list it under passes_through_symbol.
    7. Each line records its stroke width (stroke_px, measured across its dashes on the original ink), the sheet's
       solid-line width (pipe_px, None without solid lines) and the instrument bubbles' outline width (outline_px), for
       the thin_stroke condition of signal_conditions()."""
    import cv2
    import numpy as np
    import trace_connections as tc
    o = {**DASH, **opt}
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise FileNotFoundError(image_path)
    H, W = gray.shape
    ink = tc.binarize(gray)
    ink0 = ink.copy()
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
    solid_h = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (L, 1)))
    solid_v = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, L)))
    solid0 = solid_h | solid_v
    pipe_px = _solid_width(cv2, ink0, solid_h, solid_v, L)
    outline_px = _outline_width(cv2, np, ink0, [b for k, b in boxes.items() if cls.get(k) == "instrumentation"]
                                or list(boxes.values()))
    solid = cv2.dilate(solid0, np.ones((3, 3), np.uint8))
    res = ink & (1 - solid)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(res, connectivity=8)
    tmax = max(3, int(round(o["max_width_frac"] * side)))
    dmin = max(3, int(round(o["min_dash_frac"] * side)))
    gap = max(3, int(round(o["max_gap_frac"] * side)))
    strokes = []  # (axis, across, lo, hi, piece) on the pixel grid
    thick = {}  # piece -> stroke width in px (area over length)
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
            thick[npieces] = _cross_width(ink0, "h" if w >= h else "v", (y + y1) / 2 if w >= h else (x + x1) / 2,
                                          (x + x1) // 2 if w >= h else (y + y1) // 2)
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
        thick[npieces] = _cross_width(ink0, "h", hy, (x + x1) // 2)
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
    merged_strokes = set()
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
            crossed = _ink_between(solid0, ax, c, hi, nxt) or _ink_between(res, ax, c, hi, nxt) or any(
                st[0] != ax and st[2] - tmax <= c <= st[3] + tmax and hi < st[1] < nxt for st in strokes)
            if crossed:  # another line (a pipe, a dashed line) lies in the gap
                if not _in_phase(strokes, ids, si, best, tmax, gap):
                    continue  # two dashed lines each drawn to the other line, not one crossing it: kept apart
                merged_strokes.update((si, best))  # joined through a crossing: provenance for the assembly
            elif d > gap + 1:
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
    merged_runs = {find(si) for si in merged_strokes}
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
    through = defaultdict(set)  # run -> boxes a straight line is drawn through (its dashes carry on inside the box)
    end_stroke = {}
    for si, st in enumerate(strokes):
        r = find(si)
        for e, pos in (("lo", st[2]), ("hi", st[3])):
            if pos == run_info[r][e]:
                end_stroke[(r, e)] = si
    for (r1, e1), at1 in terminal.items():
        if e1 != "hi" or len(at1) != 1:
            continue
        for (r2, e2), at2 in terminal.items():
            if e2 != "lo" or at2 != at1 or r2 == r1 or run_info[r2]["axis"] != run_info[r1]["axis"] or \
                    abs(run_info[r2]["c"] - run_info[r1]["c"]) > tmax or run_info[r2]["lo"] <= run_info[r1]["hi"]:
                continue
            run_strokes = [si for si in range(len(strokes)) if find(si) in (r1, r2)]
            if _dashes_inside(ink0, boxes[at1[0]], run_info[r1]["axis"], run_info[r1]["c"],
                              [strokes[si] for si in run_strokes]):
                through[r1].add(at1[0])
                through[r2].add(at1[0])
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
                if not corner and _opposite_stub(run_info, r, e, q, tmax, gap):
                    break  # two runs end on q from opposite sides at one point: a crossing, not two tees
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
        widths = sorted(thick[p] for p in pieces)
        behind = sorted(set().union(*(through[r] for r in rs)))
        lines.append({"members": sorted(hit), "dashes": len(pieces),
                      **({"merged_through_crossing": True} if any(r in merged_runs for r in rs) else {}),
                      **({"passes_through_symbol": behind} if behind else {}),
                      "stroke_px": round(widths[len(widths) // 2], 2), "pipe_px": pipe_px, "outline_px": outline_px,
                      **({"ambiguous_ends": sorted(ambiguous)} if ambiguous else {}),
                      "box_0_1000": [round(max(0.0, 1000 * x0 / W), 1), round(max(0.0, 1000 * y0 / H), 1),
                                     round(min(1000.0, 1000 * x1 / W), 1), round(min(1000.0, 1000 * y1 / H), 1)]})
    lines.sort(key=lambda x: (x["members"], x["box_0_1000"]))
    return {"lines": lines, "side_px": round(side, 1), "pipe_px": pipe_px, "outline_px": outline_px, "settings": o}


def _cross_width(ink, axis, c, at):
    """The ink's width across a stroke, in px, on the original image: from the stroke's centre line at position `at`,
    count inked pixels outwards on both sides. Measured on the original ink, so a thick line the solid-line filter
    has hollowed out still reads as thick."""
    H, W = ink.shape
    c, at = int(round(c)), int(at)

    def on(k):
        y, x = (k, at) if axis == "h" else (at, k)
        return 0 <= y < H and 0 <= x < W and ink[y, x]
    if not on(c):
        return 0
    lo, hi = c, c
    while on(lo - 1):
        lo -= 1
    while on(hi + 1):
        hi += 1
    return hi - lo + 1


def _solid_width(cv2, ink, solid_h, solid_v, L):
    """The sheet's solid-line (pipe) width in px: the median of the widths across every straight solid run, measured
    on the original ink at points along the run, or None when the sheet has none."""
    w = []
    for mask, axis in ((solid_h, "h"), (solid_v, "v")):
        n, _, stats, cent = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, n):
            x, y, bw, bh = (int(v) for v in stats[i][:4])
            length = bw if axis == "h" else bh
            if length < L:
                continue
            c = cent[i][1] if axis == "h" else cent[i][0]
            start = x if axis == "h" else y
            for at in range(start + length // 8, start + length, max(1, length // 8)):
                v = _cross_width(ink, axis, c, at)
                if v:
                    w.append(v)
    if not w:
        return None
    w.sort()
    return float(w[len(w) // 2])


def _outline_width(cv2, np, ink, boxes):
    """The symbol outline width in px: the median over the boxes of 2 * ink area / contour length inside the box (a
    ring or a stroke of width t has an area of about t times half its contour length)."""
    w = []
    for x0, y0, x1, y1 in boxes:
        crop = np.ascontiguousarray(ink[y0:y1 + 1, x0:x1 + 1]).astype(np.uint8)
        area = int(crop.sum())
        if not area:
            continue
        cs, _ = cv2.findContours(crop, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        per = sum(cv2.arcLength(c, True) for c in cs)
        if per:
            w.append(2 * area / per)
    return round(float(np.median(w)), 2) if w else None


def _opposite_stub(run_info, r, e, q, tmax, gap):
    """True when another run collinear with run r ends on run q from the other side, at the same point: the shape of
    one line crossing q (or two lines drawn to it) that the in-step test kept apart. Neither end is then read as a tee
    into q, so the two stubs are not joined to q's line or, through it, to each other."""
    ri, qi = run_info[r], run_info[q]
    mine = (ri["lo"] if e == "lo" else ri["hi"]) - qi["c"]
    for r2, r2i in run_info.items():
        if r2 in (r, q) or r2i["axis"] != ri["axis"] or abs(r2i["c"] - ri["c"]) > tmax:
            continue
        for e2 in ("lo", "hi"):
            theirs = r2i[e2] - qi["c"]
            if theirs * mine < 0 and abs(theirs) <= gap + tmax and qi["lo"] - gap <= ri["c"] <= qi["hi"] + gap:
                return True
    return False


def _dashes_inside(ink, box, axis, c, run_strokes):
    """True when a straight dashed line that ends at a box from both sides carries on inside it: on the original ink,
    along the line's centre row inside the box (its outline ring left out), runs of the line's own dash length cover
    at least 35% of the inside, and no run is longer than a dash. A line that ends at a bubble leaves its inside empty or holds text there, whose strokes are
    shorter; a solid divider (a shared-display bubble) is longer."""
    x0, y0, x1, y1 = box
    lens = sorted(st[3] - st[2] + 1 for st in run_strokes)
    if not lens:
        return False
    dash = lens[(3 * len(lens)) // 4]
    lo, hi = (x0, x1) if axis == "h" else (y0, y1)
    margin = max(2, (hi - lo) // 6)
    best = 0
    for dc in (-1, 0, 1):
        row = int(round(c)) + dc
        seg = ink[row, lo + margin:hi - margin + 1] if axis == "h" else ink[lo + margin:hi - margin + 1, row]
        runs, n = [], 0
        for v in list(seg) + [0]:
            if v:
                n += 1
            elif n:
                runs.append(n)
                n = 0
        dashes = [r for r in runs if 0.6 * dash <= r <= 1.4 * dash]
        if dashes and not [r for r in runs if r > 1.4 * dash]:
            best = max(best, sum(dashes) / max(1, len(seg)))
    return best >= 0.35


def _in_phase(strokes, ids, si, best, tmax, gap):
    """True when the dash pattern on one side of a solid line carries on in step on the other side: one dashed line
    crossing a pipe, not two dashed lines that each end at it. A crossing line's dashes keep their period through the
    pipe (the pipe may cut a dash short on either side); two lines drawn to the pipe start their patterns afresh. At
    least two dashes are needed on each side to read the period and the step; with fewer the answer is no."""
    _, c0, _, _, _ = strokes[si]

    def chain(start, step):
        out, cur = [start], start
        while len(out) < 6:
            lo, hi = strokes[cur][2], strokes[cur][3]
            cand = [sj for sj in ids if sj not in out and abs(strokes[sj][1] - c0) <= tmax and
                    (0 < lo - strokes[sj][3] <= gap + 1 if step < 0 else 0 < strokes[sj][2] - hi <= gap + 1)]
            if not cand:
                break
            cur = max(cand, key=lambda sj: strokes[sj][3]) if step < 0 else min(cand, key=lambda sj: strokes[sj][2])
            out.append(cur)
        return out
    left, right = chain(si, -1)[::-1], chain(best, 1)
    if len(left) < 2 or len(right) < 2:
        return False
    lens = sorted(strokes[x][3] - strokes[x][2] + 1 for x in left + right)
    full = lens[(3 * len(lens)) // 4]
    starts_l = [strokes[x][2] for x in left]
    starts_r = [strokes[x][2] for x in right[1:]]  # the first dash past the pipe may be cut at its start
    diffs = [b - a for a, b in zip(starts_l, starts_l[1:])] + [b - a for a, b in zip(starts_r, starts_r[1:])]
    if len(starts_r) >= 1 and len(starts_l) >= 1 and not diffs:
        return False
    period = sorted(diffs)[len(diffs) // 2] if diffs else 0
    if period <= 0:
        return False
    first_r = right[0]
    r_len = strokes[first_r][3] - strokes[first_r][2] + 1
    anchor_r = strokes[first_r][2] if r_len >= 0.8 * full else strokes[first_r][3] - full + 1
    off = (anchor_r - starts_l[-1]) % period
    return min(off, period - off) <= max(2, 0.15 * period)


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
                            **{k: line.get(k) for k in ("stroke_px", "pipe_px", "outline_px")},
                            **({"merged_through_crossing": True} if line.get("merged_through_crossing") else {}),
                            **({"passes_through_symbol": sorted({syms[sheet][m]["asset"]
                                                                 for m in line["passes_through_symbol"]})}
                               if line.get("passes_through_symbol") else {}),
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


RANK = {"primary_element": 0, "transmitter": 1, "switch": 2, "indicator": 2, "controller": 3, "relay": 4,
        "final_element": 5}


def compact(text):
    return re.sub(r"[\s\-_]", "", str(text or "")).upper()


CONNECTOR_TAG = re.compile(r"(?:TO|FROM)[\s:]+((?:[0-9][0-9A-Z]{0,5}[\s-]+)?[A-Z]{1,6}[\s-]*[0-9]+(?:\.[0-9]+)?[A-Z]?)\b")


def connector_tags(text):
    """The ISA-5.1 tags with a loop role an off-page connector's text names after TO or FROM ("SIG PID 2 / TO FV 401"
    names FV 401; "TO PID 2" names nothing, as PID has no loop role)."""
    out = []
    for m in CONNECTOR_TAG.finditer(" ".join(str(text or "").upper().split())):
        ident = loop_identity(m.group(1))
        if ident and role_of(ident[3]):
            out.append(" ".join(m.group(1).split()))
    return out


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
            named = {cid: connector_tags(conn[cid].get("text")) for cid in (p["a"], p["b"])}
            named = {cid: t for cid, t in named.items() if t}
            names = [{"connector": cid, "names": tag[m]} for cid in (p["a"], p["b"]) for m in members
                     if tag.get(m) and compact(tag[m]) in {compact(t) for t in connector_tags(conn[cid].get("text"))}]
            flags.append({"kind": "cross_sheet_flag", "pair": p["id"], "connectors": [p["a"], p["b"]],
                          "sheets": [p["sheet_a"], p["sheet_b"]], "texts": [p.get("text_a"), p.get("text_b")],
                          "pair_method": p.get("method"),
                          "pair_status": (p.get("verification") or {}).get("status"),
                          "named_tags": named, "text_names_reached_instrument": names})
        out.append({"members": members, "lines": net["lines"], "flags": flags})
    return out


def _line_evidence(lines):
    return [{"kind": "traced_line", "line": x["id"], "line_kind": x["line_kind"], "sheet": x["sheet"],
             **({"box_0_1000": x["box_0_1000"], "dashes": x["dashes"]} if "box_0_1000" in x else {}),
             **({"instrument_lines": x["lines"]} if "lines" in x else {})} for x in lines]


MIN_DASH_PIECES = 2   # a signal line has at least this many dash pieces (one stroke can be a leader or a letter)
THIN_VS_OUTLINE = 1.5  # ...and its stroke is at most this times the instrument bubbles' outline pen
THIN_VS_PIPE = 1.25    # ...and, where the sheet has solid lines, at most this times their width
SIGNAL_ROLES = tuple(RANK)  # the roles a signal may join; relief devices, hand switches and no role never


def signal_conditions(net, cand, role, model=None):
    """THE POSITIVE LIST. A signal relation is asserted on a network of traced lines only when every condition below
    holds; a network failing any of them is listed under unresolved_signal_networks with the conditions it failed,
    and nothing is asserted on it. Returns [(condition, detail)] for the failed ones ([] = assert).

      dashed_line          every line is a dashed signal line traced from the sheet image (dashed_signal_lines). A
                           solid instrument line of the line layer may be an impulse line, a capillary or a shared
                           leader, so it is never signal evidence by itself.
      min_dash_pieces      every line has at least MIN_DASH_PIECES dash pieces: one stroke between two stacked bubbles
                           is a leader, a faceplate edge or part of a letter.
      thin_stroke          every line's stroke is at most THIN_VS_OUTLINE times the outline pen of the sheet's
                           instrument bubbles, and where the sheet has solid lines, at most THIN_VS_PIPE times their
                           width: a process line broken into dash-sized pieces (a scan dropout) is drawn with the
                           thicker pipe pen. (Where a sheet draws pipes with the same pen as signals, as TE does, the
                           pipe width cannot tell them apart and the outline pen decides.)
      not_across_a_pipe    enforced in the tracer (dashed_signal_lines step 3): two dashed runs that meet a solid line
                           from opposite sides are one line only when the dash pattern carries on in step through it;
                           two lines drawn to a pipe stay two lines.
      ends_resolved        no line end is in reach of two symbols (ambiguous_ends).
      not_through_a_symbol no line passes behind a symbol: two collinear runs that end at one box from opposite sides
                           with the dash pattern in step across it are one line drawn through the box
                           (passes_through_symbol), not a signal into it and another out of it.
      known_roles          every member has a loop role in SIGNAL_ROLES from the full ISA-5.1 letter parse (role_of):
                           no plant-coded tag, relief device, hand switch or letters that do not parse.
      role_order           two members: a sender and its next receiver (NEXT: measurement -> controller, controller ->
                           final element or relay, relay -> final element), or two controllers (a cascade, ordered by
                           _cascades). More members: one sender, and every other member one of its next receivers.
      connector_text_agrees  where the network runs through a paired off-page connector whose printed text names an
                           ISA-5.1 tag with a loop role ("TO FV 401"), the joined lines reach an item with that tag.
    And one limit on what a passing network may support, applied in _directed_links and assemble():
      not_merged_through_a_crossing  a line the tracer joined through a crossing (merged_through_crossing: a pipe or
                           another line lay in a gap, and the dash pattern was in step across it) supports a signal_to
                           at tier traced at most, and never controls, sets_point_of or a confirmed loop; the network is
                           also listed under unresolved_signal_networks with this condition named. Being in step is
                           evidence, not proof: two lines drawn to a pipe from either side are in step by chance about
                           one time in six."""
    failed = []
    lines = net["lines"]
    ms = [m for m in net["members"] if m in cand]
    solid = [x["id"] for x in lines if x["line_kind"] != "dashed_signal_line"]
    if solid:
        failed.append(("dashed_line", f"solid instrument line(s) {', '.join(solid)} from the line layer"))
    few = [x["id"] for x in lines if x["line_kind"] == "dashed_signal_line" and x.get("dashes", 0) < MIN_DASH_PIECES]
    if few:
        failed.append(("min_dash_pieces", f"fewer than {MIN_DASH_PIECES} dash pieces on {', '.join(few)}"))
    thick = []
    for x in lines:
        if x["line_kind"] != "dashed_signal_line":
            continue
        w, outline, pipe = x.get("stroke_px"), x.get("outline_px"), x.get("pipe_px")
        if w is None or outline is None or w > THIN_VS_OUTLINE * outline or (pipe is not None and w > THIN_VS_PIPE * pipe):
            thick.append(f"{x['id']} stroke {w} px (bubble outline {outline} px, solid lines {pipe} px)")
    if thick:
        failed.append(("thin_stroke", "; ".join(thick)))
    ambiguous = [a for x in lines for a in x.get("ambiguous_ends", [])]
    if ambiguous:
        failed.append(("ends_resolved", f"a line end in reach of {ambiguous}"))
    behind = sorted({b for x in lines for b in x.get("passes_through_symbol", [])})
    if behind:
        failed.append(("not_through_a_symbol", "the line runs on in step on the far side of " + ", ".join(behind)
                       + ": it passes behind the symbol rather than ending at it"))
    if len(ms) < 2:
        if not failed:
            return []  # one item or none: nothing to assert, nothing to review
        return failed
    bad = [m for m in ms if role[m] not in SIGNAL_ROLES]
    if bad:
        failed.append(("known_roles", "no loop role: " + ", ".join(f"{cand[m]['tag']} ({role[m] or 'none'})"
                                                                     for m in bad)))
    else:
        if len(ms) == 2:
            a, b = sorted(ms, key=lambda m: RANK[role[m]])
            ok = role[b] in NEXT.get(role[a], ()) or role[a] == role[b] == "controller"
        else:
            low = min(RANK[role[m]] for m in ms)
            senders = [m for m in ms if RANK[role[m]] == low]
            ok = len(senders) == 1 and all(role[m] in NEXT.get(role[senders[0]], ()) for m in ms if m != senders[0])
        if not ok:
            failed.append(("role_order", "roles " + ", ".join(f"{cand[m]['tag']} {role[m]}" for m in ms)
                           + " are not a sender and its next receivers"))
    reached = {compact(cand[m]["tag"]) for m in ms}
    for f in net["flags"]:
        for cid, tags in sorted((f.get("named_tags") or {}).items()):
            if not reached & {compact(t) for t in tags}:
                failed.append(("connector_text_agrees", f"connector {cid} names {', '.join(tags)}; the joined lines "
                                                        "reach none of them"))
    return failed


def _directed_links(nets, cand, role):
    """[(from, to, directed, evidence)] for the networks that meet every signal_conditions() condition, and the
    unresolved networks with the conditions each failed."""
    links, unresolved = [], []
    for net in nets:
        ms = [m for m in net["members"] if m in cand]
        evidence = _line_evidence(net["lines"]) + net["flags"]
        failed = signal_conditions(net, cand, role)
        if failed:
            unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                               "failed_conditions": [c for c, _ in failed],
                               "why": "; ".join(f"{c}: {d}" for c, d in failed),
                               **({"ambiguous_ends": [a for x in net["lines"] for a in x.get("ambiguous_ends", [])]}
                                  if any(x.get("ambiguous_ends") for x in net["lines"]) else {})})
            continue
        if len(ms) < 2:
            continue
        merged = any(x.get("merged_through_crossing") for x in net["lines"])
        if merged:
            unresolved.append({"members": ms, "roles": {m: role[m] for m in ms}, "evidence": evidence,
                               "failed_conditions": ["not_merged_through_a_crossing"], "signal_to_kept": True,
                               "why": "not_merged_through_a_crossing: the tracer joined this line through a crossing "
                                      "(a pipe or another line in a gap); its signal_to is kept at tier traced, and it "
                                      "is not used for controls, sets_point_of or a confirmed loop"})
        if len(ms) == 2:
            a, b = sorted(ms, key=lambda m: RANK[role[m]])
            directed = RANK[role[a]] != RANK[role[b]]
            links.append({"from": a, "to": b, "directed": directed, "evidence": evidence, "merged": merged})
            continue
        low = min(RANK[role[m]] for m in ms)
        sender = next(m for m in ms if RANK[role[m]] == low)
        links += [{"from": sender, "to": m, "directed": True, "evidence": evidence, "merged": merged}
                  for m in ms if m != sender]
    return links, unresolved


def _cascades(links, role, untraced_finals=None, measured=None):
    """Direct controller-to-controller links outer -> inner: the inner controller is nearer a final element along
    traced controller-to-controller links. Equal or unknown distance leaves the link undirected, and so does a would-be
    outer controller that has a final element of its own loop identity no traced line reaches (it may be the inner
    one, with its output simply not traced), and so does a would-be outer controller with no traced measurement of
    its own (a transmitter misread as a controller, FT read as FC, would otherwise become an outer loop). Links the
    tracer merged through a crossing take no part. A direction found this way is inferred from graph distance, so its
    relations carry the tier traced_direction_inferred."""
    links = [lk for lk in links if not lk.get("merged")]
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
            if (untraced_finals or {}).get(outer) or (measured is not None and outer not in measured):
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
    solid = [lk for lk in links if not lk.get("merged")]  # the links loop logic may rest on
    reached = {lk["to"] for lk in solid if role.get(lk["to"]) == "final_element"}
    untraced_finals = {c: [k for k in cand if ident[k] == ident[c] and role[k] == "final_element"
                           and k not in reached] for c in cand if role[c] == "controller"}
    measured = {lk["to"] for lk in solid if lk["directed"] and role.get(lk["from"]) in MEASUREMENTS
                and role.get(lk["to"]) == "controller"}
    _cascades(links, role, untraced_finals, measured)
    relations, seen = [], {}

    def add(typ, a, b, evidence, basis, loop=None, inferred=False, merged=False):
        if (typ, a, b) in seen:
            return seen[(typ, a, b)]
        cross = any(e["kind"] == "cross_sheet_flag" for e in evidence)
        rec = {"id": None, "type": typ, "from": a, "to": b, "direction": "forward" if basis else "unknown",
               **({"direction_basis": basis} if basis else {}),
               **({"merged_through_crossing": True} if merged else {}),
               "confidence": "traced_direction_inferred" if inferred else "traced_cross_sheet" if cross else
                             "traced_and_grouped" if ident[a] == ident[b] and not merged else "traced",
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
        add("signal_to", a, b, lk["evidence"], basis, inferred=bool(lk.get("cascade")), merged=bool(lk.get("merged")))
    into, outof = defaultdict(list), defaultdict(list)
    for lk in solid:
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
    for lk in solid:
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
        traced = {lk["from"] for lk in meas} | {f for f, _ in finals} | {lk["to"] for lk in inner} | \
            {lk["to"] for _, path in finals for lk in path[:-1]}  # a relay on the way to the valve is traced
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
