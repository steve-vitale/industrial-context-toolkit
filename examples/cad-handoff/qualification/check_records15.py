"""Offline receive of crossed native record paths; no native/model execution."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
HERE=Path(__file__).resolve().parent
BASE=HERE/'record-paths-15'
sys.path[:0]=[str(HERE)]
import check_linux7 as old
spec=importlib.util.spec_from_file_location('ict_records15_analysis',BASE/'record_analysis.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);b=a.b
spec=importlib.util.spec_from_file_location('ict_records15_attribute_analysis',BASE/'attribute_analysis.py')
attributes=importlib.util.module_from_spec(spec);spec.loader.exec_module(attributes)
spec=importlib.util.spec_from_file_location('ict_records15_symbol_analysis',BASE/'symbol_analysis.py')
symbols=importlib.util.module_from_spec(spec);spec.loader.exec_module(symbols)
CONFIG='2c23f1511046e1ce876753efa354185a733d88e1264713ee13cc72d735f73a6c'
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
FREEZES=['FREEZE.json','EXPLICIT-FREEZE.json','DIRECTORY-FREEZE.json','COMPLETE-FREEZE.json']
def equal(actual,expected):b.require(actual==expected,'Retained report differs from exact re-score')
def receive(root):
    for name,pin in b.read(root/'METHODS.json').items():b.require(b.sha(BASE/name)==pin,'Diagnostic method differs: '+name)
    prior=None
    for index,manifest in enumerate(FREEZES,1):
        work=root/f'attempt-{index}';frozen=b.read(work/'FREEZE.json');equal(frozen,b.read(BASE/manifest))
        for name,pin in frozen['inputs'].items():b.require(b.sha(work/name)==pin,'Frozen input differs: '+name)
        if prior is not None:
            for name,pin in prior['inputs'].items():
                if name not in('native_records.js','run_native.py'):b.require(frozen['inputs'][name]==pin,'Successor changed data: '+name)
        prior=frozen
        b.require(frozen['configuration_sha256']==CONFIG,'Supplied profile differs')
        env=b.read(work/'ENVIRONMENT.json');state=env['state']
        b.require(env['image']==IMAGE and env['user']=='1001:1001'and env['network']=='none'and not env['qt_hash_seed']and
            state['Status']=='exited'and not state['Running']and not state['OOMKilled']and state['ExitCode']==1,'Native terminal identity/state differs')
        b.require(env['path']=='/usr/bin/python3'and env['args']==['/work/run_native.py']and len(env['mounts'])==1 and
            env['mounts'][0]['Type']=='bind'and env['mounts'][0]['Destination']=='/work','Wrong native entrypoint/mount')
        commands=b.read(work/'native/commands.json');b.require(len(commands)==(2 if index==4 else 1),'Native phase omitted')
        for command in commands:
            phase=command['id'];manifest_path='/work/export.json'if phase=='export'else'/work/native/fresh-success.json'
            equal(command['command'],['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
                '-config','/home/cad/.config/QCAD/QCAD3.conf','-font-substitution','Standard','DejaVu Sans',
                '-autostart','/work/native_records.js','-m',manifest_path])
            b.require(command['exit']==0 and command['configuration_sha256_before']==CONFIG and command['configuration_sha256_after']==CONFIG,'Native command/profile differs')
            if index==4:b.require(command['manifest_sha256']==b.sha(work/manifest_path.removeprefix('/work/')),'Derived manifest hash differs')
            b.require(b'absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"'in(work/'native'/(phase+'.stderr')).read_bytes(),'Actual settings selection absent')
        text=(work/'native/export.stdout').read_text(encoding='utf-8');errors=b.read(work/'CONTAINER-LOG.json')['stderr']
        if index<4:
            b.require(not(work/'native/COMPLETE.json').exists()and not(work/'native/fresh.stdout').exists(),'Early failure promoted')
            b.require('Native incomplete/error'in errors,'Earlier controller refusal omitted')
        if index==1:b.require('Ambiguous/missing OpenDesign null filter'in text,'Ambiguity failure omitted')
        if index==2:b.require('Can\'t open file:'in(work/'native/export.stderr').read_text(encoding='utf-8'),'Directory failure omitted')
        if index in(3,4):b.require('Invalid Symbol Table name'in(work/'native/export.stderr').read_text(encoding='utf-8'),'Engine failure omitted')
    pins=b.read(HERE/'save-boundaries-14/FREEZE.json')['inputs']
    for identity in b.IDS:
        for index in range(1,5):b.require(b.sha(root/f'attempt-{index}/cases'/identity/'original.dxf')==pins['cases/'+identity+'/source.dxf'],'Original source differs')
    result,reports=a.analyze(root/'attempt-4');equal(result,b.read(root/'attempt-4/analysis/diagnosis-count-corrected.json'))
    first=b.read(root/'attempt-4/analysis/diagnosis.json')
    b.require(first['exports']==5,'Original shadowed count omitted');equal(dict(first,exports=46),result)
    for key,value in reports.items():equal(value,b.read(root/'attempt-4/analysis'/(key.replace('/','--')+'.json')))
    attr=attributes.analyze(root/'attempt-4');equal(attr,b.read(root/'attempt-4/analysis/attribute-diagnosis.json'))
    earlier,pr=a.partial(root/'attempt-3');equal(earlier,b.read(root/'attempt-3/analysis/partial.json'))
    for key,value in pr.items():equal(value,b.read(root/'attempt-3/analysis'/(key.replace('/','--')+'.json')))
    failed=[r['id']for r in result['comparisons']if r['strict_status']=='native_failed']
    equal(b.read(root/'attempt-4/native/COMPLETE.json'),dict(commands=2,attempted_jobs=48,failed_jobs=failed,
        fresh_success_jobs=46,cohort_status='differences',inputs_unchanged=True,whole_cad_qualified=False))
    work=root/'symbol-5';frozen=b.read(work/'FREEZE.json');equal(frozen,b.read(BASE/'SYMBOL-FREEZE.json'))
    for name,pin in frozen['inputs'].items():b.require(b.sha(work/name)==pin,'Frozen name-control input differs: '+name)
    for namespace in('qcad','foreign'):
        b.require(b.sha(work/'cases'/namespace/'source.dxf')==b.sha(root/'attempt-4/cases/qcad-hydraulic'/namespace/'source.dxf'),'Name control changed source bytes')
    b.require(frozen['configuration_sha256']==CONFIG and frozen['image']==b.read(root/'attempt-4/FREEZE.json')['image'],'Name-control frozen environment differs')
    env=b.read(work/'ENVIRONMENT.json');state=env['state']
    b.require(env['image']==IMAGE and env['user']=='1001:1001'and env['network']=='none'and not env['qt_hash_seed']and
        state['Status']=='exited'and not state['Running']and not state['OOMKilled']and state['ExitCode']==1,'Name-control terminal identity/state differs')
    b.require(env['path']=='/usr/bin/python3'and env['args']==['/work/run_native.py']and len(env['mounts'])==1 and
        env['mounts'][0]['Type']=='bind'and env['mounts'][0]['Destination']=='/work','Name-control native entrypoint differs')
    commands=b.read(work/'native/commands.json');equal([c['id']for c in commands],['export','fresh'])
    for command in commands:
        phase=command['id'];manifest_path='/work/export.json'if phase=='export'else'/work/native/fresh-success.json'
        equal(command['command'],['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
            '-config','/home/cad/.config/QCAD/QCAD3.conf','-font-substitution','Standard','DejaVu Sans',
            '-autostart','/work/native_records.js','-m',manifest_path])
        b.require(command['exit']==0 and command['configuration_sha256_before']==CONFIG and command['configuration_sha256_after']==CONFIG and
            command['manifest_sha256']==b.sha(work/manifest_path.removeprefix('/work/')),'Name-control command/profile differs')
        b.require(b'absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"'in(work/'native'/(phase+'.stderr')).read_bytes(),'Name-control actual settings absent')
    b.require((work/'native/export.stderr').read_text(encoding='utf-8').splitlines().count('Warning:  Export Error:  "Invalid Symbol Table name"')==4,'Name-control engine failures differ')
    diagnostic=root/'symbol-receiver-failure'
    b.require(b.read(diagnostic/'RESULT.json')['exit']==1 and 'Name-control engine failures differ'in
        (diagnostic/'stderr.txt').read_text(encoding='utf-8'),'Earlier name receiver failure omitted')
    b.require(".count('Invalid Symbol Table name')==4"in(diagnostic/'check_records15.py').read_text(encoding='utf-8'),'Earlier failing receiver source omitted')
    symbol=symbols.analyze(work);equal(symbol,b.read(work/'analysis/symbol-diagnosis.json'))
    equal(b.read(work/'native/COMPLETE.json'),dict(commands=2,attempted_jobs=6,
        failed_jobs=['qcad/unchanged','qcad/unrelated','foreign/unchanged','foreign/unrelated'],
        fresh_success_jobs=2,cohort_status='differences',inputs_unchanged=True,whole_cad_qualified=False))
    matrix=[]
    for namespace in('qcad','foreign'):
        for importer in('OpenDesign','dxflib'):
            for exporter in('OpenDesign','dxflib'):
                rows=[r for r in result['comparisons']if(r['namespace'],r['importer'],r['exporter'])==(namespace,importer,exporter)]
                success=[r for r in rows if 'record_checks'in r]
                matrix.append(dict(namespace=namespace,importer=importer,exporter=exporter,attempted=len(rows),exports=len(success),
                    equal_ordered_tags={k:sum(r['record_checks'][k]['ordered_tags_equal']for r in success)for k in a.KEYS},
                    equal_paths={k:sum(r['record_checks'][k]['same_path']for r in success)for k in a.KEYS}))
    return dict(attempted_final_exports=48,completed_final_exports=result['exports'],fresh_public_inventory_repeats=result['fresh_public_inventory_repeats'],
        retained_earlier_exports=earlier['successful_exports'],final_statuses=dict(b.Counter(r['strict_status']for r in result['comparisons'])),
        final_failed_jobs=failed,final_returns_with_dangling_links=sum(any(x['type']=='dangling-reference'for x in r.get('returned_dictionary_records',[]))for r in result['comparisons']),
        dxflib_imported_attributes_parented_to_modelspace=sum(x['parent_target']is not None and x['parent_target']['name']=='*Model_Space'
            for row in attr['observations']if '/dxflib-'in row['id']for x in row['native_parents'].get('imported',[])),
        dxflib_returns_without_attribute_sequence_markers=sum(not any(x['type']=='SEQEND'or
            (x['type']=='INSERT'and any(code==66 for code,value in x['tags']))for x in row['raw_entity_sequences'])
            for row in attr['observations']if row['id'].endswith('-dxflib')and'raw_entity_sequences'in row),
        literal_tag_matrix=matrix,symbol_controls=symbol,retained_ambiguity_and_directory_failures=True,whole_cad_qualified=False,
        exposure='Twelve paired authored revisions of six exposed inputs; no fresh qualification')
def check():
    old.recheck.method_bindings()
    b.require(b.sha(BASE/'package.py')==b.read(BASE/'INVENTORY.json')['packager_sha256'],'Packager differs')
    with tempfile.TemporaryDirectory(prefix='ict-record15-')as temporary:
        root=old.unpack(BASE,Path(temporary));result=receive(root)
    equal(result,b.read(BASE/'SUMMARY.json'));return result
if __name__=='__main__':print(json.dumps(check(),indent=2))
