"""Retained source-revision and planted raw-loss controls on the exposed transfer cohort."""
import copy
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent));sys.path.insert(0,str(HERE.parents[3]/'scripts'))
import cad_handoff as ch
import cad_value_patch as patch
import prepare_layout10 as raw_records
from verify_bytes import verify


def write(path,value):ch.write_json(path,value)


def raw_value(raw,record,code,value):
    tags=[t for t in record['tags'] if t[0]==code]
    if len(tags)!=1:raise ValueError('Control requires one explicit raw tag')
    t=tags[0];return raw[:t[2]]+value+raw[t[3]:]


def foreign_revision(raw,path):
    records=raw_records.records(raw);doc=ch.load(path);asset=ch.assets(doc)[0]
    ref=doc.entitydb[asset['handle']];attr=ref.get_attrib('ICT_ID')
    record=next(r for r in records if raw_records.own_handle(r)==attr.dxf.handle.upper())
    clone=raw[record['start']:record['end']]
    handle=format(max(int(k,16) for k in doc.entitydb.keys())+1,'X').encode()
    changes={5:handle,2:b'QUAL_FOREIGN_CONTROL',1:b'KEEP-FOREIGN-1'}
    spans=[]
    for code,value in changes.items():
        tags=[t for t in record['tags'] if t[0]==code]
        if len(tags)!=1:raise ValueError('Ambiguous foreign-control source tag')
        t=tags[0];spans.append((t[2]-record['start'],t[3]-record['start'],value))
    for start,end,value in sorted(spans,reverse=True):clone=clone[:start]+value+clone[end:]
    seqend=next(r for r in records if raw_records.own_handle(r)==ref.seqend.dxf.handle.upper())
    raw=raw[:seqend['start']]+clone+raw[seqend['start']:]
    # Use an existing registered application and a record without prior XDATA.
    records=raw_records.records(raw)
    geometry=next(r for r in records if r['kind'] in (b'LINE',b'CIRCLE',b'ARC') and not any(t[0]>=1000 for t in r['tags']))
    newline=geometry['newline'];addition=b'1001'+newline+b'ACAD'+newline+b'1000'+newline+b'KEEP-XDATA-1'+newline
    return raw[:geometry['end']]+addition+raw[geometry['end']:]


def execute(root,out):
    out.mkdir(parents=True,exist_ok=False);rows=[]
    admission=json.loads((root/'inputs/ADMISSION.json').read_bytes())
    for item in admission['cases']:
        identity=item['id'];folder=out/identity;folder.mkdir();source=root/'native-1/cases'/identity/'source.dxf'
        plan=json.loads((source.parent/'plan.json').read_bytes());before=ch.snapshot(source)
        candidate=source.parent/'candidate.dxf';raw=candidate.read_bytes()
        geometry=next(r for r in raw_records.records(raw) if r['kind'] in (b'LINE',b'CIRCLE',b'ARC') and sum(t[0]==10 for t in r['tags'])==1)
        value=next(t[1] for t in geometry['tags'] if t[0]==10)
        changed=folder/'unplanned-geometry.dxf';changed.write_bytes(raw_value(raw,geometry,10,str(float(value)+.125).encode()))
        if not ch.compare(before,ch.snapshot(changed),plan)['unexpected']:raise ValueError('Missed unplanned geometry')
        try:verify(source,changed,plan)
        except ValueError:pass
        else:raise ValueError('Raw checker missed geometry')
        # A new explicit fictional source revision supplies unfamiliar payloads absent from this adaptation.
        revision=folder/'revision-2.dxf';revision.write_bytes(foreign_revision(raw,candidate))
        attrs=ch.assets(ch.load(revision))[0]['attributes']
        if attrs.get('QUAL_FOREIGN_CONTROL')!='KEEP-FOREIGN-1':raise ValueError('Foreign revision not admitted')
        for label,oldplan in [('stale-source',copy.deepcopy(plan)),('stale-before',copy.deepcopy(plan))]:
            if label=='stale-before':oldplan['source_sha256']=ch.digest(revision)
            try:patch.apply(revision,oldplan,folder/label)
            except ch.InputError as error:
                if (folder/label).exists():raise ValueError('Refusal published output')
                write(folder/(label+'.json'),dict(refused=True,error=str(error)))
            else:raise ValueError('Stale revision accepted')
        newplan=copy.deepcopy(plan);newplan['source_sha256']=ch.digest(revision)
        for change in newplan['changes']:change.update(before='QUAL-AFTER',after='QUAL-REV2',reason='Explicit fictional second revision; preserve added unfamiliar payloads')
        write(folder/'revision-2-plan.json',newplan);patch.apply(revision,newplan,folder/'revision-2-candidate')
        target=folder/'revision-2-candidate/candidate.dxf';verify(revision,target,newplan)
        if ch.compare(ch.snapshot(revision),ch.snapshot(target),newplan)['unexpected']:raise ValueError('Revision candidate failed strict preservation')
        targetraw=target.read_bytes()
        for name,old,new in [('foreign',b'KEEP-FOREIGN-1',b'LOST-FOREIGN-1'),('xdata',b'KEEP-XDATA-1',b'LOST-XDATA-1')]:
            if targetraw.count(old)!=1:raise ValueError('Ambiguous control payload')
            bad=folder/('changed-'+name+'.dxf');bad.write_bytes(targetraw.replace(old,new))
            if not ch.compare(ch.snapshot(revision),ch.snapshot(bad),newplan)['unexpected']:raise ValueError('Missed '+name+' change')
            try:verify(revision,bad,newplan)
            except ValueError:pass
            else:raise ValueError('Raw checker missed '+name)
        rows.append(dict(id=identity,unplanned_geometry_detected=True,stale_source_refused=True,stale_before_refused=True,
                         second_revision_strict_and_raw=True,foreign_change_detected=True,xdata_change_detected=True,
                         original_candidate_unchanged=candidate.read_bytes()==raw))
        write(out/'RESULTS.json',dict(cases=rows,scope='Added fictional foreign/XDATA revision controls on already exposed source structures; not fresh upstream foreign-payload evidence',whole_cad_qualified=False))
    return rows


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    print(json.dumps(execute(args.root,args.out),indent=2))
