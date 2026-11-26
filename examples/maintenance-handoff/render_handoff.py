"""One self-contained web page for a replaced asset: what each record says, where the records disagree,
which field ruling was applied, and what is still waiting for a correction.

Reads the 'after' folder that `scripts/one_map.py build` wrote (graph.json and queues/review_queue.csv) and
writes one HTML file: no network, no scripts, no external styles or fonts. Standard library only. Read-only
with respect to the inputs; the page restates the build's records and rulings and decides nothing itself.

  python examples/maintenance-handoff/render_handoff.py --after out/maintenance-handoff/after --tag FDV-2210 \
      --out out/maintenance-handoff/HANDOFF.html
"""
import argparse
import csv
import html
import json
import sys
from pathlib import Path

# (label shown to the reader, attribute name on the equipment record, field name on a work order)
FIELDS = (
    ("Maker", "manufacturer", "installed_manufacturer"),
    ("Model", "model", "installed_model"),
    ("Serial number", "serial_number", "installed_serial_number"),
    ("Size", "size", "installed_size"),
    ("Body material", "body_material", None),
)
KIND_TITLES = {"work_order": "Closed work order", "cmms": "Equipment export", "datasheet": "Valve datasheet",
               "drawing": "P&ID drawing"}

CSS = """
body{font:16px/1.5 Segoe UI,Helvetica,Arial,sans-serif;color:#1d2733;background:#f5f6f8;margin:0;padding:24px}
main{max-width:1060px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:30px 0 8px}
.sub{color:#4a5666;margin:0 0 14px}
.note{background:#fff8e1;border:1px solid #e6d28a;border-radius:6px;padding:8px 12px;font-size:14px}
table{border-collapse:collapse;width:100%;background:#fff;border:1px solid #cfd6df}
th,td{border:1px solid #cfd6df;padding:8px 10px;vertical-align:top;text-align:left}
th{background:#e9edf2;font-size:14px} th small{display:block;font-weight:400;color:#4a5666}
td.field{font-weight:600;white-space:nowrap}
.val{font-size:17px;font-weight:600} .src{display:block;font-size:12px;color:#5a6676;word-break:break-all}
.none{color:#8a94a2;font-style:italic}
td.differs{background:#fdeaea;box-shadow:inset 4px 0 0 #c62828}
td.old{background:#fff1dc;box-shadow:inset 4px 0 0 #e08a00}
td.good{background:#e6f4ea;box-shadow:inset 4px 0 0 #2e7d32}
.tag{display:inline-block;font-size:12px;font-weight:700;border-radius:10px;padding:1px 8px;margin-top:3px}
.t-red{background:#c62828;color:#fff} .t-amber{background:#b26a00;color:#fff} .t-green{background:#2e7d32;color:#fff}
.t-grey{background:#d5dae1;color:#1d2733}
.card{background:#fff;border:1px solid #cfd6df;border-radius:6px;padding:10px 14px;margin:8px 0}
.card.open{border-left:6px solid #c62828} .card.fix{border-left:6px solid #e08a00} .card.ruling{border-left:6px solid #2e7d32}
.card.decide{border-left:6px solid #5a6676}
.who{font-weight:700} .card p{margin:4px 0}
footer{margin-top:28px;font-size:13px;color:#4a5666}
"""


def e(text):
    return html.escape("" if text is None else str(text))


def source_line(src):
    """'document · file path · row or zone', as far as the record says."""
    if not src:
        return ""
    sheet = f"sheet {src['sheet']} rev {src.get('revision', '?')}" if src.get("sheet") else ""
    return " · ".join(x for x in (src.get("document"), src.get("path"), sheet, src.get("locator")) if x)


