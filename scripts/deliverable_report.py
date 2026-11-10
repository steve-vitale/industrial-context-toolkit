"""Turn a review bundle (scripts/import_site_drawing.py output) into the one-page report a client would read first.

    python scripts/deliverable_report.py my-bundle                     # writes my-bundle/REPORT.html
    python scripts/deliverable_report.py my-bundle --out report.html

The report is a single self-contained HTML file: what was extracted from the drawing and by what, the drawing with
every extracted item boxed, the items to check first and why, the asset hierarchy, what each file in the package is
for, the next steps, and what the package does not establish. It reads only the bundle; it adds no judgement of its
own, and every number in it comes from the bundle's files. With Pillow installed the drawing is embedded as a
reduced JPEG; without it, as the original PNG.

It refuses a review_queue.csv that doesn't describe plant_model.json as it is now: every column but the reviewer's
OPS_ ones is rewritten from the model by the sheet's own writer and must match. Applied review records are listed
with their supplied attribution and left out of the items to check first.
"""
import argparse
import base64
import csv
import html
import io
import json
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import TWIN_REVIEW_COLS, _csv_text, twin_review_rows  # noqa: E402  (the queue's own writer)
from output_paths import protect_outputs

CLASS_COLOURS = {"tank": "#b45309", "pump": "#7c3aed", "valve": "#0f766e", "instrumentation": "#2563eb",
                 "inlet/outlet": "#be185d", "general": "#4b5563"}
ROUTINE = ("routine check", "check the line exists")
FILES = [
    ("review_queue.csv", "Every extracted item and link, one row each, for a reviewer to confirm, correct or reject in "
                         "the OPS_ columns. Start here."),
    ("plant_model.json", "The draft asset model: systems, equipment, instruments, valves, links, with where each came "
                         "from on the sheet."),
    ("ignition/tags.json", "An Ignition tag import (UDT types, one instance per asset); every value is a placeholder "
                           "until mapped to a real signal."),
    ("pi/", "PI AF staging sheets and the steps a PI site would still run; not import-tested."),
    ("svg/sheet_0.svg", "The extracted items and links drawn as a logical diagram, not pipe routes."),
    ("source/", "The exact drawing and extraction the bundle was built from, with hashes in intake_manifest.json."),
    ("READ_ME.txt", "What the bundle has not established."),
]


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("source drawing is not a PNG")
    return struct.unpack(">II", data[16:24])


