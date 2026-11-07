"""Exchange equipment-data proposals through a local form or agent without resaving CAD geometry.

Source-bound sidecar only: explicit ICT_ID/TAG DXF profile and the existing five editable attributes.
Returned JSON is untrusted proposal data. No full CAD return, geometry merge or engineering approval.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import cad_handoff as ch
import cad_value_patch as vp


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ch.InputError("Duplicate JSON field: " + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def read_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8-sig"))


def catalog(source):
    vp.source_tags(Path(source).read_bytes())
    snap = ch.snapshot(source)
    return {"schema": "cad-data-exchange-1", "source_sha256": snap["sha256"],
            "mode": "existing equipment attributes only; drawing geometry is not an input channel",
            "editable": sorted(ch.EDITABLE),
            "assets": [{"id": a["id"], "attributes": a["attributes"]} for a in snap["assets"]]}


def response_for(exchange, changes):
    """Agent-facing response constructor; apply still validates every field against the current source."""
    return {"schema": "cad-data-response-1", "source_sha256": exchange["source_sha256"],
            "exchange_sha256": fingerprint(exchange), "changes": changes}


def plan_from(source, exchange, response):
    current = catalog(source)
    if canonical(exchange) != canonical(current):
        raise ch.InputError("Catalog is stale or changed; prepare from the current source again")
    if (not isinstance(response, dict) or set(response) != {"schema", "source_sha256", "exchange_sha256", "changes"}
            or response["schema"] != "cad-data-response-1"
            or response["source_sha256"] != current["source_sha256"]
            or response["exchange_sha256"] != fingerprint(current)):
        raise ch.InputError("Response must bind the exact current source and complete catalog")
    changes = response["changes"]
    keys = {"id", "attribute", "before", "after", "reason"}
    if (not isinstance(changes, list) or not changes
            or any(not isinstance(c, dict) or set(c) != keys
                   or any(not isinstance(v, str) for v in c.values()) for c in changes)):
        raise ch.InputError("Response requires explicit changes with only id/attribute/before/after/reason text fields")
    plan = {"schema": "cad-edit-plan-1", "source_sha256": current["source_sha256"], "changes": changes}
    ch.validate_plan(ch.snapshot(source), plan)
    return plan


def render(exchange):
    # JSON is embedded as inert data, never HTML. Source strings go into DOM textContent/value only.
    payload = json.dumps(exchange, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return HTML.replace("@FINGERPRINT@", fingerprint(exchange)).replace("@CATALOG@", payload)


def prepare(source, out):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ch.InputError("Destination exists; retain the earlier exchange")
    data = catalog(source)
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != data["source_sha256"]:
        raise ch.InputError("Source changed during preparation")
    with tempfile.TemporaryDirectory(prefix="ict-cad-exchange-") as tmp:
        stage = Path(tmp) / "packet"
        stage.mkdir()
        (stage / "source.dxf").write_bytes(raw)
        ch.write_json(stage / "exchange.json", data)
        (stage / "review.html").write_text(render(data), encoding="utf-8", newline="\n")
        if ch.digest(source) != data["source_sha256"]:
            raise ch.InputError("Source changed during preparation")
        shutil.copytree(stage, out)
    return data


def apply(source, exchange, response, out, response_raw=None):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ch.InputError("Destination exists; retain the earlier draft")
    plan = plan_from(source, exchange, response)
    if response_raw is None:
        response_raw = (json.dumps(response, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if canonical(parse_json(response_raw.decode("utf-8-sig"))) != canonical(response):
        raise ch.InputError("Original response bytes disagree with the supplied proposal")
    with tempfile.TemporaryDirectory(prefix="ict-cad-exchange-apply-") as tmp:
        stage = Path(tmp) / "draft"
        report = vp.apply(source, plan, stage)
        ch.write_json(stage / "exchange.json", exchange)
        ch.write_json(stage / "response.json", response)
        (stage / "response-original.json").write_bytes(response_raw)
        ch.write_json(stage / "exchange-receipt.json", {
            "schema": "cad-data-exchange-receipt-1", "source_sha256": plan["source_sha256"],
            "exchange_sha256": fingerprint(exchange), "response_sha256": fingerprint(response),
            "response_original_sha256": hashlib.sha256(response_raw).hexdigest(),
            "candidate_sha256": ch.digest(stage / "candidate.dxf"), "strict_status": report["status"],
            "status": "draft equipment-data proposal; not approval",
            "boundary": "Only declared value spans; source CAD bytes otherwise retained. No full CAD return imported.",
            "native_ui_and_visual_acceptance": "not established or required for this metadata operation"})
        if ch.digest(source) != plan["source_sha256"]:
            raise ch.InputError("Source changed before publishing; prepare again")
        shutil.copytree(stage, out)
    return report


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>Review drawing equipment data</title><style>
:root{font:16px/1.5 system-ui;color:#182d38;background:#f3f6f7}body{max-width:950px;margin:auto;padding:24px}
h1{font-size:1.8rem;line-height:1.2}h2{font-size:1.2rem;overflow-wrap:anywhere}section{background:white;border:1px solid #c4d2d9;border-radius:10px;padding:20px;margin:20px 0}
label{display:block;font-weight:650;margin-top:14px}input,textarea{box-sizing:border-box;width:100%;font:inherit;padding:9px;border:1px solid #8297a4;border-radius:4px}input[readonly]{background:#edf1f3;color:#415564}
.row{border-top:1px solid #dde4e8;margin-top:18px;padding-top:4px}.hint{font-size:.9rem;color:#465e6a;overflow-wrap:anywhere}button{background:#17546e;color:white;border:0;border-radius:5px;padding:12px 20px;font:inherit;cursor:pointer}#status{white-space:pre-wrap;overflow-wrap:anywhere;font-weight:600}
code{overflow-wrap:anywhere}a{color:#164b6b}textarea{min-height:110px}#response{min-height:230px}footer{margin:24px 0}@media(max-width:500px){body{padding:14px}section{padding:14px}h1{font-size:1.5rem}}
</style></head><body><h1>Review drawing equipment data</h1>
<p>Propose changes to equipment records while keeping the drawing intact. This form works locally and sends nothing to a server.</p>
<p><a href="source.dxf" download>Retained source DXF</a> · <a href="exchange.json" download>Agent data catalog</a></p>
<p class="hint">Geometry, layouts, identities and unfamiliar fields stay in the source. This form does not display or approve the drawing. All changes remain drafts for engineering review.</p>
<p class="hint" id="binding"></p><noscript>This local form needs JavaScript. An agent can use exchange.json instead.</noscript>
<form id="review"><div id="assets"></div><button type="submit">Download proposed changes</button></form>
<p id="status" role="status" aria-live="polite"></p><label for="response">Returned JSON (also available to copy)</label><textarea id="response" readonly></textarea>
<footer class="hint">Run cad_exchange.py apply with the current source, catalog and downloaded response. A changed source requires a fresh catalog. A reason is supplied evidence, not authenticated approval.</footer>
<script id="catalog" type="application/json">@CATALOG@</script>
<script>
'use strict';
const exchange=JSON.parse(document.getElementById('catalog').textContent), fields=[];
document.getElementById('binding').textContent='Source SHA-256: '+exchange.source_sha256;
const host=document.getElementById('assets');let n=0;
for(const asset of exchange.assets){
 const section=document.createElement('section'),heading=document.createElement('h2');
 heading.textContent=asset.id;section.append(heading);
 for(const [attribute,before] of Object.entries(asset.attributes).sort((a,b)=>a[0].localeCompare(b[0]))){
  const row=document.createElement('div');row.className='row';
  const label=document.createElement('label'),input=document.createElement('input'),key='field-'+n++;
  label.htmlFor=key;label.textContent=attribute;input.id=key;input.value=before;
  const editable=exchange.editable.includes(attribute);input.readOnly=!editable;
  row.append(label,input);
  if(editable){
   const hint=document.createElement('p');hint.className='hint';hint.textContent='Source value: '+before;row.append(hint);
   const reasonLabel=document.createElement('label'),reason=document.createElement('textarea');
   reason.id=key+'-reason';reasonLabel.htmlFor=reason.id;reasonLabel.textContent=attribute+' evidence / reason (required when changed)';
   row.append(reasonLabel,reason);fields.push({asset:asset.id,attribute,before,input,reason});
  } else {const hint=document.createElement('p');hint.className='hint';hint.textContent='Retained, read-only source field';row.append(hint);}
  section.append(row);
 }
 host.append(section);
}
document.getElementById('review').addEventListener('submit',event=>{
 event.preventDefault();const changes=[],errors=[];
 for(const f of fields){if(f.input.value===f.before)continue;
  if(!f.input.value.trim()||!f.reason.value.trim())errors.push(f.asset+' / '+f.attribute+': enter a value and evidence / reason.');
  else if(/[\x00-\x1f\x7f\x85\u2028\u2029]|\\[PX]/.test(f.input.value))errors.push(f.asset+' / '+f.attribute+': use plain single-line text.');
  else changes.push({id:f.asset,attribute:f.attribute,before:f.before,after:f.input.value,reason:f.reason.value.trim()});
 }
 const status=document.getElementById('status'),output=document.getElementById('response');output.value='';
 if(errors.length||!changes.length){status.textContent=errors.join('\n')||'No changed values. Edit a value and supply its evidence / reason.';return;}
 const response={schema:'cad-data-response-1',source_sha256:exchange.source_sha256,exchange_sha256:'@FINGERPRINT@',changes};
 output.value=JSON.stringify(response,null,2)+'\n';
 const url=URL.createObjectURL(new Blob([output.value],{type:'application/json'})),link=document.createElement('a');
 link.href=url;link.download='cad-response.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 status.textContent=changes.length+' proposed change(s) downloaded. The source drawing has not been edited. Apply validates encoding and the current source again.';
});
</script></body></html>
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p = sub.add_parser("apply")
    p.add_argument("source")
    p.add_argument("exchange")
    p.add_argument("response")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            data = prepare(args.source, args.out)
            print(len(data["assets"]), "asset(s); open review.html locally or use exchange.json with your agent")
        else:
            report = apply(args.source, read_json(args.exchange), read_json(args.response), args.out,
                           response_raw=Path(args.response).read_bytes())
            print(len(report["expected_edits"]), "draft edits; zero unexpected strict differences; source retained")
        return 0
    except (ch.InputError, OSError, ValueError, ch.ezdxf.DXFError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
