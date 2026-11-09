"""Offline read-only HTML presentation for map_explorer; all supplied content becomes text nodes."""
import json


def render(payload):
    data = json.dumps(payload, ensure_ascii=True, sort_keys=True, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return PAGE.replace('__MAP_DATA__', data)


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Engineering context map</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#172d3b;background:#f2f5f5}*{box-sizing:border-box}
body{margin:0}header{background:#193c46;color:white;padding:1.3rem max(1rem,4vw)}h1{margin:0;font-size:1.8rem}
header p{max-width:65rem;margin:.5rem 0}main{max-width:1400px;margin:auto;padding:1rem;display:grid;grid-template-columns:19rem minmax(0,1fr);gap:1rem}
aside,section{background:white;padding:1rem;border-radius:8px;min-width:0}aside{align-self:start}section{margin-bottom:1rem}
h2{font-size:1.2rem;margin:.2rem 0 .7rem}h3{font-size:1rem;margin:1rem 0 .3rem}p{margin:.4rem 0}label{display:block;margin:.5rem 0}
input,select,button{font:inherit;max-width:100%}input,select{width:100%;padding:.45rem;border:1px solid #8a9a9f;border-radius:4px}
button{color:#164f66;background:#eef5f6;border:1px solid #c6d7da;border-radius:4px;padding:.35rem .6rem;cursor:pointer;white-space:normal;text-align:left;overflow-wrap:anywhere}
button:hover,button:focus{background:#d9edef;outline:2px solid #407f90}button.active{border-left:5px solid #176979}
#items{display:grid;gap:.4rem;max-height:60vh;overflow:auto;margin-top:.7rem}small,.muted{color:#546c77}code,pre{font-family:ui-monospace,monospace;font-size:.85rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f6;padding:.7rem;border-radius:4px}summary{cursor:pointer;color:#245e72;overflow-wrap:anywhere}
.row{padding:.75rem 0;border-top:1px solid #dce5e7;overflow-wrap:anywhere}.row:first-child{border-top:0}.warn{border-left:4px solid #ac701c;padding:.7rem;background:#fff8eb}
.badge{display:inline-block;font-size:.8rem;border:1px solid #a4b5bb;padding:.05rem .4rem;border-radius:4px;margin:.1rem .3rem .1rem 0}
.wrap{overflow-wrap:anywhere}.links{display:flex;gap:.5rem;flex-wrap:wrap}a{color:#176077;overflow-wrap:anywhere}footer{max-width:1400px;margin:auto;padding:1rem}
@media(max-width:760px){main{display:block}aside{margin-bottom:1rem}#items{max-height:12rem}h1{font-size:1.4rem}}
</style></head><body><header><h1>Engineering context map</h1><p>Find an item. Follow its recorded relationships. Inspect the evidence and disagreements. Compare supplied revisions.</p><p>Read-only local snapshot · Draft interpretations need engineering review · No ongoing synchronization</p></header>
<main><aside><label for="snapshot">Snapshot</label><select id="snapshot"></select><label for="search">Find by name, tag, alias or qualified identity</label><input id="search" type="search" placeholder="e.g. P-101"><p id="count" class="muted" aria-live="polite"></p><div id="items"></div></aside>
<article><section id="intro"><h2>Start with an engineering question</h2><p>Select an item to inspect its facts, source versions, documents and relationships. A shared tag may identify several different items; choose the full scope.</p><p class="warn">A recorded connection or document mention does not establish an isolation boundary, safe action, installed state or operating consequence.</p><div class="links"><a href="current.json" download>Complete current map</a><a href="exploration.json" download>All inspection records</a><a href="evidence.json" download>Evidence inventory</a></div></section><div id="detail" aria-live="polite"></div><section id="comparison"></section><section id="limits"><h2>What this establishes</h2></section></article></main>
<footer>Keep authoritative drawings and records in their assigned company systems. Rebuild from a new approved export to examine its changes. This package contains the entire supplied map and any retained originals.</footer>
<script id="data" type="application/json">__MAP_DATA__</script><script>
'use strict';
const data=JSON.parse(document.getElementById('data').textContent), model=data.exploration;
const snapshots=Object.keys(model.views), select=document.getElementById('snapshot'), search=document.getElementById('search');
let snapshot='current', selected=model.selected;
function el(tag,text,parent,cls){const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;if(parent)parent.append(x);return x}
function raw(parent,title,value){const d=el('details',undefined,parent);el('summary',title,d);el('pre',JSON.stringify(value,null,2),d);return d}
function nav(parent,id){const v=model.views[snapshot][id];if(!v)return el('span',id+' (not in this snapshot)',parent);const b=el('button',(v.node.tag||v.node.name||v.node.kind)+' · '+id,parent);b.onclick=()=>{selected=id;draw();};return b}
function sourceLine(parent,src){if(!src||typeof src!=='object')return;el('p','Source: '+(src.document||'not supplied')+' · revision '+(src.revision||'not supplied')+' · '+(src.locator||src.zone||src.sheet||'locator not supplied'),parent,'muted')}
function sources(parent,value){sourceLine(parent,value.source);raw(parent,'Complete source / review record',value)}
function evidence(parent,parts){
 const paths=new Set();function walk(v){if(!v||typeof v!=='object')return;if(typeof v.path==='string')paths.add(v.path);Object.values(v).forEach(walk)}walk(parts);
 const refs=data.evidence.filter(x=>x.snapshot===snapshot&&paths.has(x.source.path));
 if(!refs.length){el('p','No file path is supplied by these records.',parent,'muted');return}
 const groups=new Map();for(const r of refs){const k=JSON.stringify([r.source.path,r.source.sha256,r.status]);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r)}
 const panel=el('details',undefined,parent);const kept=[...groups.values()].filter(rs=>rs[0].status==='retained').length;el('summary','Evidence file bindings: '+kept+' retained, '+(groups.size-kept)+' unavailable',panel);
 for(const rs of groups.values()){const r=rs[0],box=el('div',undefined,panel,'row');el('strong',r.source.path,box);el('p',r.status.replaceAll('_',' '),box,r.status==='retained'?'':'warn');
 if(r.status==='unbound')el('p','This reference supplies no usable file hash. Another reference to the same path does not verify this binding.',box,'muted');
 if(r.retained){const a=el('a','Download exact retained original',box);a.href=r.retained;a.download=r.source.path.split('/').pop()}
 raw(box,'Bindings, revisions and graph locators',rs);}
}
function drawList(){const list=document.getElementById('items');list.replaceChildren();const q=search.value.toLowerCase();const vs=Object.values(model.views[snapshot]).filter(v=>[v.node.id,v.node.tag,v.node.name,...(v.node.aliases||[])].join(' ').toLowerCase().includes(q));document.getElementById('count').textContent=vs.length+' matching items';for(const v of vs){const b=nav(list,v.node.id);if(v.node.id===selected)b.classList.add('active')}}
function draw(){drawList();const root=document.getElementById('detail');root.replaceChildren();const v=model.views[snapshot][selected];if(!v){if(selected)el('p',selected+' is absent in this snapshot. Its removal is not proof of physical removal.',root,'warn');return}
 const n=v.node,card=el('section',undefined,root);el('h2',n.tag||n.name||n.id,card);el('p',n.id,card,'wrap');el('p',n.name||'',card);el('span',n.kind,card,'badge');el('span','Map review: '+(n.status||'unspecified'),card,'badge');if(n.document)el('span','Document: '+n.document.status+' · revision '+n.document.revision,card,'badge');if(n.owner)el('p','Record owner: '+n.owner,card);
 const attrs=el('section',undefined,root);el('h2','Facts and evidence',attrs);if(!(n.attributes||[]).length)el('p','No attribute claims recorded on this node.',attrs,'muted');for(const a of n.attributes||[]){const r=el('div',undefined,attrs,'row');el('strong',a.name+' = '+JSON.stringify(a.value),r);el('p','Review: '+a.status,r);sources(r,a)}sources(attrs,n);evidence(attrs,n);
 const links=el('section',undefined,root);el('h2','Recorded relationships',links);el('p','Arrows preserve the stored from/to order. Relation type, direction, layer, uncertainty and evidence remain in each full record.',links,'muted');for(const e of v.edges){const r=el('div',undefined,links,'row');nav(r,e.from);el('span',' → '+e.type+' → ',r);nav(r,e.to);el('p','Review: '+(e.status||'unspecified')+' · Direction: '+(e.direction||'unspecified'),r);raw(r,'Complete relationship and source',e)}if(!v.edges.length)el('p','No incident relationships recorded.',links);
 const docs=el('section',undefined,root);el('h2','Related documents',docs);el('p','Declared coverage and text mentions give context; they do not establish applicability to installed equipment.',docs,'muted');for(const d of v.documents){const r=el('div',undefined,docs,'row');nav(r,d.id);el('p',d.document.status+' · revision '+d.document.revision+' · '+d.document.owner,r);for(const f of (v.answers.documents||{facts:[]}).facts.filter(f=>f.other===d.id))el('p',f.says,r);raw(r,'Complete document record',d);evidence(r,d)}if(!v.documents.length)el('p','No covering or mentioning documents returned by the supported item questions.',docs);
 const conflicts=el('section',undefined,root);el('h2','Disagreements and retained rulings',conflicts);for(const c of v.conflicts){const r=el('div',undefined,conflicts,'row');el('strong',c.what,r);el('p',c.status+' · record owner: '+c.record_owner,r);raw(r,'Both sides, qualifications and full history',c);evidence(r,c)}if(!v.conflicts.length)el('p','No conflict with this exact subject is recorded. This is not a completeness or correctness guarantee.',conflicts,'muted');
 const questions=el('section',undefined,root);el('h2','Ask the existing map tools',questions);el('p','Expected-complete checks only configured record rules, not job readiness or equipment condition.',questions,'muted');for(const a of Object.values(v.answers)){const r=el('details',undefined,questions,'row');el('summary',a.question,r);el('p',a.reason||a.note||a.answer,r);for(const f of a.facts){el('p',f.says,r);sourceLine(r,f.source);if(f.other)nav(r,f.other);raw(r,'Complete answer fact',f)}raw(r,'Exact structured answer',a)}if(!Object.keys(v.answers).length)el('p','These item questions do not apply to this kind of node.',questions);raw(questions,'Related register rows',v.records);
 const compare=el('section',undefined,root);el('h2','This item across snapshots',compare);const d=model.node_changes.find(x=>x.id===selected);if(!model.changes)el('p','No previous snapshot supplied.',compare);else if(d){el('p','The stored node differs. A source hash/review change can change this record without proving a physical change.',compare,'warn');raw(compare,'Complete before / after node',d)}else el('p','Node record unchanged. Relationships or referenced documents can still differ; inspect the full comparison below.',compare);
}
for(const key of snapshots){const o=el('option',key,select);o.value=key}select.onchange=()=>{snapshot=select.value;draw()};search.oninput=drawList;
const comparison=document.getElementById('comparison');el('h2','Snapshot comparison',comparison);if(model.changes){el('p','The existing map_changes comparison reports supplied record differences; it does not update answers or certify implementation.',comparison);raw(comparison,'Complete structured comparison',model.changes);const a=el('a','Readable change report',comparison);a.href='changes.md';}else el('p','Supply a previous map of the same site to compare revisions.',comparison);
for(const limit of model.limits)el('p',limit,document.getElementById('limits'));draw();
</script></body></html>'''
