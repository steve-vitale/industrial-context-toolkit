"""Receive native save-boundary diagnostics offline; never launches native software."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
HERE=Path(__file__).resolve().parent
BASE=HERE/'save-boundaries-14'
sys.path[:0]=[str(HERE),str(BASE)]
import check_linux7 as old
def module(name):
    spec=importlib.util.spec_from_file_location('ict_boundaries14_'+name,BASE/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
f=module('followup_analysis');b=f.b
CONFIG='2c23f1511046e1ce876753efa354185a733d88e1264713ee13cc72d735f73a6c'
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
FREEZES={'attempt-1':'FREEZE.json','payload-2':'PAYLOAD-FREEZE.json','payload-3':'PAYLOAD-COMPLETE-FREEZE.json',
    'seed-0-a':'SEED-0-A-FREEZE.json','seed-0-b':'SEED-0-B-FREEZE.json','integer-4':'INTEGER-FREEZE.json'}
def equal(actual,retained):b.require(actual==retained,'Retained report differs from exact re-score')
def reassemble(root):
    chunks=b.read(root/'CHUNKS.json');seen=set()
    for name,pin in chunks.items():
        target=root/name
        b.require(target.resolve().is_relative_to(root.resolve())and not target.exists(),'Unsafe/duplicate chunk target')
        data=bytearray()
        for part in pin['parts']:
            b.require(part.startswith('chunks/')and(root/part).resolve().is_relative_to(root.resolve())and part not in seen,'Unsafe/reused chunk')
            seen.add(part);data.extend((root/part).read_bytes())
            b.require(len(data)<=256*1024*1024,'Unbounded reconstructed record')
        b.require(len(data)==pin['bytes']and hashlib.sha256(data).hexdigest()==pin['sha256'],'Reconstructed evidence differs')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    b.require(seen=={p.relative_to(root).as_posix()for p in(root/'chunks').rglob('*.part')},'Chunk omitted')

def receive(root):
    for name,pin in b.read(root/'METHODS.json').items():b.require(b.sha(BASE/name)==pin,'Bound diagnostic method differs: '+name)
    for folder,manifest in FREEZES.items():
        work=root/folder;freeze=b.read(work/'FREEZE.json');equal(freeze,b.read(BASE/manifest))
        b.require(freeze['configuration_sha256']==CONFIG,'Wrong supplied native settings')
        for name,pin in freeze['inputs'].items():b.require(b.sha(work/name)==pin,'Frozen native input differs: '+name)
        env=b.read(work/'ENVIRONMENT.json');state=env['state'];failed=folder=='payload-2'
        b.require(env['image']==IMAGE and env['user']=='1001:1001'and env['network']=='none'and
            state['Status']=='exited'and not state['Running']and not state['OOMKilled']and state['ExitCode']==(1 if failed else 0),'Native terminal state/profile differs')
        b.require(env['path']=='/usr/bin/python3'and env['args']==['/work/run_native.py']and len(env['mounts'])==1 and
            env['mounts'][0]['Destination']=='/work'and env['mounts'][0]['Type']=='bind','Native entrypoint/mount differs')
        seeded=folder.startswith('seed-0-');equal(env['qt_hash_seed'],['QT_HASH_SEED=0']if seeded else [])
        commands=b.read(work/'native/commands.json');b.require(len(commands)==(1 if failed else 2),'Native command omitted')
        for command in commands:
            name=command['id'];probe='native_payload.js'if folder.startswith(('payload','integer'))else'native_boundaries.js'
            equal(command['command'],['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
                '-config','/home/cad/.config/QCAD/QCAD3.conf','-font-substitution','Standard','DejaVu Sans',
                '-autostart','/work/'+probe,'-m','/work/'+name+'.json'])
            b.require(command['exit']==0 and command['configuration_sha256_before']==CONFIG,'Native command/config differs')
            b.require(('absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"').encode()in(work/'native'/(name+'.stderr')).read_bytes(),'Actual selected configuration missing')
            if seeded:b.require(command['qt_hash_seed']=='0','Seed command receipt differs')
        if failed:
            b.require(not(work/'native/COMPLETE.json').exists()and not(work/'native/fresh.stdout').exists(),'Incomplete probe promoted')
            b.require('Native incomplete/error'in b.read(work/'CONTAINER-LOG.json')['stderr'],'Incomplete probe refusal omitted')
            try:b.native_rows(work/'native/export.stdout',b.read(work/'export.json'))
            except ValueError:pass
            else:raise ValueError('Placeholder probe incorrectly accepted')
        else:
            equal(b.read(work/'native/COMPLETE.json'),dict(commands=2,jobs=len(b.read(work/'export.json')['jobs']),inputs_unchanged=True,whole_cad_qualified=False))
    first,reports=b.analyze(root/'attempt-1');equal(first,b.read(root/'attempt-1/analysis-raw-header/diagnosis.json'))
    for key,value in reports.items():equal(value,b.read(root/'attempt-1/analysis-raw-header'/(key.replace('/','--')+'.json')))
    original=b.read(HERE/'public-validation-11/NATIVE-INPUTS.json')['inputs']
    for identity in b.IDS:
        for name in('source.dxf','candidate.dxf','plan.json'):
            b.require(b.sha(root/'attempt-1/cases'/identity/name)==original['cases/'+identity+'/'+name],'Historical source/candidate/plan changed')
    payload,pr=f.analyze_payload(root/'payload-3');equal(payload,b.read(root/'followup-analysis/payload.json'))
    seeds,sr=f.analyze_seeds(root/'seed-0-a',root/'seed-0-b',root/'attempt-1');equal(seeds,b.read(root/'followup-analysis/seeds.json'))
    integer,ir=f.analyze_payload(root/'integer-4');equal(integer,b.read(root/'integer-analysis/payload.json'))
    for prefix,results in [('payload',pr),('seeds',sr)]:
        for key,value in results.items():equal(value,b.read(root/'followup-analysis'/(prefix+'--'+key.replace('/','--')+'.json')))
    for key,value in ir.items():equal(value,b.read(root/'integer-analysis'/(key.replace('/','--')+'.json')))
    for case in integer['cases']:
        b.require(case['literal_equal']['useri5']and case['literal_equal']['xdata']and case['literal_equal']['attributes'],'Valid selected metadata preservation differs')
        for stage in('imported','after_export','reopened'):
            equal(case['known_native'][stage]['USERI5'],dict(type='number',value=case['source']['useri5']))
        marker=case['source']['xrecord'][0][1].encode('ascii');folder=root/'integer-4/cases'/case['id']
        b.require((folder/'source.dxf').read_bytes().count(marker)==1 and (folder/'returned.dxf').read_bytes().count(marker)==0,
            'Foreign XRECORD marker was moved rather than omitted')
    for case in payload['cases']:
        b.require(case['returned']['useri5']==case['source']['useri5']-65536,'Out-of-range conversion differs')
    return dict(native_exports=first['jobs']+payload['jobs']+seeds['jobs']+integer['jobs'],
        fresh_public_inventory_repeats=first['fresh_public_inventory_repeats']+payload['fresh_public_inventory_repeats']+seeds['fresh_public_inventory_repeats']+integer['fresh_public_inventory_repeats'],
        strict_reports=len(reports)+len(pr)+len(sr)+len(ir),
        seed_repeat_strict_differences=[r['strict_differences']for r in seeds['comparisons']if r['comparison']=='seed0a_to_seed0b'],
        unseeded_to_seeded_differences=[r['strict_differences']for r in seeds['comparisons']if r['comparison']=='unseeded_to_seed0a'],
        source_to_original_differences=[r['strict_differences']for r in first['comparisons']if r['comparison']=='source_to_original'],
        empty_export_records={k:v['records']for k,v in first['empty_controls'].items()},
        valid_integer_controls=len(integer['cases']),out_of_range_controls=len(payload['cases']),
        missing_xrecord_controls=sum(c['returned']['xrecord']is None for c in integer['cases']),
        missing_unused_registration_controls=sum(not c['returned']['appids']['ICT_BOUND14_UNUSED']for c in integer['cases']),
        retained_incomplete_probe=True,exposure='All exposed/authored development; no fresh holdout',whole_cad_qualified=False)

def check():
    old.recheck.method_bindings()
    b.require(b.sha(BASE/'package.py')==b.read(BASE/'INVENTORY.json')['packager_sha256'],'Packager differs')
    with tempfile.TemporaryDirectory(prefix='ict-boundary14-')as temporary:
        root=old.unpack(BASE,Path(temporary));reassemble(root);result=receive(root)
    equal(result,b.read(BASE/'SUMMARY.json'));return result
if __name__=='__main__':print(json.dumps(check(),indent=2))
