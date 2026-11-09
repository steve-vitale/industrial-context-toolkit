"""Receive actual final native API fields and saved-file differences; no native invocation."""
import argparse
from pathlib import Path
from campaign import HERE, ROOT, read, write, sha, binding, require
import cad_handoff as ch


def groups(rows):
    values={}
    for row in rows:
        attrs=row['attributes'];identity=attrs.get('ICT_ID')
        require(identity and identity not in values,'Unprofiled/duplicate native attribute group')
        values[identity]=attrs
    return values


def receive(api,host):
    binding();declared=read(HERE/'NATIVE-PREPARATION.json')['files'];launch=read(HERE/'NATIVE-LAUNCH.json')
    require(sha(HERE/'NATIVE-PREPARATION.json')==launch['native_preparation_sha256'],'Pre-execution native preparation differs')
    for name,pin in declared.items():
        if name.startswith('api/'):require(sha(api/name[4:])==pin,'Pre-execution native API input differs: '+name)
    require(read(host/'EXIT.json')['exit']==0,'Original final API host failed')
    require(sha(host/'SCRIPT.py')==launch['host_wrappers']['run_final_api_host.py'],'Original native API host wrapper differs')
    terminal=read(host/'AFTER.json')[0]
    require(terminal['State']['Status']=='exited' and terminal['State']['ExitCode']==0 and terminal['Image']==read(HERE/'FREEZE.json')['native_image'] and terminal['HostConfig']['NetworkMode']=='none','Final API native terminal/image/network differs')
    commands=read(api/'native/commands.json')
    require([r['id'] for r in commands]==['edit-save','fresh-readback','bounds'] and all(r['exit']==0 for r in commands),'Final API process coverage differs')
    expected_config=read(HERE/'FREEZE.json')['configuration_sha256']
    parsed={}
    for row in commands:
        require(row['configuration_sha256_before']==expected_config,'Native API selected configuration differs')
        stdout=(api/'native'/(row['id']+'.stdout')).read_text(encoding='utf-8');stderr=(api/'native'/(row['id']+'.stderr')).read_text(encoding='utf-8')
        require('absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"' in stderr and 'ICT_TRANSFER11_PROFILE ' in stdout,'Actual native profile not evidenced')
        prefix='ICT_VIEW_BOUNDS ' if row['id']=='bounds' else 'ICT_QUAL_NATIVE '
        parsed[row['id']]=[__import__('json').loads(line[len(prefix):]) for line in stdout.splitlines() if line.startswith(prefix)]
        manifest=read(api/('FRESH.json' if row['id']=='fresh-readback' else 'BATCH.json'))
        require([r['id'] for r in parsed[row['id']]]==[r['id'] for r in manifest['cases']],'Native API row coverage differs')
    snapshots={};rows=[]
    for supplied in read(HERE/'INPUTS.json')['cases']:
        if supplied['status']!='admitted':continue
        identity=supplied['id'];source=ROOT/supplied['source'];plan=read(ROOT/supplied['plan']);before={a['id']:a['attributes'] for a in ch.snapshot(source)['assets']};after={k:dict(v) for k,v in before.items()}
        for change in plan['changes']:after[change['id']][change['attribute']]=change['after']
        snapshots[identity]=(before,after);result=dict(id=identity,field_checks=[],native_saves=[]);rows.append(result)
        for role in ('baseline','edited'):
            native=next(v for v in parsed['edit-save'] if v['id']==identity+'-'+role);expected=before if role=='baseline' else after
            for key,wanted in [('source',before),('candidate',expected),('native_default',expected),('native_r15',expected)]:
                try:actual=groups(native[key]);result['field_checks'].append(dict(phase=role,key=key,match=actual==wanted,expected=wanted,actual=actual))
                except Exception as error:result['field_checks'].append(dict(phase=role,key=key,match=False,error=type(error).__name__+': '+str(error)))
            for version in ('default','r15'):
                path=api/'returned'/(identity+'-'+role+'-'+version+'.dxf');comparison=ch.compare(ch.snapshot(source),ch.snapshot(path),plan if role=='edited' else None)
                result['native_saves'].append(dict(role=role,format=version,path='returned/'+path.name,sha256=sha(path),dxfversion=ch.load(path).dxfversion,strict_unexpected=len(comparison['unexpected']),strict_status=comparison['status'],comparison=comparison))
        for suffix in ('source-candidate','default','r15'):
            native=next(v for v in parsed['fresh-readback'] if v['id']==identity+'-'+suffix)
            for key,wanted in [('source',before),('candidate',after)]:
                try:actual=groups(native[key]);result['field_checks'].append(dict(phase='fresh-'+suffix,key=key,match=actual==wanted,expected=wanted,actual=actual))
                except Exception as error:result['field_checks'].append(dict(phase='fresh-'+suffix,key=key,match=False,error=type(error).__name__+': '+str(error)))
        result['all_native_fields_match']=all(r['match'] for r in result['field_checks'])
    return dict(scope='Actual saved/reopened/fresh-process native API field observations on ten frozen procedural/public-adapted cases; not UI equivalence or engineering acceptance',cases=rows,
        fields_match=sum(r['all_native_fields_match'] for r in rows),native_save_files=sum(len(r['native_saves']) for r in rows),whole_cad_qualified=False,
        boundaries='Native default/R15 format observations are distinct from the separately declared UI R27 route. Every strict difference remains unresolved unless separately explained.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','host','out'):p.add_argument(name,type=Path)
    a=p.parse_args();require(not a.out.exists(),'New API receipt required');r=receive(a.api,a.host);write(a.out,r)
    print('Native API field cases',r['fields_match'],'/',len(r['cases']),'saved files',r['native_save_files'],'whole CAD qualified',r['whole_cad_qualified'])