def collect(graph, tag):
    """Group what each source says about one tag: {kind: {"title","document","source","values"}}."""
    node = next((n for n in graph["nodes"] if n.get("tag") == tag and n.get("kind") != "conflict"), None)
    if node is None:
        raise SystemExit(f"no item tagged {tag} in this graph")
    cols = {}
    for att in node.get("attributes", []):
        src = att.get("source") or {}
        doc = src.get("document", "")
        kind = "datasheet" if "DATASHEET" in doc.upper() else "cmms"
        col = cols.setdefault(kind, {"document": doc, "source": src, "values": {}})
        col["values"][att["name"]] = (att["value"], source_line(src))
    for rec in graph.get("records", {}).get("work_order", []):
        if rec.get("item") == node["id"]:
            v, src = rec["values"], rec.get("source") or {}
            col = cols.setdefault("work_order", {"document": src.get("document", ""), "source": src, "values": {},
                                                 "note": f"{rec['id']}, closed {v.get('closed_on', '?')}"})
            for _, attr, wo_field in FIELDS:
                if wo_field and v.get(wo_field):
                    col["values"][attr] = (v[wo_field], source_line(src))
    for app in node.get("appearances", []):
        if app.get("printed"):
            col = cols.setdefault("drawing", {"document": app.get("document", ""), "source": app, "values": {},
                                              "note": f"sheet {app.get('sheet', '')} rev {app.get('revision', '')}"})
            for attr, value in app["printed"].items():
                col["values"][attr] = (value, source_line(app) + (f", zone {app['zone']}" if app.get("zone") else ""))
    conflicts = [n["conflict"] for n in graph["nodes"]
                 if n.get("kind") == "conflict" and n["conflict"].get("subject") == node["id"]]
    return node, cols, conflicts


def read_queue(after, node_id):
    path = after / "queues" / "review_queue.csv"
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["item"] == node_id]


