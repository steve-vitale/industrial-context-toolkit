"""Re-score retained public transfer files and exact native observations; no CAD/model calls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
QUAL=HERE.parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(QUAL));sys.path.insert(0,str(QUAL.parents[2]/'scripts'))
import cad_handoff as ch
import cad_value_patch as patch
from verify_bytes import verify
import transfer


def read(path):return json.loads(path.read_bytes())
def require(condition,message):
    if not condition:raise ValueError(message)


def native_rows(path,prefix,ids):
    lines=path.read_text(encoding='utf-8').splitlines()
    require(not any('FATAL' in s for s in lines),'Native fatal error')
    rows=[json.loads(s[len(prefix):]) for s in lines if s.startswith(prefix)]
    require([r['id'] for r in rows]==ids,'Native case coverage/order differs')
    require(not any(any(k.endswith('error') for k in r) for r in rows),'Native reported case error')
    profile=[json.loads(s.split(' ',1)[1]) for s in lines if s.startswith('ICT_TRANSFER11_PROFILE ')]
    require(len(profile)==1 and profile[0]['configuration_file']=='/home/cad/.config/QCAD/QCAD3.conf','Native selected profile differs')
    return rows


def fields(rows):
    out={}
    for row in rows:
        attrs=row['attributes'];identity=attrs.get('ICT_ID')
        require(identity and identity not in out,'Missing/duplicate native identity')
        out[identity]=attrs
    return out


def expected(path):return {a['id']:a['attributes'] for a in ch.snapshot(path)['assets']}


def native_fields(rows,values):
    require(fields(rows)==values,'Native fields differ from exact route file')
    return sum(len(v) for v in values.values())


def compare(actual,saved):
    # Exact strict data retained. Zero TDCREATE can vary only the separately reported in-memory save flag.
    require({k:v for k,v in actual.items() if k!='save_metadata_changed'}==
            {k:v for k,v in saved.items() if k!='save_metadata_changed'},'Retained strict comparison differs')


def check(root,rendered=True):
    transfer.verify_methods()
    admission=read(HERE/'ADMISSION.json')
    require(read(root/'inputs/ADMISSION.json')==admission,'Derived admission receipt differs')
    native=root/'native-1';manifest=read(HERE/'NATIVE-INPUTS.json')
    require(read(native/'NATIVE.json')==manifest,'Frozen native manifest differs')
    for name,pin in manifest['inputs'].items():
        require(ch.digest(native/name)==pin,'Native input/recipe changed: '+name)
    for phase,ids in [('edit-save',[r['id'] for r in admission['cases']]),
                      ('fresh-readback',[r['id'] for r in read(native/'FRESH.json')['cases']])]:
        records=native_rows(native/'native'/(phase+'.stdout'),'ICT_QUAL_NATIVE ',ids)
        if phase=='edit-save':first=records
        else:fresh=records
    counts=[];first_fields=0;fresh_fields=0
    with tempfile.TemporaryDirectory(prefix='cad-public11-receive-') as tmp:
        for item,observed in zip(admission['cases'],first):
            identity=item['id'];original=root/'inputs'/identity/'original.dxf'
            raw=original.read_bytes()
            require(ch.digest(original)==item['original_sha256'] and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['git_blob_sha1'],'Upstream original changed')
            folder=native/'cases'/identity;source=folder/'source.dxf';plan=read(folder/'plan.json')
            require(ch.digest(source)==item['source_sha256'] and ch.digest(folder/'plan.json')==item['plan_sha256'],'Derived source/plan pin differs')
            produced=Path(tmp)/identity;patch.apply(source,plan,produced)
            candidate=folder/'candidate.dxf'
            require(candidate.read_bytes()==(produced/'candidate.dxf').read_bytes(),'Exact candidate reconstruction differs')
            verify(source,candidate,plan)
            require(not ch.compare(ch.snapshot(source),ch.snapshot(candidate),plan)['unexpected'],'Candidate strict differences')
            for role,path in [('source',source),('candidate',candidate),('native_default',folder/'returns/default.dxf'),('native_r15',folder/'returns/r15.dxf')]:
                first_fields+=native_fields(observed[role],expected(path))
            for name in ['default','r15']:
                result=ch.compare(ch.snapshot(source),ch.snapshot(folder/'returns'/(name+'.dxf')),plan)
                compare(result,read(folder/'returns'/(name+'.comparison.json')))
                counts.append(dict(id=identity,route=name,strict_differences=len(result['unexpected'])))
            library=root/'candidates'/identity/'library.dxf'
            result=ch.compare(ch.snapshot(source),ch.snapshot(library),plan)
            compare(result,read(root/'candidates'/identity/'library-save.comparison.json'))
            try:verify(source,library,plan)
            except ValueError:pass
            else:raise ValueError('Expected retained library byte failure disappeared')
        fresh_manifest=read(native/'FRESH.json')
        for record,case in zip(fresh,fresh_manifest['cases']):
            for role in ['source','candidate']:
                path=native/Path(case[role]).relative_to('/work')
                fresh_fields+=native_fields(record[role],expected(path))
    commands=read(native/'native/commands.json')
    require([r['id'] for r in commands]==['edit-save','fresh-readback','bounds'] and all(r['exit']==0 for r in commands),'Native commands incomplete/failed')
    require(commands[0]['configuration_sha256_before']==manifest['configuration_sha256'],'Native initial configuration differs')
    for a,b in zip(commands,commands[1:]):require(a['configuration_sha256_after']==b['configuration_sha256_before'],'Configuration chain reset')
    for r in commands:
        stderr=(native/'native'/(r['id']+'.stderr')).read_text(encoding='utf-8')
        require('absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"' in stderr,'Selected configuration stderr missing')
    require(read(native/'native-environment.json')['State']['Status']=='exited' and read(native/'native-environment.json')['State']['ExitCode']==0,'Native controller not normally terminal')
    summary=dict(cases=len(first),exact_candidates=len(first),native_strict=counts,
                 native_fields=first_fields,fresh_process_fields=fresh_fields,whole_cad_qualified=False,
                 remaining=['Complete rendered-image review','Actual fresh-cohort native UI edit/save/close/reopen',
                            'Planted-loss and second-revision controls on this cohort','Explain native full-save differences',
                            'Fresh foreign-payload/text/layout coverage; current public adaptation adds only ordinary test fields',
                            'Engineering/company acceptance not inferred'])
    if rendered:
        from PIL import Image
        jobs=read(HERE/'RENDERS.json');require(read(native/'RENDERS.json')==jobs,'Fixed render jobs changed')
        records=read(native/'renders/commands.json')
        require([r['id'] for r in records]==[j['id'] for j in jobs['jobs']],'Render coverage omitted/reordered')
        require(records[0]['configuration_sha256_before']==jobs['configuration_sha256'],'Initial render configuration differs')
        for a,b in zip(records,records[1:]):require(a['configuration_sha256_after']==b['configuration_sha256_before'],'Render configuration reset')
        for r,j in zip(records,jobs['jobs']):
            require(r['exit']==0 and ch.digest(native/'renders'/(r['id']+'.png'))==r['image_sha256'],'Render failed/altered')
            require(ch.digest(native/j['path'])==j['sha256'],'Rendered source changed')
            require('-window='+','.join(str(x) for x in j['window']) in r['command'],'Render frame differs')
            require('absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"' in (native/'renders'/(r['id']+'.stderr')).read_text(encoding='utf-8'),'Render selected settings missing')
            with Image.open(native/'renders'/(r['id']+'.png')) as im:require(im.size==(2400,1600),'Wrong render size')
        require(read(native/'render-environment.json')['State']['Status']=='exited' and read(native/'render-environment.json')['State']['ExitCode']==0,'Rendering not normally terminal')
        summary['retained_images']=len(records)
        from window import xywh
        corrected=read(native/'renders-corrected/commands.json')
        require([r['id'] for r in corrected]==[j['id'] for j in jobs['jobs']],'Corrected render coverage differs')
        require(corrected[0]['configuration_sha256_before']==jobs['configuration_sha256'],'Corrected initial configuration differs')
        for a,b in zip(corrected,corrected[1:]):require(a['configuration_sha256_after']==b['configuration_sha256_before'],'Corrected render configuration reset')
        for r,j in zip(corrected,jobs['jobs']):
            require(r['exit']==0 and ch.digest(native/'renders-corrected'/(r['id']+'.png'))==r['image_sha256'],'Corrected render failed/altered')
            require('-window='+','.join(str(x) for x in xywh(j['window'])) in r['command'],'Corrected XYWH frame differs')
            require('absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"' in (native/'renders-corrected'/(r['id']+'.stderr')).read_text(encoding='utf-8'),'Corrected render selected settings missing')
            with Image.open(native/'renders-corrected'/(r['id']+'.png')) as im:require(im.size==(2400,1600),'Wrong corrected render size')
        state=read(native/'corrected-environment.json')['State']
        require(state['Status']=='exited' and state['ExitCode']==0,'Corrected rendering not normally terminal')
        summary['corrected_images']=len(corrected)
    return summary


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--native-only',action='store_true');args=ap.parse_args()
    print(json.dumps(check(args.root,not args.native_only),indent=2))
