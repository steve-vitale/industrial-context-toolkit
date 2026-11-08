"""Diagnose exposed native paper round trips from exact records; no CAD launch or waived differences."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from native_revisions import HERE, ROOT, read, write, sha, lf, require
from evidence import unpack
from receive import equal
import cad_handoff as ch
from cad_value_patch import source_tags


def raw_records(raw):
    result={};group=[]
    def retain(tags):
        if not tags or tags[0][1] not in (b'LAYOUT',b'VIEWPORT'):return
        handles=[v.strip().decode('ascii').upper() for code,v,*_ in tags if code==5]
        require(len(handles)==1 and handles[0] not in result,'Ambiguous raw paper record')
        result[handles[0]]=[dict(code=code,value_hex=v.hex()) for code,v,*_ in tags]
    for tag in source_tags(raw):
        if tag[0]==0:retain(group);group=[]
        group.append(tag)
    retain(group);return result


def inventory(path):
    raw=path.read_bytes();records=raw_records(raw);doc=ch.load(path);layouts=[];covered=set()
    for layout in doc.layouts:
        settings=layout.dxf_layout.dxf.all_existing_dxf_attribs();handle=settings['handle'].upper();tags=records[handle];covered.add(handle)
        owners=[bytes.fromhex(t['value_hex']).decode('ascii').strip().upper() for t in tags if t['code']==330]
        require(settings['block_record_handle'].upper() in owners,'Raw layout block ownership differs')
        views=[]
        for entity in layout:
            if entity.dxftype()!='VIEWPORT':continue
            attrs=entity.dxf.all_existing_dxf_attribs();h=attrs['handle'].upper();vtags=records[h];covered.add(h)
            ids=[int(bytes.fromhex(t['value_hex'])) for t in vtags if t['code']==69]
            owners=[bytes.fromhex(t['value_hex']).decode('ascii').strip().upper() for t in vtags if t['code']==330]
            require(ids==[attrs['id']] and attrs['owner'].upper()==settings['block_record_handle'].upper() and attrs['owner'].upper() in owners,'Raw viewport ID/layout ownership differs')
            views.append(dict(attributes=attrs,raw_tags=vtags))
        layouts.append(dict(name=layout.name,settings=settings,raw_layout_tags=tags,viewports=views))
    require(covered==set(records),'An orphan/uninventoried raw layout or viewport remains')
    # Vector types are retained as their full component lists; no numeric rounding.
    return json.loads(json.dumps(dict(sha256=sha(path),dxfversion=doc.dxfversion,layouts=layouts),default=lambda v:list(v)))


def run(out):
    require(not out.exists(),'New native-paper record audit folder required')
    frozen=read(HERE/'PAPER-RECORD-FREEZE-1.json')
    for name,pin in frozen['files_sha256_lf'].items():require(lf(ROOT/name)==pin,'Frozen paper diagnosis input/method differs: '+name)
    first=read(HERE/'NATIVE-REVISION-FREEZE-1.json')['inputs'];second=read(HERE/'SECOND-REVISION-INPUTS.json')['cases']
    retained=read(HERE/'NATIVE-CONCURRENT-RETAINED-1.json')['attempts'];rows=[]
    with tempfile.TemporaryDirectory(prefix='ict-paper-records-') as temporary:
        root=Path(temporary)
        for row in first:
            case=row['case'];short=case.removeprefix('validation-');later=next(r for r in second if r['case']==case)
            baseline=ROOT/row['baseline_inventory'];require(lf(baseline)==row['baseline_inventory_sha256_lf'],'Original matched baseline inventory differs')
            noedit=unpack(baseline.parent)['attempt/job/returned.dxf']
            packet=ROOT/later['native_packet'];pins=retained[short+'-concurrent-edited-1']
            require(lf(packet/'INVENTORY.json')==pins['inventory_sha256_lf'] and sha(packet/'evidence.tar.xz')==pins['archive_sha256'],'Actual concurrent packet differs')
            concurrent=unpack(packet)['attempt/job/returned.dxf']
            require(hashlib.sha256(concurrent).hexdigest()==later['source_sha256'],'Actual native return/source differs')
            paths={}
            for role,raw in [('noedit_native',noedit),('concurrent_native',concurrent)]:
                p=root/(case+'-'+role+'.dxf');p.write_bytes(raw);paths[role]=p
            for role,key,pin_key,source in [('original','source','source_sha256',row),('original_value_candidate','candidate','candidate_sha256',row),('selected_second_candidate','candidate','candidate_sha256',later)]:
                p=ROOT/source[key];require(sha(p)==source[pin_key],'Declared '+role+' changed');paths[role]=p
            snapshots={role:inventory(path) for role,path in paths.items()};source={l['name']:l for l in snapshots['original']['layouts']};findings=[]
            for role in ('noedit_native','concurrent_native'):
                returned={l['name']:l for l in snapshots[role]['layouts']}
                for name,before in source.items():
                    if name=='Model':continue
                    after=returned.get(name)
                    original_display=[v for v in before['viewports'] if v['attributes']['id']>1]
                    current_display=[v for v in after['viewports'] if v['attributes']['id']>1] if after else []
                    settings={key:dict(before=before['settings'].get(key),after=after['settings'].get(key) if after else None) for key in ('paper_size','paper_width','paper_height','plot_rotation','plot_paper_units') if not after or before['settings'].get(key)!=after['settings'].get(key)}
                    findings.append(dict(role=role,layout=name,missing_layout=after is None,settings_changes=settings,
                        source_display_viewports=original_display,returned_display_viewports=current_display,
                        display_viewport_missing=bool(original_display) and not current_display))
            rows.append(dict(case=case,documents=snapshots,findings=findings,
                noedit_and_concurrent_paper_records_identical=equal(snapshots['noedit_native']['layouts'],snapshots['concurrent_native']['layouts']),
                original_value_candidate_retains_paper=equal(snapshots['original']['layouts'],snapshots['original_value_candidate']['layouts']),
                second_candidate_retains_native_source_paper=equal(snapshots['concurrent_native']['layouts'],snapshots['selected_second_candidate']['layouts'])))
    result=dict(scope='Post-observation diagnosis on exposed cases; raw IDs/owners cross-check decoded inventories; no model or native invocation',cases=rows,
        conclusion='The no-edit and concurrent native paths both change paper settings and omit the original display viewport. Attribute candidates retain their own source paper records, including pre-existing losses. Native round-trip paper preservation fails; exact import/save cause and rendered paper acceptance are not established.',whole_cad_qualified=False)
    out.mkdir(parents=True);write(out/'RESULT.json',result)
    lines=['# Native paper records do not preserve the original sheets','',result['scope']+'.','',
        '| Case / route | Layout | Paper / rotation changes | Display viewport |','|---|---|---|---|']
    for row in rows:
        for finding in row['findings']:
            changes='; '.join(k+': '+str(v['before'])+' → '+str(v['after']) for k,v in finding['settings_changes'].items())
            lines.append('| '+row['case']+' / '+finding['role']+' | '+finding['layout']+' | '+changes+' | '+('Original display viewport missing' if finding['display_viewport_missing'] else 'No source display viewport to preserve')+' |')
    lines+=['','The complete [record audit](RESULT.json) retains all layouts, raw LAYOUT/VIEWPORT tags, owners and exact source hashes. Layout1 originally has no display viewport; it is not counted as a removed display viewport. Qualification sheet originally has ID3; native returns contain only a generated ID1.',
        '',result['conclusion'],'','This does not explain or waive every strict difference. It does not locate the precise installed importer/writer function. Source originals and all comparator rules remain unchanged.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('out',type=Path);args=parser.parse_args();r=run(args.out)
    print(json.dumps(dict(cases=len(r['cases']),missing_display_observations=sum(f['display_viewport_missing'] for c in r['cases'] for f in c['findings']),noedit_concurrent_equal=[c['noedit_and_concurrent_paper_records_identical'] for c in r['cases']],source_value_preserved=[c['original_value_candidate_retains_paper'] for c in r['cases']],whole_cad_qualified=False)))