def render(graph, queue_rows, tag):
    node, cols, conflicts = collect(graph, tag)
    order = [k for k in ("work_order", "cmms", "datasheet", "drawing") if k in cols]
    ruled = {c["attribute"]: c["history"][-1] for c in conflicts
             if c.get("status") == "resolved" and c.get("history")}
    head = "".join(
        f"<th>{e(KIND_TITLES[k])}<small>{e(cols[k]['document'])}"
        f"{(' · ' + e(cols[k]['note'])) if cols[k].get('note') else ''}</small></th>" for k in order)
    rows, open_fields = [], []
    for label, attr, _ in FIELDS:
        seen = {cols[k]["values"][attr][0] for k in order if attr in cols[k]["values"]}
        if not seen:
            continue
        ruling = ruled.get(attr)
        disagree = len(seen) > 1
        if disagree and ruling:
            state = f'<span class="tag t-green">settled by field ruling: {e(ruling["chosen_value"])}</span>'
        elif disagree:
            state = '<span class="tag t-red">records disagree</span>'
            open_fields.append(label)
        else:
            state = '<span class="tag t-grey">records agree</span>'
        cells = []
        for k in order:
            got = cols[k]["values"].get(attr)
            if got is None:
                cells.append('<td><span class="none">not recorded here</span></td>')
                continue
            value, where = got
            cls, extra = "", ""
            if disagree and ruling:
                if value == ruling["chosen_value"]:
                    cls = "good"
                else:
                    cls, extra = "old", '<span class="tag t-amber">out of date: needs correcting</span>'
            elif disagree:
                cls = "differs"
            cells.append(f'<td class="{cls}"><span class="val">{e(value)}</span>{extra}'
                         f'<span class="src">{e(where)}</span></td>')
        rows.append(f'<tr><td class="field">{e(label)}<br>{state}</td>{"".join(cells)}</tr>')

    ruling_cards = []
    for c in conflicts:
        for h in c.get("history", []):
            ruling_cards.append(
                f'<div class="card ruling"><p><span class="who">Field ruling {e(h.get("ruling_id", ""))} applied</span> '
                f'to the {e(c["attribute"].replace("_", " "))}: the valve is <b>{e(h.get("chosen_value", ""))}</b>.</p>'
                f'<p>{e(h.get("note", ""))}</p>'
                f'<p class="src">By {e(h.get("by", ""))} on {e(h.get("on", ""))} · evidence: {e(h.get("evidence", ""))}'
                f' (named in the ruling, not included in this example)</p>'
                f'<p>The records said {e(c["source_a"]["says"])} ({e(c["source_a"]["source"].get("document"))}) '
                f'and {e(c["source_b"]["says"])} ({e(c["source_b"]["source"].get("document"))}). '
                f'The ruling picks one; it does not change the other record.</p></div>')

    todo = []
    for c in conflicts:
        h = (c.get("history") or [None])[-1]
        if h and c.get("status") == "resolved":
            b = c["source_b"] if c["source_b"]["says"] != h["chosen_value"] else c["source_a"]
            todo.append(("fix", c.get("record_owner", "record owner"),
                         f"Change the {c['attribute'].replace('_', ' ')} in {b['source'].get('document')} "
                         f"({b['source'].get('locator', '')}) from {b['says']} to {h['chosen_value']}.",
                         "Decided by the field ruling above; only the record itself is still wrong."))
    for row in queue_rows:
        kind = row["kind"]
        if kind == "replacement may not be like-for-like":
            todo.append(("open", row["owner"], "Settle size: the closed work order says DN65 was installed, "
                         "the valve datasheet still says DN50.",
                         "Open. The ruling above did not cover size. Someone who knows the design checks which "
                         "is right, then corrects the datasheet or the installation."))
        elif kind == "P&ID value note":
            todo.append(("fix", row["owner"], "P&ID sheet prints DN65 while the datasheet says DN50.",
                         "Reference only. If DN65 turns out to be wrong, correct the drawing at its next revision."))
    cards = "".join(
        f'<div class="card {css}"><p><span class="who">{e(owner)}</span> · {e(what)}</p><p class="src">{e(why)}</p></div>'
        for css, owner, what, why in todo) or '<p class="none">Nothing waiting.</p>'
    decide = ""
    if any(r["kind"] == "replacement may not be like-for-like" for r in queue_rows):
        decide = ('<div class="card decide"><p><span class="who">Not decided here</span> · Whether this replacement needs a '
                  'management of change (MOC) review. A size that differs from the datasheet is a reason to ask, '
                  'not an answer. Engineering owns that call.</p></div>')
    title = f"{tag} {node.get('name', '')}".strip()
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{e(title)}: do the records agree?</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head>
<body><main>
<h1>{e(title)}: do the records agree after the replacement?</h1>
<p class="sub">Site: {e(graph.get("title") or graph.get("site", ""))}. Each box shows what one record says, and which file it came from.</p>
<p class="note">Fictional example. The ruling is supplied sample data, not a real company approval.</p>
<h2>What each record says</h2>
<table><thead><tr><th>Detail</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>
<p class="src">Red: records disagree and nothing has settled it. Orange: out of date after a ruling. Green: matches the ruling.</p>
<h2>Ruling applied</h2>
{"".join(ruling_cards) or '<p class="none">No ruling recorded.</p>'}
<h2>Still needs a correction, and who owns it</h2>
{cards}
{decide}
<footer>Built from {e(graph.get("source_model", "the build output"))} by render_handoff.py. It only restates the records and rulings
it was given; people decide what is correct. Open details: {e(", ".join(open_fields) or "none")}.</footer>
</main></body></html>
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--after", type=Path, required=True, help="folder written by one_map.py build (has graph.json)")
    ap.add_argument("--tag", default="FDV-2210")
    ap.add_argument("--out", type=Path, required=True, help="HTML file to write")
    a = ap.parse_args(argv)
    graph_path = a.after / "graph.json"
    if not graph_path.is_file():
        print(f"missing {graph_path}; run the build step first", file=sys.stderr)
        return 2
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    node_id = next((n["id"] for n in graph["nodes"] if n.get("tag") == a.tag and n.get("kind") != "conflict"), None)
    page = render(graph, read_queue(a.after, node_id), a.tag)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
