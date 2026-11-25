"""Offline review page: confirm, correct or reject a drawing's extracted items without a spreadsheet.

    python -S scripts/review_page.py my-bundle                      # writes my-bundle/review.html
    python -S scripts/review_page.py my-bundle --out review.html

Reads the bundle that import_site_drawing.py writes (review_queue.csv, plant_model.json, source/<sheet>.png) and
writes ONE self-contained HTML file: inline CSS and JavaScript, the drawing embedded as a data URI, no network.
Open it in any browser. Each queue item shows a crop of the drawing with its box, what was extracted and why it is
worth a look, and three buttons: Confirm (key 1), Correct (2), Reject (3); J/K move. Decisions are kept in the
browser's local storage, keyed by the bundle's content hash, so closing the tab loses nothing. Nothing leaves the
computer: the page makes no request.

"Download decisions" writes review_decisions.csv: review_queue.csv with the OPS_ columns filled in the format
scripts/apply_review.py reads (OPS_confirm_or_correct = confirm | correct | reject; OPS_correct_value =
"field=value; field=value"; OPS_notes = the note). Then, from the repository root:

    python scripts/apply_review.py my-bundle/plant_model.json review_decisions.csv --reviewer "Name, role" --dry-run

Queue order: items marked safety-relevant first, then the queue's own order (the risk tier when a rating exists,
otherwise the existing check-first order of scripts/generate.py). Every row of the queue is in the page. The page
adds no judgement of its own and the reviewed bundle stays a draft.

Like deliverable_report.py, it refuses a review_queue.csv that does not describe plant_model.json as it is now.
decisions_csv() below is the reference writer for the download format; the page's JavaScript mirrors it and the
tests compare the two.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deliverable_report import BundleError, columns, consistency, png_size  # noqa: E402
from output_paths import protect_outputs  # noqa: E402

OPS = ("OPS_confirm_or_correct", "OPS_correct_value", "OPS_notes")
DECISIONS = ("confirm", "correct", "reject")
MAX_EMBED_BYTES = 3_500_000  # a larger drawing is reduced (when Pillow is installed) so the page stays light
MAX_EMBED_WIDTH = 3000


def sheet_image(png_bytes):
    """(width, height, data URI) of a sheet image as embedded. The box coordinates are 0-1000 fractions of the
    sheet, so a reduced image keeps every box in place."""
    w, h = png_size(png_bytes)
    if len(png_bytes) > MAX_EMBED_BYTES and w > MAX_EMBED_WIDTH:
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            im = im.resize((MAX_EMBED_WIDTH, round(im.height * MAX_EMBED_WIDTH / im.width)))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=88)
            return im.width, im.height, "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            pass
    return w, h, "data:image/png;base64," + base64.b64encode(png_bytes).decode()


def decisions_csv(cols, rows, decisions):
    """The download format. `rows` are review_queue.csv rows (lists in `cols` order); `decisions` maps item_id to
    {"d": confirm|correct|reject|"", "v": [[field, value], ...], "n": note}. Every row is written, undecided ones
    unchanged; a Correct without a value is left blank (apply_review.py would refuse it)."""
    ix = {c: i for i, c in enumerate(cols)}
    out = io.StringIO(newline="")
    out.write("﻿")
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(cols)
    for row in rows:
        row = list(row)
        d = decisions.get(row[ix["item_id"]]) or {}
        kind, note = d.get("d") or "", (d.get("n") or "").strip()
        pairs = [(f, v.strip()) for f, v in d.get("v") or [] if f and v.strip()]
        if kind == "correct" and not pairs:
            kind = ""
        if kind:
            row[ix["OPS_confirm_or_correct"]] = kind
            row[ix["OPS_correct_value"]] = "; ".join(f"{f}={v}" for f, v in pairs) if kind == "correct" else ""
        if note:
            row[ix["OPS_notes"]] = note
        w.writerow(row)
    return out.getvalue()


def bundle_hash(bundle):
    h = hashlib.sha256()
    for name in ("review_queue.csv", "plant_model.json"):
        h.update((bundle / name).read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def payload(bundle):
    bundle = Path(bundle)
    missing = [n for n in ("plant_model.json", "review_queue.csv") if not (bundle / n).is_file()]
    src = bundle / "source"
    pngs = sorted(src.glob("*.png")) if src.is_dir() else []
    if missing or not pngs:
        raise BundleError("not a review bundle from import_site_drawing.py: missing "
                          + ", ".join(missing + ([] if pngs else ["source/*.png"])))
    model = json.loads((bundle / "plant_model.json").read_text(encoding="utf-8"))
    if not isinstance(model, dict) or "summary" not in model or "hierarchy" not in model:
        raise BundleError("plant_model.json is not an extracted model (no summary or hierarchy)")
    with open(bundle / "review_queue.csv", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        cols = next(reader, [])
        rows = list(reader)
    with open(bundle / "review_queue.csv", encoding="utf-8-sig", newline="") as f:
        dict_reader = csv.DictReader(f)
        columns(dict_reader.fieldnames)
        consistency(model, list(dict_reader))
    missing_ops = [c for c in OPS if c not in cols]
    if missing_ops or "item_id" not in cols:
        raise BundleError("review_queue.csv has no " + ", ".join(missing_ops or ["item_id"]) + " column")
    sheets = {}
    for p in pngs:
        w, h, uri = sheet_image(p.read_bytes())
        sheets[p.stem] = {"w": w, "h": h, "uri": uri}
    return {"cols": cols, "rows": rows, "sheets": sheets, "hash": bundle_hash(bundle),
            "bundle": bundle.name, "title": (model.get("site") or {}).get("name") if isinstance(model.get("site"), dict) else None}


def render(data):
    text = json.dumps(data, ensure_ascii=True, sort_keys=True, allow_nan=False)
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return PAGE.replace("__REVIEW_DATA__", text)


def build(bundle):
    return render(payload(bundle))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else Path(a.bundle) / "review.html"
    try:
        text = build(a.bundle)
        bundle = Path(a.bundle)
        sources = [bundle / n for n in ("plant_model.json", "review_queue.csv")]
        sources.extend(p for p in (bundle / "source").rglob("*") if p.is_file())
        protect_outputs([out], sources)
        out.write_text(text, encoding="utf-8", newline="\n")
    except BundleError as exc:
        print(f"{a.bundle}: {exc}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError) as exc:
        print(f"{a.bundle}: can't read the bundle ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 1
    print(f"wrote {out} ({len(text) // 1024} KB); open it in a browser. Nothing leaves your computer.")
    return 0


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Review the extracted items</title><style>
:root{font:16px/1.45 system-ui,sans-serif;color:#1d2b33;background:#eef2f4}*{box-sizing:border-box}body{margin:0}
header{background:#193d48;color:#fff;padding:.7rem max(1rem,3vw)}header h1{font-size:1.25rem;margin:0}header p{margin:.15rem 0 0;font-size:.9rem;color:#cfe0e6}
#bar{height:.5rem;background:#2d5766;border-radius:4px;margin:.5rem 0 .2rem;overflow:hidden}#fill{height:100%;width:0;background:#6fd0a0}
main{display:grid;grid-template-columns:19rem minmax(0,1fr);gap:1rem;padding:1rem max(1rem,3vw);max-width:1500px;margin:auto}
aside,section.card{background:#fff;border-radius:6px;padding:.9rem;min-width:0}aside{align-self:start;position:sticky;top:.5rem}
label{display:block;font-size:.85rem;margin:.5rem 0 .15rem;color:#40525d}input,select,textarea,button{font:inherit;border:1px solid #7b929e;border-radius:4px;padding:.4rem .5rem;max-width:100%}
input,select,textarea{width:100%}textarea{min-height:3.2rem}
button{cursor:pointer;background:#eaf3f6;color:#173d50}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #40849c;outline-offset:2px}
#list{display:grid;gap:.25rem;max-height:52vh;overflow:auto;margin-top:.5rem}#list button{text-align:left;padding:.3rem .45rem;font-size:.85rem;overflow-wrap:anywhere;border-left:5px solid #c4d0d6}
#list button.cur{outline:2px solid #177484}#list .confirm{border-left-color:#2e9e62}#list .correct{border-left-color:#d38b10}#list .reject{border-left-color:#c13b3b}#list .earlier{border-left-style:dotted}
#crop{width:100%;max-height:58vh;background:#dfe6ea;border:1px solid #b7c5cc;display:block}
.facts{display:grid;grid-template-columns:max-content 1fr;gap:.15rem .8rem;margin:.6rem 0;font-size:.92rem}.facts dt{color:#516670}.facts dd{margin:0;overflow-wrap:anywhere}
.why{padding:.5rem .7rem;background:#fff6e4;border-left:4px solid #c58a1d;margin:.6rem 0;overflow-wrap:anywhere}.why.safe{background:#fde9e7;border-left-color:#b3261e}
.act{display:flex;flex-wrap:wrap;gap:.5rem;margin:.7rem 0}.act button{padding:.65rem 1.1rem;font-weight:600;min-width:8.5rem}
.act button kbd,.keys kbd{font:inherit;font-size:.8rem;background:#fff;border:1px solid #8aa;border-radius:3px;padding:0 .3rem;margin-right:.35rem;color:#173d50}
.act button[aria-pressed=true].confirm{background:#2e9e62;color:#fff}.act button[aria-pressed=true].correct{background:#d38b10;color:#fff}.act button[aria-pressed=true].reject{background:#c13b3b;color:#fff}
#fixes{margin:.4rem 0}.fix{display:grid;grid-template-columns:9rem 1fr;gap:.4rem;margin:.3rem 0}.small{font-size:.85rem;color:#516670}.err{color:#a3221b;font-size:.9rem}
.row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}.note{margin:.7rem 0;padding:.5rem .7rem;background:#e8f3ee;border-left:4px solid #2e9e62;font-size:.92rem}
.keys{font-size:.85rem;color:#516670;margin-top:.6rem}.badge{display:inline-block;font-size:.78rem;padding:.05rem .4rem;border-radius:3px;background:#e1e8ec;margin-right:.3rem}.badge.s{background:#b3261e;color:#fff}
#dl{background:#193d48;color:#fff;font-weight:600}#cmd{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.82rem;background:#f2f5f7;padding:.5rem;margin:.4rem 0}
@media(max-width:820px){main{display:block}aside{position:static;margin-bottom:1rem}#list{max-height:11rem}.act button{flex:1}}
</style></head><body>
<header><h1>Review the extracted items</h1>
<p>Nothing leaves this computer: the page makes no network request, and your decisions stay in this browser until you download them.</p>
<div id="bar" aria-hidden="true"><div id="fill"></div></div><p id="progress" role="status" aria-live="polite"></p></header>
<main><aside>
<label for="f-show">Show</label><select id="f-show"><option value="all">All items</option><option value="todo">To do (no decision yet)</option><option value="done">Decided here</option><option value="safety">Safety-relevant only</option></select>
<label for="f-type">Type</label><select id="f-type"></select>
<div id="tier-box"><label for="f-tier">Risk tier</label><select id="f-tier"></select></div>
<label for="f-text">Find</label><input id="f-text" type="search" placeholder="item id or name">
<p id="count" class="small" aria-live="polite"></p><div id="list"></div>
<hr><div class="row"><button id="dl" type="button">Download decisions</button></div><p id="dlmsg" class="small" role="status"></p>
</aside>
<section class="card" id="card"><p id="empty" hidden>No item matches this filter.</p><div id="item">
<svg id="crop" role="img" aria-label="The drawing around the item, with its box drawn"></svg>
<div class="row"><button id="whole" type="button">Show whole sheet</button><span id="nobox" class="small"></span></div>
<h2 id="title"></h2><div id="badges"></div>
<div class="why" id="why"></div>
<dl class="facts" id="facts"></dl>
<div class="act" role="group" aria-label="Decision">
<button type="button" class="confirm" data-d="confirm" aria-pressed="false"><kbd>1</kbd>Confirm</button>
<button type="button" class="correct" data-d="correct" aria-pressed="false"><kbd>2</kbd>Correct</button>
<button type="button" class="reject" data-d="reject" aria-pressed="false"><kbd>3</kbd>Reject</button>
<button type="button" id="clear"><kbd>0</kbd>Clear</button></div>
<div id="fixes" hidden><p class="small">Type the corrected value. Add another field only if more than one thing is wrong.</p><div id="fixrows"></div><button type="button" id="addfix">Add another field</button><p class="err" id="fixerr"></p></div>
<label for="note">Note (optional)</label><textarea id="note" maxlength="2000"></textarea>
<div class="row"><button type="button" id="prev">Previous (K)</button><button type="button" id="next">Next (J)</button></div>
<p class="keys"><kbd>1</kbd> confirm <kbd>2</kbd> correct <kbd>3</kbd> reject <kbd>J</kbd> next <kbd>K</kbd> previous <kbd>0</kbd> clear. Confirm and Reject move on by themselves. Keys are off while you type in a box; press Esc to leave it.</p>
</div>
<div class="note" id="after" hidden><b>Next step.</b> Keep the file you downloaded, then run this from the toolkit folder (the first line only previews what would change):<div id="cmd"></div></div>
</section></main>
<script id="review-data" type="application/json">__REVIEW_DATA__</script><script>
'use strict';
const D=JSON.parse(document.getElementById('review-data').textContent);
const $=id=>document.getElementById(id);
const C={};D.cols.forEach((c,i)=>C[c]=i);
const EDIT=['tag','name','description','uom','class','unit','parent','from','to','variable','text'];
const KEY='icp-review:'+D.hash;
const ROUTINE=['routine check','check the line exists'];
let dec={};try{dec=JSON.parse(localStorage.getItem(KEY)||'{}')||{};}catch(e){dec={};}
function save(){try{localStorage.setItem(KEY,JSON.stringify(dec));}catch(e){}}
function el(t,txt,cls){const n=document.createElement(t);if(txt!==undefined)n.textContent=txt;if(cls)n.className=cls;return n;}
const f=(r,c)=>(r[C[c]]===undefined?'':r[C[c]]);
const isSafety=r=>/safety-relevant/i.test(f(r,'why_check_this'))||/safety-relevant/i.test(f(r,'why'));
const isConn=r=>f(r,'item_type')==='connection';
const earlier=r=>{const s=f(r,'model_status');return s&&s!=='unverified';};
const TIER={red:0,amber:1,green:2};
// Queue order: safety items first, then the queue's own order (risk tier, else its check-first order).
const rows=D.rows.map((r,i)=>({r,i})).sort((a,b)=>{
  const sa=isSafety(a.r)?0:1,sb=isSafety(b.r)?0:1;if(sa!==sb)return sa-sb;return a.i-b.i;}).map(x=>x.r);
const byId={};rows.forEach(r=>{byId[f(r,'item_id')]=r;});
const P=s=>String(s).trim().split(/\s+/).map(Number);
function boxOf(r){const p=P(f(r,'location_on_sheet_0_1000'));return p.length===4&&p.every(isFinite)&&f(r,'location_on_sheet_0_1000').trim()?p:null;}
function boxesOf(r){
  if(!isConn(r)){const b=boxOf(r);return b?[b]:[];}
  const m=/^connection:\s*(.+?)\s+-\s+(.+)$/.exec(f(r,'what_it_is'));if(!m)return[];
  return [m[1],m[2]].map(id=>byId[id]).filter(Boolean).map(boxOf).filter(Boolean);}
// sheet images, defined once and referenced by every crop
// SVG elements come from the HTML parser, which sets their namespace: the page names no URL anywhere.
const S=t=>{const d=document.createElement('div');d.innerHTML='<svg><'+t+'></'+t+'></svg>';return d.firstChild.firstChild;};
const defs=S('svg');defs.setAttribute('width','0');defs.setAttribute('height','0');defs.style.position='absolute';
const dd=S('defs');defs.append(dd);
for(const [name,s] of Object.entries(D.sheets)){const im=S('image');im.setAttribute('id','sheet-'+name);im.setAttribute('href',s.uri);im.setAttribute('width',s.w);im.setAttribute('height',s.h);dd.append(im);}
document.body.append(defs);
const sheetOf=r=>D.sheets[f(r,'sheet')]||D.sheets[Object.keys(D.sheets)[0]];
const sheetName=r=>D.sheets[f(r,'sheet')]?f(r,'sheet'):Object.keys(D.sheets)[0];
let cur=rows.length?f(rows[0],'item_id'):null,whole=false,pendingFocus=false;
function status(r){return dec[f(r,'item_id')]||{};}
const decided=r=>!!status(r).d;
function visible(){
  const show=$('f-show').value,type=$('f-type').value,tier=$('f-tier').value,q=$('f-text').value.trim().toLowerCase();
  return rows.filter(r=>{
    if(show==='todo'&&decided(r))return false;if(show==='done'&&!decided(r))return false;if(show==='safety'&&!isSafety(r))return false;
    if(type&&f(r,'item_type')!==type)return false;if(tier&&(f(r,'tier')||'(none)')!==tier)return false;
    if(q&&!(f(r,'item_id')+' '+f(r,'what_it_is')).toLowerCase().includes(q))return false;return true;});}
function setupFilters(){
  const types=[...new Set(rows.map(r=>f(r,'item_type')))].sort();
  $('f-type').append(new Option('All types',''));types.forEach(t=>$('f-type').append(new Option(t+' ('+rows.filter(r=>f(r,'item_type')===t).length+')',t)));
  const tiers=[...new Set(rows.map(r=>f(r,'tier')||'(none)'))];
  if(tiers.length===1&&tiers[0]==='(none)')$('tier-box').hidden=true;
  $('f-tier').append(new Option('All tiers',''));tiers.sort().forEach(t=>$('f-tier').append(new Option(t,t)));}
function cropBox(r,boxes,sh){
  const W=sh.w,H=sh.h;let x1=1e9,y1=1e9,x2=-1e9,y2=-1e9;
  for(const b of boxes){x1=Math.min(x1,b[0]);y1=Math.min(y1,b[1]);x2=Math.max(x2,b[2]);y2=Math.max(y2,b[3]);}
  let w=(x2-x1)*W/1000,h=(y2-y1)*H/1000,cx=(x1+x2)/2*W/1000,cy=(y1+y2)/2*H/1000;
  w=Math.max(w*3,W*0.16);h=Math.max(h*3,H*0.16);
  if(w<h*1.3)w=h*1.3;if(h<w/2.6)h=w/2.6;
  w=Math.min(w,W);h=Math.min(h,H);
  return [Math.min(Math.max(cx-w/2,0),W-w),Math.min(Math.max(cy-h/2,0),H-h),w,h];}
function drawCrop(r){
  const svg=$('crop');svg.replaceChildren();const sh=sheetOf(r),boxes=boxesOf(r);
  const vb=(whole||!boxes.length)?[0,0,sh.w,sh.h]:cropBox(r,boxes,sh);
  svg.setAttribute('viewBox',vb.join(' '));
  const u=S('use');u.setAttribute('href','#sheet-'+sheetName(r));svg.append(u);
  const sw=Math.max(vb[2]/220,1.5),conn=isConn(r);
  const rects=boxes.map(b=>[b[0]*sh.w/1000,b[1]*sh.h/1000,(b[2]-b[0])*sh.w/1000,(b[3]-b[1])*sh.h/1000]);
  if(conn&&rects.length===2){const l=S('line');
    l.setAttribute('x1',rects[0][0]+rects[0][2]/2);l.setAttribute('y1',rects[0][1]+rects[0][3]/2);l.setAttribute('x2',rects[1][0]+rects[1][2]/2);l.setAttribute('y2',rects[1][1]+rects[1][3]/2);
    l.setAttribute('stroke','#d6336c');l.setAttribute('stroke-width',sw);l.setAttribute('stroke-dasharray',(sw*4)+' '+(sw*3));svg.append(l);}
  for(const q of rects){const e=S('rect');
    e.setAttribute('x',q[0]);e.setAttribute('y',q[1]);e.setAttribute('width',q[2]);e.setAttribute('height',q[3]);
    e.setAttribute('fill','none');e.setAttribute('stroke','#d6336c');e.setAttribute('stroke-width',sw);svg.append(e);}
  $('nobox').textContent=boxes.length?(conn?'The dashed line joins the two items this connection is said to link (a logical link, not a pipe route).':''):'No box was recorded for this item; the whole sheet is shown.';
  $('whole').textContent=whole?'Zoom to the item':'Show whole sheet';$('whole').hidden=!boxes.length;}
function drawFacts(r){
  const fa=$('facts');fa.replaceChildren();
  const add=(k,v)=>{if(v===''||v===undefined)return;fa.append(el('dt',k),el('dd',String(v)));};
  add('Item id',f(r,'item_id'));add('Type',f(r,'item_type'));add('Belongs to',f(r,'belongs_to'));
  add('Extraction confidence',f(r,'extraction_confidence'));add('Tag status',f(r,'tag_status'));
  add('Sheet',f(r,'sheet'));add('Source',f(r,'source'));add('Attached',f(r,'how_attached'));
  add('Risk tier',f(r,'tier'));add('Risk score',f(r,'risk_score'));add('Model status',f(r,'model_status'));}
function fixRow(field,val){
  const row=el('div',undefined,'fix');const sel=el('select');sel.setAttribute('aria-label','Field to correct');
  EDIT.forEach(x=>sel.append(new Option(x,x)));sel.value=field;
  const inp=el('input');inp.type='text';inp.setAttribute('aria-label','Corrected value');inp.value=val||'';inp.maxLength=500;
  const upd=()=>{collectFix();};sel.onchange=upd;inp.oninput=upd;
  inp.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();collectFix();if(!hasFix()){$('fixerr').textContent='Type the corrected value, or choose Confirm or Reject instead.';return;}go(1);}};
  row.append(sel,inp);return row;}
function hasFix(){const s=status(byId[cur]);return (s.v||[]).some(p=>p[0]&&p[1].trim());}
function collectFix(){
  const pairs=[...$('fixrows').children].map(r=>[r.children[0].value,r.children[1].value]);
  const bad=pairs.some(p=>p[1].includes(';'));$('fixerr').textContent=bad?'Remove the semicolon (;) from the value: it separates fields.':'';
  const s=dec[cur]||(dec[cur]={});s.v=pairs.map(p=>[p[0],p[1].replace(/;/g,',')]);save();drawList();drawProgress();}
function drawItem(){
  const r=byId[cur];$('empty').hidden=!!r;$('item').hidden=!r;if(!r)return;
  const s=status(r);drawCrop(r);drawFacts(r);
  $('title').textContent=f(r,'what_it_is')||f(r,'item_id');
  const b=$('badges');b.replaceChildren();if(isSafety(r))b.append(el('span','safety-relevant','badge s'));
  if(earlier(r))b.append(el('span','reviewed earlier: '+f(r,'model_status'),'badge'));
  const why=$('why');why.textContent=f(r,'why_check_this')+(f(r,'why')?' | '+f(r,'why'):'');why.className='why'+(isSafety(r)?' safe':'');
  document.querySelectorAll('.act button[data-d]').forEach(x=>x.setAttribute('aria-pressed',String(s.d===x.dataset.d)));
  $('fixes').hidden=s.d!=='correct';
  $('fixrows').replaceChildren();$('fixerr').textContent='';
  if(s.d==='correct'){const v=(s.v&&s.v.length)?s.v:[[isConn(r)?'from':'tag','']];v.forEach(p=>$('fixrows').append(fixRow(p[0],p[1])));
    if(pendingFocus){pendingFocus=false;$('fixrows').querySelector('input').focus();}}
  $('note').value=s.n||'';}
function drawList(){
  const list=$('list'),vis=visible();list.replaceChildren();
  $('count').textContent=vis.length+' of '+rows.length+' items';
  for(const r of vis){const id=f(r,'item_id'),s=status(r);
    const b=el('button',(isSafety(r)?'[safety] ':'')+id+'  '+(f(r,'what_it_is')||''),(s.d||'')+(id===cur?' cur':'')+(earlier(r)?' earlier':''));
    b.type='button';b.onclick=()=>select(id);list.append(b);}
  const c=list.querySelector('.cur');if(c&&c.scrollIntoView)c.scrollIntoView({block:'nearest'});}
function drawProgress(){
  const n=rows.length,d=rows.filter(decided).length,sf=rows.filter(r=>isSafety(r)&&!decided(r)).length;
  const inc=rows.filter(r=>status(r).d==='correct'&&!(status(r).v||[]).some(p=>p[0]&&p[1].trim())).length;
  $('progress').textContent=d+' of '+n+' decided, '+(n-d)+' to go'+(sf?', '+sf+' safety-relevant not yet decided':'')+(inc?' ('+inc+' Correct without a value)':'');
  $('fill').style.width=(n?100*d/n:0)+'%';}
function select(id){cur=id;whole=false;draw();}
function draw(){drawList();drawItem();drawProgress();}
function go(step){
  const vis=visible();if(!vis.length)return;
  let p=vis.findIndex(r=>f(r,'item_id')===cur);
  if(p<0)p=step>0?-1:vis.length;
  p=Math.min(Math.max(p+step,0),vis.length-1);select(f(vis[p],'item_id'));}
function decide(kind){
  const r=byId[cur];if(!r)return;const s=dec[cur]||(dec[cur]={});
  const vis0=visible(),pos=vis0.findIndex(x=>f(x,'item_id')===cur);
  if(s.d===kind&&kind==='correct')return;
  s.d=kind;if(kind!=='correct')s.v=s.v||[];save();
  if(kind==='correct'){pendingFocus=true;draw();return;}
  const vis=visible();let np=vis.findIndex(x=>f(x,'item_id')===cur);
  np=np>=0?np+1:pos;np=Math.min(Math.max(np,0),vis.length-1);
  if(vis.length)select(f(vis[np],'item_id'));else draw();}
function clearDecision(){const s=dec[cur];if(s){s.d='';s.v=[];save();}draw();}
document.querySelectorAll('.act button[data-d]').forEach(b=>b.onclick=()=>decide(b.dataset.d));
$('clear').onclick=clearDecision;$('prev').onclick=()=>go(-1);$('next').onclick=()=>go(1);
$('whole').onclick=()=>{whole=!whole;drawCrop(byId[cur]);};
$('addfix').onclick=()=>{$('fixrows').append(fixRow('tag',''));collectFix();};
$('note').oninput=()=>{const s=dec[cur]||(dec[cur]={});s.n=$('note').value;save();};
['f-show','f-type','f-tier'].forEach(i=>$(i).onchange=()=>{const v=visible();if(v.length&&!v.some(r=>f(r,'item_id')===cur))cur=f(v[0],'item_id');draw();});
$('f-text').oninput=()=>{const v=visible();if(v.length&&!v.some(r=>f(r,'item_id')===cur))cur=f(v[0],'item_id');draw();};
document.addEventListener('keydown',e=>{
  const t=e.target,typing=t&&/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName);
  if(e.key==='Escape'&&typing){t.blur();return;}
  if(typing||e.ctrlKey||e.metaKey||e.altKey)return;
  const k=e.key.toLowerCase();
  if(k==='1')decide('confirm');else if(k==='2')decide('correct');else if(k==='3')decide('reject');
  else if(k==='0')clearDecision();else if(k==='j')go(1);else if(k==='k')go(-1);else return;
  e.preventDefault();});
// The download: review_queue.csv with the OPS_ columns filled in the format scripts/apply_review.py reads.
function cell(v){v=String(v);return /[",\r\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function csvText(){
  const out=['﻿'+D.cols.map(cell).join(',')];
  for(const src of D.rows){
    const row=src.slice(),d=dec[src[C.item_id]]||{};
    let kind=d.d||'';const note=(d.n||'').trim();
    const pairs=(d.v||[]).filter(p=>p[0]&&p[1].trim()).map(p=>[p[0],p[1].trim()]);
    if(kind==='correct'&&!pairs.length)kind='';
    if(kind){row[C.OPS_confirm_or_correct]=kind;row[C.OPS_correct_value]=kind==='correct'?pairs.map(p=>p[0]+'='+p[1]).join('; '):'';}
    if(note)row[C.OPS_notes]=note;
    out.push(row.map(cell).join(','));}
  return out.join('\r\n')+'\r\n';}
window.__reviewCsv=csvText;
$('dl').onclick=()=>{
  const inc=rows.filter(r=>status(r).d==='correct'&&!(status(r).v||[]).some(p=>p[0]&&p[1].trim())).length;
  const n=rows.filter(decided).length-inc;
  const blob=new Blob([csvText()],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);
  const a=el('a');a.href=url;a.download='review_decisions.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('dlmsg').textContent='Downloaded review_decisions.csv with '+n+' decisions'+(inc?'; '+inc+' Correct item(s) had no value and were left blank':'')+'.';
  $('cmd').textContent='python scripts/apply_review.py '+D.bundle+'/plant_model.json review_decisions.csv --reviewer "Your name, role" --dry-run\npython scripts/apply_review.py '+D.bundle+'/plant_model.json review_decisions.csv --reviewer "Your name, role"';
  $('after').hidden=false;};
setupFilters();draw();
</script></body></html>'''


if __name__ == "__main__":
    sys.exit(main())