def drawing_uri(png_bytes, max_width=1600):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        if im.width > max_width:
            im = im.resize((max_width, round(im.height * max_width / im.width)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        return "data:image/png;base64," + base64.b64encode(png_bytes).decode()


def items(model):
    for group in ("units", "instruments", "final_elements", "line_items", "offpage_connectors"):
        for it in model.get(group, []):
            for prov in it.get("provenance", [])[:1]:
                yield it, prov


def sheet_items(model, sheet):
    """Every appearance on one sheet of a drawing-set bundle (an item can appear on several sheets)."""
    for group in ("units", "instruments", "final_elements", "line_items", "offpage_connectors"):
        for it in model.get(group, []):
            for prov in it.get("provenance", []):
                if prov.get("sheet") == sheet:
                    yield it, prov


def overlay(model, w, h, uri, sheet=None):
    boxes = []
    for it, prov in (items(model) if sheet is None else sheet_items(model, sheet)):
        x1, y1, x2, y2 = prov["box_0_1000"]
        colour = CLASS_COLOURS.get(it.get("class"), "#4b5563")
        label = html.escape(f'{it["id"]}: {it.get("tag") or "no tag"} ({it.get("class")})')
        boxes.append(f'<rect x="{x1 * w / 1000:.1f}" y="{y1 * h / 1000:.1f}" width="{(x2 - x1) * w / 1000:.1f}" '
                     f'height="{(y2 - y1) * h / 1000:.1f}" fill="none" stroke="{colour}" stroke-width="{w / 600:.1f}">'
                     f'<title>{label}</title></rect>')
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="The drawing with every extracted item boxed">'
            f'<image href="{uri}" width="{w}" height="{h}"/>{"".join(boxes)}</svg>')


def hierarchy_html(node, depth=0):
    kids = node.get("children", [])
    tag = node.get("tag") or ("no tag" if node.get("kind") not in ("site", "system") else "")
    name = node.get("name") or ""
    label = " ".join(x for x in (html.escape(node["id"]), html.escape(tag), html.escape(name)) if x)
    if depth >= 2 and not kids:
        return f"<li>{label} <span class=k>{html.escape(node.get('class') or node.get('kind', ''))}</span></li>"
    inner = "".join(hierarchy_html(k, depth + 1) for k in kids + node.get("unassigned", []) +
                    node.get("offpage_connectors", []))
    open_ = " open" if depth < 2 else ""
    return (f"<li><details{open_}><summary>{label} <span class=k>{html.escape(node.get('kind', ''))}"
            f"{', ' + str(len(kids)) + ' below' if kids else ''}</span></summary><ul>{inner}</ul></details></li>")


class BundleError(ValueError):
    pass


SET_SCHEMA = "site-drawing-set-1"


def set_drawings_html(model, intake, bundle, legend):
    """One boxed drawing per sheet of a drawing-set bundle (scripts/import_drawing_set.py)."""
    e = html.escape
    parts = []
    for sh in intake["sheets"]:
        n = sh["internal_sheet"]
        png = (bundle / "source" / f"{n}.png").read_bytes()
        w, h = png_size(png)
        d = sh["drawing"]
        title = f' · {e(sh["title"])}' if sh.get("title") else ""
        parts.append(f'<h3>Sheet {e(n)}: {e(d["drawing_id"])}, revision {e(str(d["revision"]))}, page '
                     f'{e(str(d["page"]))}{title}</h3><figure>{overlay(model, w, h, drawing_uri(png), sheet=n)}'
                     f'<figcaption class=legend>{legend}</figcaption></figure>')
    return "".join(parts)


PAIR_METHODS = {
    "reciprocal_drawing_refs": "each names the other's drawing",
    "one_way_ref_plus_system_code": "one names the other's drawing; system codes agree",
    "reciprocal_supplied_numbers": "each names the other's drawing number",
    "one_way_number_plus_sheet_title": "one names the other's number; the other carries its title",
    "one_way_number_plus_system_code": "one names the other's number; the other carries its system code",
}


def across_sheets_html(model):
    """Cross-sheet pairs and the connectors still unmatched, for a drawing-set bundle."""
    e = html.escape
    connectors = model.get("offpage_connectors", [])
    rows = "".join(
        f'<tr><td>{e(p["id"])}</td><td>sheet {e(p["sheet_a"])}: {e(str(p["text_a"]))}</td>'
        f'<td>sheet {e(p["sheet_b"])}: {e(str(p["text_b"]))}</td><td>{e(PAIR_METHODS.get(p["method"], p["method"]))}</td></tr>'
        for p in model.get("offpage_pairs", []))
    status = Counter(c.get("pair_status") for c in connectors if not c.get("pair"))
    unmatched = "".join(f"<li>{n} × {e(str(k))}</li>" for k, n in status.most_common())
    table = (f'<div class=scroll><table><thead><tr><th>Pair</th><th>From</th><th>To</th><th>Matched by</th></tr>'
             f'</thead><tbody>{rows}</tbody></table></div>') if rows else "<p>No connectors were paired across sheets.</p>"
    count = len(model.get("offpage_pairs", []))
    layers = (model.get("meta") or {}).get("line_layers_status") or {}
    if layers.get("status") == "added":
        lines_note = (f'<p>Drawn line layers: {layers["pipe_segments"]} pipe segments, '
                      f'{layers["instrument_connections"]} instrument connections, {layers["junctions"]} junctions'
                      + (f'; {layers["dropped_inconsistent_lines"]} inconsistent line(s) and '
                         f'{layers.get("dropped_orphan_junctions", 0)} junction(s) left without a line were dropped '
                         '(listed in <code>plant_model.json</code>)' if layers["dropped_inconsistent_lines"] else "")
                      + '.</p>')
    elif layers:
        lines_note = f'<p class=sub>Drawn line layers not added: {e(str(layers.get("reason") or layers.get("status")))}.</p>'
    else:
        lines_note = ""
    return (f'<h2>Across sheets ({count} pair{"" if count == 1 else "s"})</h2><p class=sub>Off-page connectors '
            'matched to a connector on another sheet of this set. Each pair is a candidate for review, not an '
            'established continuation; it is also in <code>review_queue.csv</code>.</p>' + table
            + (f"<p>Not paired:</p><ul>{unmatched}</ul>" if unmatched else "") + lines_note)


MODEL_GROUPS = ("units", "instruments", "final_elements", "line_items", "offpage_connectors", "streams")


def columns(fieldnames):
    """The report needs the sheet scripts/generate.py writes: every column of it, by name."""
    missing = [c for c in TWIN_REVIEW_COLS if c not in (fieldnames or [])]
    if missing:
        raise BundleError(f"review_queue.csv has no {', '.join(missing)} column{'s' if len(missing) > 1 else ''}, so "
                          "it isn't the review sheet scripts/generate.py writes: regenerate the exports with "
                          "scripts/generate.py before making the report")


def consistency(model, rows):
    """The report reads counts and reasons from the review sheet, so the sheet must describe this model, as it is
    now. Every column except the reviewer's OPS_ ones is rewritten from the model by the sheet's own writer
    (generate.twin_review_rows) and compared: an edited reason, a changed tag or a sheet older than the model is
    refused rather than reported."""
    model_ids = {it["id"] for g in MODEL_GROUPS for it in model.get(g, [])}
    queue_ids = {r["item_id"] for r in rows}
    dupes = sorted({r["item_id"] for r in rows if sum(1 for x in rows if x["item_id"] == r["item_id"]) > 1})
    if dupes:  # a repeated row would be counted twice in every headline number
        raise BundleError(f"review_queue.csv lists {len(dupes)} item(s) more than once ({', '.join(dupes[:5])}): "
                          "regenerate the exports with scripts/generate.py before making the report")
    if model_ids != queue_ids:
        raise BundleError(f"review_queue.csv lists {len(queue_ids)} items and plant_model.json {len(model_ids)} "
                          f"({len(model_ids - queue_ids)} missing from the sheet, {len(queue_ids - model_ids)} not in "
                          "the model): regenerate the exports with scripts/generate.py before making the report")
    by_id = {it["id"]: it for g in MODEL_GROUPS for it in model.get(g, [])}
    stale = [r["item_id"] for r in rows if (by_id[r["item_id"]].get("ops_review") or {}).get("status")
             and r.get("model_status") not in (by_id[r["item_id"]]["ops_review"]["status"],)]
    if stale:
        raise BundleError(f"{len(stale)} item(s) were reviewed after review_queue.csv was written (e.g. {stale[0]}): "
                          "regenerate the exports with scripts/generate.py before making the report")
    expected = {r["item_id"]: r for r in csv.DictReader(io.StringIO(
        _csv_text(TWIN_REVIEW_COLS, twin_review_rows(model)).lstrip("\ufeff"), newline=""))}
    differ = [(r["item_id"], c, r.get(c), expected[r["item_id"]][c]) for r in rows for c in TWIN_REVIEW_COLS
              if not c.startswith("OPS_") and r.get(c) != expected[r["item_id"]][c]]
    if differ:
        item, col, has, should = differ[0]
        raise BundleError(f"review_queue.csv doesn't describe plant_model.json as it is now: {len(differ)} cell(s) "
                          f"differ (e.g. {item} {col}: the sheet says {has!r}, the model gives {should!r}); it was "
                          "edited or written from another version of the model: regenerate the exports with "
                          "scripts/generate.py before making the report")


def build(bundle):
    bundle = Path(bundle)
    need = ["plant_model.json", "intake_manifest.json", "review_queue.csv", "READ_ME.txt"]
    missing = [n for n in need if not (bundle / n).is_file()]
    pngs = sorted((bundle / "source").glob("*.png")) if (bundle / "source").is_dir() else []
    if missing or not pngs:
        raise BundleError("not a review bundle from import_site_drawing.py: missing "
                          + ", ".join(missing + ([] if pngs else ["source/*.png"])))
    model = json.loads((bundle / "plant_model.json").read_text(encoding="utf-8"))
    intake = json.loads((bundle / "intake_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(model, dict) or "summary" not in model or "hierarchy" not in model:
        raise BundleError("plant_model.json is not an extracted model (no summary or hierarchy)")
    with open(bundle / "review_queue.csv", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns(reader.fieldnames)
        rows = list(reader)
    consistency(model, rows)
    reviewed = [it for g in MODEL_GROUPS for it in model.get(g, []) if (it.get("ops_review") or {}).get("status")]
    is_set = intake.get("schema_version") == SET_SCHEMA
    png = pngs[0].read_bytes()
    w, h = png_size(png)
    s = model["summary"]
    meta = model["meta"]
    limits = [ln for ln in (bundle / "READ_ME.txt").read_text(encoding="utf-8").splitlines()[1:] if ln.strip()]
    # An applied review record removes an item from the to-check list and is shown, with its attribution, under
    # "Reviewed so far". The sheet's model_status is the model's own (consistency() checked it).
    decided = {r["item_id"]: r for r in rows if r["model_status"] != "unverified"}
    open_rows = [r for r in rows if r["item_id"] not in decided]
    first = [r for r in open_rows if not r["why_check_this"].startswith(ROUTINE)]
    settled = sum(1 for r in decided.values() if not r["why_check_this"].startswith(ROUTINE))
    reasons = Counter(r["why_check_this"].split(";")[0] for r in first)
    kinds = Counter(r["item_type"] for r in rows)
    drawing = intake.get("drawing") or {}
    producer = intake.get("supplied_producer") or intake.get("producer") or {}
    e = html.escape

    def tile(n, label):
        return f'<div class=tile><b>{n:,}</b><span>{e(label)}</span></div>'

    first_rows = "".join(
        f"<tr><td>{e(r['item_id'])}</td><td>{e(r['what_it_is'])}</td><td>{e(r['item_type'])}</td>"
        f"<td>{e(r['why_check_this'])}</td></tr>" for r in first)
    listed = [(("svg/", "One logical diagram per sheet: the extracted items and links, not pipe routes.")
               if is_set and n == "svg/sheet_0.svg" else (n, d)) for n, d in FILES]
    files = "".join(f"<tr><td><code>{e(n)}</code></td><td>{e(d)}</td></tr>" for n, d in listed if (bundle / n).exists())
    legend = "".join(f'<span><i style="border-color:{c}"></i>{e(k)}</span>' for k, c in CLASS_COLOURS.items())
    if is_set:
        heading = e(intake.get("set_id", ""))
        subline = (f'{len(intake["sheets"])} sheets · {e(meta.get("title", ""))} · extraction: '
                   f'{e(producer.get("method", "not stated"))}'
                   + (f' ({e(producer.get("model"))})' if producer.get("model") else ""))
        drawing_section = ('<h2>The drawings, with what was extracted</h2>'
                           f'{set_drawings_html(model, intake, bundle, legend)}<p class=sub>Each box is one '
                           "extracted item, coloured by class; hover for its id and tag. Links aren't drawn here "
                           '(see <code>svg/</code>).</p>' + across_sheets_html(model))
    else:
        heading = e(drawing.get('drawing_id', meta.get('source_document', '')))
        subline = (f"Revision {e(str(drawing.get('revision', '?')))}, page {e(str(drawing.get('page', '?')))} ·\n"
                   f"{e(meta.get('title', ''))} · extraction: {e(producer.get('method', 'not stated'))}\n"
                   + (('(' + e(producer.get('model')) + ')') if producer.get('model') else ''))
        drawing_section = (f"<h2>The drawing, with what was extracted</h2>\n<figure>{overlay(model, w, h, drawing_uri(png))}\n"
                           f"<figcaption class=legend>{legend}</figcaption></figure>\n<p class=sub>Each box is one "
                           "extracted item, coloured by class; hover for its id and tag. Links aren't drawn here\n"
                           "(see <code>svg/sheet_0.svg</code>).</p>")
    reason_list = "".join(f"<li>{n} × {e(k)}</li>" for k, n in reasons.most_common())
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Draft asset model report</title>
<style>
:root{{--bg:#fafaf9;--fg:#1c1917;--mute:#57534e;--line:#e7e5e4;--card:#fff;--warn:#92400e;--warnbg:#fef3c7}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1c1917;--fg:#f5f5f4;--mute:#a8a29e;--line:#44403c;--card:#292524;
--warn:#fcd34d;--warnbg:#451a03}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 64px}}h1{{font-size:26px;margin:0 0 4px}}
h2{{font-size:18px;margin:36px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}}
.sub{{color:var(--mute)}}.draft{{background:var(--warnbg);color:var(--warn);padding:10px 14px;border-radius:6px;
margin:16px 0}}.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}}
.tile{{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 12px}}
.tile b{{display:block;font-size:22px}}.tile span{{color:var(--mute);font-size:13px}}
figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px}}
figure svg{{width:100%;height:auto;display:block}}.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;
color:var(--mute);margin-top:6px}}.legend i{{display:inline-block;width:12px;height:12px;border:2px solid;
margin-right:5px;vertical-align:-1px}}table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--mute);font-weight:600}}.scroll{{overflow-x:auto}}ul.tree,ul.tree ul{{list-style:none;padding-left:18px}}
ul.tree{{padding-left:0;font-size:14px}}.k{{color:var(--mute);font-size:12px}}code{{font-size:13px}}
ol li,ul li{{margin:3px 0}}
</style></head><body><main>
<h1>Draft asset model: {heading}</h1>
<div class=sub>{subline}</div>
<p>This bundle is a structural starting point for a digital twin of the process represented by the drawing:
assets, represented connections and their source locations, ready for engineering review. Use the same intake
and review tools with your approved P&amp;ID and extraction to build from your plant's records. Add operating
knowledge, retained decisions and reviewed signal mappings as the application develops.</p>
{('<div class=draft><b>Draft, unverified.</b> Items were imported from the supplied extraction; no completed '
  'review is recorded here. Nothing here is approved for operational use.</div>') if not reviewed else
 ('<div class=draft><b>Draft, partly reviewed.</b> ' + f'{len(reviewed)} of {len(rows)} items carry supplied '
  'review records (listed below); the remainder have no completed review recorded here. Nothing here is '
  'approved for operational use.</div>')}

