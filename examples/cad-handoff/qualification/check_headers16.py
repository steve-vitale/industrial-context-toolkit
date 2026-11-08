"""Receive frozen header/dimension controls offline; retain every strict/fresh failure."""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
HERE=Path(__file__).resolve().parent;BASE=HERE/'header-boundaries-16'
sys.path[:0]=[str(HERE)]
import check_linux7 as old
spec=importlib.util.spec_from_file_location('ict_header16_analysis',BASE/'analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);b=a.b
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
CONFIG='2c23f1511046e1ce876753efa354185a733d88e1264713ee13cc72d735f73a6c'
def equal(actual,expected):b.require(a.typed(actual)==a.typed(expected),'Header retained report differs from exact re-score')
def safe(root,name):
    p=PurePosixPath(name)
    b.require(not p.is_absolute()and p.as_posix()==name and'..'not in p.parts and':'not in name and'\\'not in name and bool(p.parts),'Unsafe reassembly path')
    result=root.joinpath(*p.parts);b.require(result.resolve().is_relative_to(root.resolve()),'Reassembly escapes receiving root');return result
def reassemble(root):
    assembly=b.read(root/'REASSEMBLY.json');seen=set();total=0
    for name,pin in assembly.items():
        target=safe(root,name);b.require(not target.exists()and 0<pin['bytes']<=64*1024*1024,'Invalid reassembly target/size')
        data=bytearray()
        for part in pin['parts']:
            source=safe(root,part);b.require(part.startswith('chunks/')and part not in seen and source.is_file(),'Duplicate/missing assembly part')
            seen.add(part);data.extend(source.read_bytes());b.require(len(data)<=pin['bytes'],'Oversized assembly')
        total+=len(data);b.require(total<=128*1024*1024 and len(data)==pin['bytes']and hashlib.sha256(data).hexdigest()==pin['sha256'],'Reassembled file differs/unbounded')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    b.require(seen=={p.relative_to(root).as_posix()for p in(root/'chunks').rglob('*.part')},'Unreferenced assembly chunk')

def receive(root):
    for name,pin in b.read(root/'METHODS.json').items():b.require(b.sha(BASE/name)==pin,'Header method differs: '+name)
    source_pins=b.read(HERE/'save-boundaries-14/FREEZE.json')['inputs'];results=[]
    for folder,manifest,exit_code in[('attempt-1','FREEZE.json',1),('dimension-2','DIMENSION-FREEZE.json',0)]:
        work=root/folder;freeze=b.read(work/'FREEZE.json');equal(freeze,b.read(BASE/manifest))
        for name,pin in freeze['inputs'].items():b.require(b.sha(work/name)==pin,'Header frozen input differs: '+name)
        equal(b.read(work/'KEYS.json'),b.read(BASE/'KEYS.json'))
        b.require(freeze['configuration_sha256']==CONFIG and freeze['image']==IMAGE,'Header frozen environment differs')
        for identity in b.IDS:b.require(b.sha(work/'cases'/identity/'source.dxf')==source_pins['cases/'+identity+'/source.dxf'],'Header original source differs')
        env=b.read(work/'ENVIRONMENT.json');state=env['state']
        b.require(env['image']==IMAGE and env['user']=='1001:1001'and env['network']=='none'and not env['qt_hash_seed']and
            state['Status']=='exited'and not state['Running']and not state['OOMKilled']and state['ExitCode']==exit_code,'Header native terminal identity/state differs')
        equal(env['resources'],dict(NanoCpus=2000000000,Memory=3*1024**3,ShmSize=256*1024**2,PidsLimit=256,CapDrop=['ALL'],SecurityOpt=['no-new-privileges']))
        b.require(env['path']=='/usr/bin/python3'and env['args']==['/work/run_native.py']and len(env['mounts'])==1 and env['mounts'][0]['Type']=='bind'and env['mounts'][0]['Destination']=='/work','Header native entrypoint/mount differs')
        commands=b.read(work/'native/commands.json');equal([c['id']for c in commands],['export','fresh'])
        for command in commands:
            phase=command['id'];path='/work/export.json'if phase=='export'else'/work/native/fresh-success.json'
            equal(command['command'],['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances','-config',
                '/home/cad/.config/QCAD/QCAD3.conf','-font-substitution','Standard','DejaVu Sans','-autostart','/work/native_headers.js','-m',path])
            b.require(command['exit']==0 and command['configuration_sha256_before']==CONFIG and command['configuration_sha256_after']==CONFIG and
                command['manifest_sha256']==b.sha(work/path.removeprefix('/work/')),'Header native command/profile differs')
            b.require(b'absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"'in(work/'native'/(phase+'.stderr')).read_bytes(),'Header selected settings absent')
        cases=b.read(work/'CASES.json');equal([c['id']for c in cases],list(b.IDS));expected=[]
        for case in cases:
            identity=case['id'];version={'AC1015':'R15','AC1021':'R21','AC1024':'R24'}[case['version']]
            variants=[(i+'-'+e,i,e,None)for i in('OpenDesign','dxflib')for e in('OpenDesign','dxflib')]if folder=='attempt-1'else[
                (label+'-'+e,'OpenDesign',e,label)for label in('unchanged','known','style','unrelated')for e in('OpenDesign','dxflib')]
            for label,importer,exporter,operation in variants:
                job=dict(id=identity+'/'+label,input='/work/cases/'+identity+'/source.dxf',output='/work/cases/'+identity+'/returns/'+label+'.dxf',
                    importer=importer,exporter=exporter,version=version if exporter=='OpenDesign'else'R15')
                if operation is not None:job['operation']=operation
                expected.append(job)
        if folder=='attempt-1':
            expected +=[dict(id='empty/'+e,input=None,output='/work/cases/empty/returns/'+e+'.dxf',importer=e,exporter=e,version='R24'if e=='OpenDesign'else'R15')for e in('OpenDesign','dxflib')]
        equal(b.read(work/'export.json'),dict(jobs=expected))
        result,reports=a.analyze(work)if folder=='attempt-1'else a.dimensions(work)
        equal(result,b.read(work/'analysis/diagnosis.json'))
        for key,report in reports.items():equal(report,b.read(work/'analysis'/(key.replace('/','--')+'.json')))
        count=26 if folder=='attempt-1'else 48;failed=['qcad-hydraulic/dxflib-OpenDesign']if folder=='attempt-1'else[]
        equal(b.read(work/'native/COMPLETE.json'),dict(commands=2,attempted_jobs=count,failed_jobs=failed,fresh_success_jobs=count-len(failed),
            cohort_status='diagnostic_coverage_with_failures'if failed else'diagnostic_coverage_only',inputs_unchanged=True,whole_cad_qualified=False))
        results.append(result)
    for folder,message in[('analysis-syntax-failure','SyntaxError'),('analysis-fresh-failure','Fresh header/public inventory differs')]:
        b.require(b.read(root/folder/'RESULT.json')['exit']==1 and message in(root/folder/'stderr.txt').read_text(encoding='utf-8'),'Earlier header analysis failure omitted')
    b.require(b.read(root/'HOST-LAUNCH-FAILURE.json')['exit']==1,'Host daemon failure omitted')
    first,dim=results;fresh=[r for r in first['observations']if r.get('fresh_public_inventory_equal')is False]
    return dict(observation_jobs=first['attempted_jobs'],observation_exports=first['exports'],observation_fresh_imports=first['fresh_imports'],
        observation_exact_public_inventory_repeats=first['fresh_public_inventory_repeats'],observation_strict_statuses=first['strict_statuses'],
        fresh_layout_differences=[dict(id=r['id'],differences=r['fresh_public_inventory_differences'])for r in fresh],
        dimension_jobs=dim['attempted_jobs'],dimension_exports=dim['exports'],dimension_exact_public_inventory_repeats=dim['fresh_public_inventory_repeats'],
        dimension_strict_statuses=dim['strict_statuses'],exact_single_cell_operations=sum(r['operation_exact']for r in dim['observations']),
        directional_DIMASZ_controls=sum(r['raw_returned_DIMASZ']==(9.875 if '/style-'in r['id']else r['source_style_DIMASZ']['value'])for r in dim['observations']),
        whole_cad_qualified=False,exposure='Six previously exposed adapted sources, no new holdout or UI/readability/revision qualification')
def check():
    old.recheck.method_bindings();b.require(b.sha(BASE/'package.py')==b.read(BASE/'INVENTORY.json')['packager_sha256'],'Header packager differs')
    with tempfile.TemporaryDirectory(prefix='ict-headers16-')as temporary:
        root=old.unpack(BASE,Path(temporary));reassemble(root);result=receive(root)
    equal(result,b.read(BASE/'SUMMARY.json'));return result
if __name__=='__main__':print(json.dumps(check(),indent=2))