<h2>What was extracted</h2>
<div class=tiles>{tile(s['equipment'], 'equipment')}{tile(s['instruments'], 'instruments')}
{tile(kinds.get('valve', 0), 'valves')}{tile(kinds.get('in-line item', 0), 'other in-line items')}
{tile(s['offpage_connectors'], 'off-page connectors')}{tile(s['streams_extracted'], 'links between items')}
{tile(len(open_rows), 'rows still to review' if decided else 'rows to review')}{tile(len(first), 'to check first')}</div>

{drawing_section}

{reviewed_html(reviewed, decided)}
<h2>Check these first ({len(first)} of {len(open_rows)} rows{' still to review' if decided else ''})</h2>
<p>The software flagged these for a specific reason; the rest are routine checks (does this line exist, is this
item right).{f' {settled} flagged item(s) already have a decision and are listed above instead.' if settled else ''}
Reasons:</p><ul>{reason_list}</ul>
<div class=scroll><table><thead><tr><th>Item</th><th>What it is</th><th>Type</th><th>Why check it</th></tr></thead>
<tbody>{first_rows}</tbody></table></div>

<h2>Asset hierarchy</h2>
<p class=sub>Instruments are attached to the nearest line item or equipment; {s['instrument_parent_method'].get('linked', 0)}
by a drawn link and {s['instrument_parent_method'].get('geometry_nearest', 0)} by distance alone, which needs a closer look.</p>
<ul class=tree>{hierarchy_html(model['hierarchy'])}</ul>

<h2>What's in the package</h2>
<div class=scroll><table><tbody>{files}</tbody></table></div>

<h2>Build on this model</h2>
<ol><li>A reviewer who knows the unit works through <code>review_queue.csv</code>, starting with the rows above, and
fills the <code>OPS_</code> columns.</li>
<li>Apply supported corrections with <code>apply_review.py</code>, inspect the change record and regenerate exports
with <code>generate.py</code>. Missing items need a corrected extraction and a new bundle.</li>
<li>For an investigation, run <code>question_engine.py</code> on <code>plant_model.json</code> and choose a relevant
question. Export the model and questions with <code>graph_export.py</code>; the context-register tools can retain
source revisions and reviewed answers. These are optional next outputs, not files already in this bundle.</li>
<li>For a data-connected application, supply an authoritative I/O list to <code>map_points.py</code> or reviewed
PI references to <code>map_pi_points.py</code>, then regenerate. Import the selected staging files into the approved
lab target and verify signal identity, values, units and quality. Author the displays and connections the job needs.</li></ol>
<p class=sub>The repository's <code>examples/own-drawing/README.md</code> gives the commands and own-input steps.
The assembled public replay and screen projects illustrate further application work.</p>

<h2>What this package does not establish</h2>
<ul>{''.join(f'<li>{e(x)}</li>' for x in limits)}</ul>
<p class=sub>Generated by <code>scripts/deliverable_report.py</code> from the bundle's own files.</p>
</main></body></html>
"""


def reviewed_html(reviewed, decided):
    """Items with applied review records: decision, supplied attribution and what the sheet now says."""
    if not reviewed:
        return ""
    e = html.escape
    rows = "".join(f"<tr><td>{e(it['id'])}</td><td>{e(str(it.get('tag') or 'no tag'))}</td>"
                   f"<td>{e(it['ops_review']['status'])}</td><td>{e(str(it['ops_review'].get('by') or ''))}</td>"
                   f"<td>{e(str(it['ops_review'].get('on') or ''))}</td><td>{e(str(it['ops_review'].get('notes') or ''))}</td>"
                   f"<td>{e(decided[it['id']]['why_check_this'])}</td></tr>"
                   for it in reviewed)
    return (f"<h2>Reviewed so far ({len(reviewed)})</h2><p class=sub>These recorded decisions are shown with their "
            "supplied reviewer and date; attribution is not authentication. They are left out of the list to check "
            "below.</p><div class=scroll><table><thead><tr><th>Item</th><th>Tag now</th>"
            "<th>Decision</th><th>By</th><th>On</th><th>Notes</th><th>The sheet now says</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div>")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):  # a Windows console is cp1252: print arrows and units, don't crash
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else Path(a.bundle) / "REPORT.html"
    try:
        text = build(a.bundle)
        bundle = Path(a.bundle)
        sources = [bundle / name for name in ("plant_model.json", "intake_manifest.json",
                                              "review_queue.csv", "READ_ME.txt")]
        # source/ holds the preserved originals, including extraction records not rendered in the HTML.
        sources.extend(p for p in (bundle / "source").rglob("*") if p.is_file())
        protect_outputs([out], sources)
        out.write_text(text, encoding="utf-8", newline="\n")
    except BundleError as exc:
        print(f"{a.bundle}: {exc}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError) as exc:
        print(f"{a.bundle}: can't read the bundle ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 1
    print(f"wrote {out} ({len(text) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
