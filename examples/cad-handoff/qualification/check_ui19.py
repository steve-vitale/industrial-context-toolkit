"""Receive retained exposed native UI evidence offline; no native launch or qualification promotion."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import traceback

HERE=Path(__file__).resolve().parent;BASE=HERE/'native-ui-pairs-19';ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'scripts'))
from ui19_archive import read,sha,require,equal,unpack
import cad_handoff as ch
from verify_bytes import verify
from PIL import Image
import diagnose_ui19
import ui19_metadata
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
analysis=module('cad_ui19_analysis',BASE/'analyze.py')
controls=module('cad_ui19_controls',BASE/'native_controls.py')

def walk(node):
    yield node
    for child in node.get('children',[]):yield from walk(child)
def fields(tree):
    found={}
    for n in walk(tree):
        children=n.get('children',[])
        if n.get('role')=='panel'and children and children[0].get('role')=='label'and children[0].get('name')=='Attributes':
            require(len(children)%2==1,'Incomplete native attribute panel')
            for label,value in zip(children[1::2],children[2::2]):
                require(label['role']=='label'and label['name'].endswith(':'),'Missing native attribute label')
                tag=label['name'][:-1];require(tag not in found,'Ambiguous native attribute field');found[tag]=value
    return found
def values(row,expected):
    require(set(row)==set(expected),'Omitted/added native fields')
    require(all(n.get('text')==expected[tag]and n.get('enabled')is True and n.get('editable')is True and n.get('showing')is True for tag,n in row.items()),'Native displayed values/editability differ')
def native_values(row,expected):
    attrs=row['attributes'];require(len(attrs)==len(expected),'Native attribute inventory differs')
    require({a['tag']for a in attrs}==set(expected),'Native attribute tags differ')
    require({a['text']for a in attrs if a['tag']=='ICT_ID'}=={expected['ICT_ID']},'Native identity differs')
    require(len({a['parent_id']for a in attrs})==1 and len({a['parent_handle']for a in attrs})==1,'Native attributes have ambiguous parent')
    require(all(a['text']==expected[a['tag']]for a in attrs),'Native stored values differ')
def control_trace(actions,basis,role):
    bindings=[r for r in actions if r['kind']=='selection_binding']
    paths=(['/work/source.dxf','/work/returned.dxf']if role=='baseline'else
           ['/work/source.dxf','/work/source.dxf','/work/returned.dxf']if role=='edited'else
           ['/work/'+n+'.dxf'for n in ('source','baseline','edited','candidate')])
    require(len(bindings)==len(paths),'Native selection coverage differs')
    for binding,path in zip(bindings,paths):
        previous=[r['reply']for r in actions[:binding['event']-1]if r['kind']=='native_observation'][-1]
        require(previous['filename']==path and binding['identity']==basis['attributes']['ICT_ID']and binding['source_handle']==basis['handle'],'Native selection basis differs')
        identity=[a for a in previous['attributes']if a['tag']=='ICT_ID'and a['text']==binding['identity']]
        require(len(identity)==1 and binding['observed_handle']==identity[0]['parent_handle'],'Native selection handle not observed')
        if path in ('/work/source.dxf','/work/candidate.dxf'):require(binding['observed_handle']==basis['handle'],'Original handle changed')
    handles=[r['observed_handle']for r in bindings]
    expected_types=(['/work/source.dxf',handles[0],'/work/returned.dxf','/work/returned.dxf',handles[1]]if role=='baseline'else
                    ['/work/source.dxf',handles[0],handles[1],'QUAL-AFTER','/work/returned.dxf','/work/returned.dxf',handles[2]]if role=='edited'else
                    [v for path,handle in zip(paths,handles)for v in (path,handle)])
    typed=[r for r in actions if r['kind']=='control'and r['operation']=='type']
    require([r['text']for r in typed]==expected_types,'Native text-entry coverage differs')
    for row in [r for r in actions if r['kind']=='control']:
        node=row['observed'];operation=row['operation'];require(node['enabled']is True and node['showing']is True,'Native control disabled/hidden')
        following=actions[row['event']];cmd=['python3','/work/ui_control.py',operation,node['path']]
        if row['text']is not None:cmd.append(row['text'])
        require(following['kind']=='command'and following['command']==cmd and following['exit']==0,'Native control dispatch missing')
        reply=json.loads(following['stdout']);require(reply['path']==node['path']and reply['operation']==operation and reply['name']==node['name']and reply['role']==node['role'],'Control observation/dispatch differs')
        if operation=='focus':require(reply['focus_result']is True,'Native focus refused');continue
        x,y,w,h=node['rectangle'];click=['xdotool','mousemove','--sync',str(x+w//2),str(y+h//2),'click','1']
        require(reply['commands'][0]['command']==click and all(r['exit']==0 for r in reply['commands']),'Native observed-bounds click differs')
        if operation=='press':require(reply['event_dispatched']is True,'Native click dispatch failed')
        else:require(reply['typed_text']==row['text']and reply['focus_result']is True and reply['active_window']['exit']==0,'Native field text/focus check differs')
    opening=['Escape','Escape','ctrl+o'];select=['Escape','Escape','t','h'];deselect=['Escape','Escape','t','n'];close=['Escape','Escape','ctrl+w'];save=['Escape','Escape','ctrl+shift+s']
    expected_keys=([opening,select,deselect,save,close,opening,select,deselect,close]if role=='baseline'else
                   [opening,select,deselect,select,save,close,opening,select,deselect,close]if role=='edited'else
                   [v for _ in range(4)for v in (opening,select,deselect,close)])
    keys=[r['command'][3:]for r in actions if r['kind']=='command'and r['command'][:3]==['xdotool','key','--clearmodifiers']]
    require(keys==expected_keys,'Native open/select/deselect/save/close sequence differs')
def environment(job,failed=False):
    env=read(job/'ENVIRONMENT.json');prior=read(HERE/'layout-construction-17/FREEZE.json');state=env['state']
    require(env['image']==prior['image']and env['user']=='1001:1001'and env['network']=='none'and env['special_environment']==[],'Native execution identity changed')
    require(state['Status']=='exited'and state['Running']is False and state['OOMKilled']is False,'Native process not terminal')
    require(state['ExitCode']==(1 if failed else 0),'Native container exit differs')
    require(env['path']=='dbus-run-session'and env['args']==['--','python3','/work/launch_case.py'],'Native launcher changed')
    require(len(env['mounts'])==1 and env['mounts'][0]['Destination']=='/work'and env['mounts'][0]['Type']=='bind','Native mount differs')
    require(env['resources']==dict(NanoCpus=2000000000,Memory=3*1024**3,ShmSize=256*1024**2,PidsLimit=256,CapDrop=['ALL'],SecurityOpt=['no-new-privileges']),'Native resource limits changed')
    process=read(job/'native/PROCESS.json');require(process['exit']==0 and process['controller_exit']==(1 if failed else 0),'Native/controller terminal result differs')
    require(process['configuration_before']==prior['configuration_sha256']and len(process['configuration_after'])==64,'Selected settings differ')
    require(process['command']==['/opt/qcad/qcad','-allow-multiple-instances','-config','/home/cad/.config/QCAD/QCAD3.conf','-font-substitution','Standard','DejaVu Sans','-exec','/work/observe_case.js'],'Native command changed')
    return process
def job_check(job,basis,cohort):
    job_basis=read(job/'job.json');role=job_basis['role'];require(role in ('baseline','edited','receiving'),'Wrong role')
    require(equal({k:v for k,v in job_basis.items()if k!='role'},basis),'Native job basis changed')
    process=environment(job);require(equal(process['job'],job_basis),'Actual process job differs')
    result=read(job/'ui/RESULT.json');require(result==dict(status='controller-complete',role=role,case=basis['case'],whole_cad_qualified=False),'Native completion result differs')
    require(not(job/'ui/FAILURE.json').exists(),'Clean job contains a failure')
    frozen=read(job/'JOB-FREEZE.json')
    required={'PLAN.md','METHOD.md','observe_case.js','workflow.py','launch_case.py','inspect_ui.py','ui_control.py','prepare.py','native_controls.py','job.json','source.dxf','.configuration/QCAD3.conf'}
    if role=='receiving':required|={'baseline.dxf','edited.dxf','candidate.dxf'}
    require(set(frozen['files'])==required,'Frozen job input coverage differs')
    for name,pin in frozen['files'].items():
        if name=='.configuration/QCAD3.conf':require(pin==process['configuration_before'],'Original configuration pin changed');continue
        path=job/name;require(path.resolve().is_relative_to(job.resolve())and sha(path)==pin,'Job input changed: '+name)
    for name in required&set(cohort['methods']):require(frozen['files'][name]==cohort['methods'][name],'Job is not the frozen cohort method')
    actions=read(job/'ui/actions.json');require([r['event']for r in actions]==list(range(1,len(actions)+1)),'Native action missing/reordered')
    require([r['at']for r in actions]==sorted(r['at']for r in actions),'Native action clock order differs')
    commands=[r for r in actions if r['kind']=='command'];require(commands and all(r['exit']==0 for r in commands),'Native command failure omitted')
    control_trace(actions,basis,role)
    require(any(r['command']==['ps','-eo','pid,ppid,stat,etime,args']and'/opt/qcad/qcad-bin -platform xcb'in r['stdout']for r in commands),'Actual native binary process missing')
    observed=[r['reply']for r in actions if r['kind']=='native_observation'];require([r['request']['seq']for r in observed]==list(range(1,len(observed)+1)),'Read-only observation missing/reordered')
    require({p.name for p in(job/'replies').glob('*.json')}=={str(r['request']['seq'])+'.json'for r in observed},'Read-only reply coverage differs')
    before=basis['attributes'];after=dict(before,MANUFACTURER='QUAL-AFTER')
    for r in observed:
        require(equal(r,read(job/'replies'/(str(r['request']['seq'])+'.json'))),'Native reply differs from action record')
        require('error'not in r and r['qt']=='5.14.2'and r['configuration_file']=='/home/cad/.config/QCAD/QCAD3.conf','Read-only native observation failed')
        path=r['filename']
        if path=='':require(r['modified']is False and r['attributes']==[],'Untitled document changed');continue
        require(path in ['/work/'+n+'.dxf'for n in ('source','returned','baseline','edited','candidate')],'Wrong native filename')
        if role=='receiving':
            require(path!='/work/returned.dxf'and r['modified']is False,'Receiving changed document');expected=after if path in ('/work/edited.dxf','/work/candidate.dxf')else before
        elif path=='/work/source.dxf':
            require(r['modified']is False or(role=='edited'and r['modified']is True),'Unexpected native modification');expected=after if r['modified']else before
        else:
            require(path=='/work/returned.dxf'and r['modified']is False,'Wrong return state');expected=after if role=='edited'else before
        native_values(r,expected)
    selected=[r for r in actions if r['kind']=='native_fields']
    expected_rows=([before,before]if role=='baseline'else[before,before,after,after])
    require(len(selected)==len(expected_rows),'Native editable-field coverage differs')
    snapshots=sorted(p for p in(job/'ui').glob('*.json')if p.name.endswith(('-selected.json','-edited.json')))
    require(len(snapshots)==len(selected),'Selected field tree coverage differs')
    recording_mismatches=[]
    for row,snapshot,expected in zip(selected,snapshots,expected_rows):
        # Source/phase keys are independent of the recorder's mutable expected dictionary.
        # Preserve a mismatch as a failed recording check; never relabel its metadata as correct.
        if not equal(row['expected'],expected):recording_mismatches.append(dict(event=row['event'],recorded=row['expected'],source_phase_expected=expected))
        values(row['observed'],expected)
        actual=fields(read(snapshot));values(actual,expected);require(equal(actual,row['observed']),'Field values/paths do not match captured tree')
    edits=[r for r in actions if r['kind']=='control'and r.get('operation')=='type'and r.get('text')=='QUAL-AFTER']
    require(len(edits)==(1 if role=='edited'else 0),'Native edit coverage differs')
    if edits:
        edit=edits[0];require(edit['observed']['path']==selected[1]['observed']['MANUFACTURER']['path'],'Wrong native attribute edited')
        response=json.loads(actions[edit['event']]['stdout']);require(response['typed_text']=='QUAL-AFTER'and response['focus_result']is True and response['active_window']['stdout'].strip()=='Property Editor','Field activation/input evidence differs')
    saved=[r for r in actions if r['kind']=='returned_file'];require(len(saved)==(0 if role=='receiving'else 1),'Native returned-file coverage differs')
    if saved:require(saved[0]['path']=='/work/returned.dxf'and saved[0]['sha256']==sha(job/'returned.dxf'),'Returned file differs')
    capture_rows=[r for r in actions if r['kind']=='capture']
    labels=['source','returned']if role!='receiving'else['source','baseline','edited','candidate']
    require([(r['label'],r['frame'])for r in capture_rows]==[(label,frame)for label in labels for frame in basis['frames']],'Native view coverage missing/reordered')
    images=set()
    for capture in capture_rows:
        obs=capture['observation'];require(any(equal(obs,r)for r in observed),'Capture not bound to native observation')
        require(obs['request']['frame']==basis['frames'][capture['frame']]and obs['filename']=='/work/'+('returned'if capture['label']=='returned'else capture['label'])+'.dxf','Capture filename/frame differs')
        x,y,w,h=capture['canvas']['rectangle'];require([w,h]==[obs['view']['width'],obs['view']['height']]and x>=0 and y>=0 and w>0 and h>0,'Native canvas/view differs')
        require(2<=len(capture['images'])<=10,'Native stable-frame coverage differs')
        require(capture['images'][-1]['pixel_sha256']==capture['images'][-2]['pixel_sha256'],'Native canvas not stable')
        for image in capture['images']:
            name=image['path'];require(Path(name).name==name and name.endswith('.png')and'\\'not in name,'Unsafe native image path')
            require(name not in images,'Native frame reused');images.add(name);crop_name=Path(name).with_suffix('.canvas.png').name;images.add(crop_name)
            with Image.open(job/'ui'/name)as full,Image.open(job/'ui'/crop_name)as crop:
                require(full.size==(2400,1400)and crop.size==(w,h),'Native screenshot dimensions differ')
                actual=full.crop((x,y,x+w,y+h));require(actual.tobytes()==crop.tobytes(),'Native screenshot crop differs')
                import hashlib
                require(hashlib.sha256(crop.tobytes()).hexdigest()==image['pixel_sha256'],'Native canvas pixels differ')
    require({p.name for p in(job/'ui').glob('*.png')}==images,'Native screenshot omitted or unregistered')
    return dict(role=role,fields=len(selected),observations=len(observed),views=len(capture_rows),images=len(images),process_exit=process['exit'],
                recording=dict(status='failed'if recording_mismatches else'pass',expected_metadata_mismatches=recording_mismatches))

def receive_case(root,out):
    cohort=read(root/'cohort/COHORT.json');cases=list((root/'cases').iterdir());require(len(cases)==1,'Wrong packet case scope')
    case=cases[0];name=case.name;basis=read(case/'basis.json');prior=read(HERE/'layout-construction-17/FREEZE.json')
    require(basis['source_sha256']==prior['inputs']['cases/'+name+'/source.dxf']==sha(case/'source.dxf'),'Prior exposed source changed')
    for method,pin in cohort['methods'].items():
        require(Path(method).name==method and sha(root/'cohort/methods'/method)==pin==sha(BASE/method),'Frozen native method differs')
    require(cohort['image']==prior['image']and cohort['max_running']==4,'Native cohort changed')
    expected_cases=['libre-air-water','libre-motion','libre-power','qcad-hydraulic','qcad-mechanical','qcad-template']
    require([(r['case'],r['role'])for r in cohort['jobs']]==[(c,role)for c in expected_cases for role in ('baseline','edited','receiving')],'Declared cohort omitted/reordered')
    jobs=root/'jobs';require({p.name for p in jobs.iterdir()}=={name+'-'+r for r in ('baseline','edited','receiving')},'Packet job scope differs')
    plan=read(case/'plan.json');before=ch.snapshot(case/'source.dxf');require(before['assets'][0]['attributes']==basis['attributes']and len(before['assets'])==1,'Source asset basis differs')
    require(verify(case/'source.dxf',case/'software/candidate/candidate.dxf',plan)['status']=='pass','Candidate byte check failed')
    job_results=[]
    for role in ('baseline','edited','receiving'):
        job=jobs/(name+'-'+role);require((job/'source.dxf').read_bytes()==(case/'source.dxf').read_bytes(),'Staged source changed')
        job_results.append(job_check(job,basis,cohort))
        if role!='receiving':
            expected=dict(basis['attributes'])
            if role=='edited':expected['MANUFACTURER']='QUAL-AFTER'
            doc=ch.load(job/'returned.dxf');require(doc.dxfversion=='AC1027','Native returned DXF version differs from Save As format');returned=ch.assets(doc)
            require(len(returned)==1 and equal(returned[0]['attributes'],expected),'DXF returned attribute readback differs')
    receiver=jobs/(name+'-receiving')
    for role in ('baseline','edited'):require((receiver/(role+'.dxf')).read_bytes()==(jobs/(name+'-'+role)/'returned.dxf').read_bytes(),'Receiving native return differs')
    require((receiver/'candidate.dxf').read_bytes()==(case/'software/candidate/candidate.dxf').read_bytes(),'Receiving exact-span candidate differs')
    original_failure=None
    try:results=analysis.analyze(root/'cases',jobs,out)
    except ValueError as error:
        if str(error)!='Native camera/canvas changed':raise
        original_failure=dict(error=str(error),scope='Original exact-camera gate remains failed; subsequent pixel counts are diagnostic')
        (out/'ORIGINAL-ANALYSIS-FAILURE.json').write_text(json.dumps(dict(**original_failure,traceback=traceback.format_exc()),indent=2)+'\n',encoding='utf-8')
        results=None
    diagnostic=diagnose_ui19.pixels(analysis,receiver,out/'complete-pixel-diagnostics')
    if results is not None:
        require(all(v['status']=='complete'for v in results[0]['native'].values()),'Incomplete clean UI case')
        for original,new in zip(results[0]['pixels'],diagnostic):
            require(all(equal(original[k],new[k])for k in original),'Diagnostic differs from original pixel calculation')
        initial=read(BASE/'validation/INITIAL-SUMMARY.json')
        prior=next(c for c in initial['packets'][1:]if c['case']==name)['analysis']['candidate_strict']['save_metadata_changed']
        retained=ui19_metadata.candidate_report(results[0]['candidate_strict'],case/'source.dxf',case/'software/candidate/candidate.dxf',prior,out/'candidate-comparison-parser.json')
        results[0]['candidate_strict']=retained['comparison']
        results[0]['candidate_save_metadata']=retained['save_metadata']
    native_strict={}
    for role in ('baseline','edited'):
        comparison=read(out/(name+'-'+role+'-strict.json'));native_strict[role]=len(comparison['unexpected'])
    paired=read(out/(name+'-paired-strict.json'))
    return dict(case=name,jobs=job_results,analysis=results[0]if results else None,original_analysis_failure=original_failure,
                native_strict_differences=native_strict,paired_strict_differences=len(paired['unexpected']),pixels=diagnostic,whole_cad_qualified=False)

def historical(root,out):
    pre=root/'preflight-1';close=read(pre/'16-normal-close.json');process=read(pre/'native/PROCESS.json')
    require(close['exit']==0 and close['no_file_created']is True and close['status_before_close']['filename']==''and close['status_before_close']['modified']is False and process['exit']==0,'Startup-only preflight changed')
    require(read(pre/'01-acknowledge-trial.json')['exit']==1 and'Expected one observed native action'in read(pre/'01-acknowledge-trial.json')['stderr'],'Preflight action-count failure omitted')
    require(read(pre/'04-open-dialog-action.json')['exit']==1 and'Did not receive a reply'in read(pre/'04-open-dialog-action.json')['stderr'],'Preflight modal timeout omitted')
    for name,pin in read(pre/'FREEZE.json')['inputs'].items():require(sha(pre/name)==pin,'Original preflight method changed')
    failed=root/'jobs-1/libre-air-water-baseline';require(read(failed/'ENVIRONMENT.json')['state']['ExitCode']==2 and"can't open file '/work/launch_case.py'"in read(failed/'CONTAINER-LOG.json')['stderr'],'Empty staging launch failure omitted')
    for folder,filename in [('jobs-2','/work/source.dxf'),('jobs-3','')]:
        job=root/folder/'libre-air-water-baseline';environment(job,True)
        require('Ambiguous/missing'in read(job/'ui/FAILURE.json')['traceback'],'Original MDI failure omitted')
        close=read(job/'normal-close-failed.json');require(close['exit']==0 and close['observation']['filename']==filename and close['observation']['modified']is False,'Failed run normal close changed')
    for relative,filename in [('jobs-2/libre-air-water-baseline/ui/004-opened.json','/work/source.dxf'),('jobs-3/libre-air-water-baseline/ui/002-ready.json','')]:controls.active_canvas(read(root/relative),filename)
    baseline=root/'jobs-4/libre-air-water-baseline';edited=root/'jobs-4/libre-air-water-edited';environment(baseline);environment(edited,True)
    require('Native field set differs: []'in read(edited/'ui/FAILURE.json')['traceback'],'Wrong-window failure omitted')
    obs=read(edited/'replies/900.json');require(obs['modified']is False and len(obs['selected'])==14,'Wrong-window native observation omitted');native_values(obs,read(edited/'job.json')['attributes'])
    recovery=read(edited/'ui-focus-recovery/RESULT.json');require(recovery['status']=='recovery-complete'and recovery['whole_cad_qualified']is False and read(edited/'focus-recovery/EXIT.json')['exit']==0,'Recovery history differs')
    for name,pin in read(edited/'focus-recovery/FREEZE.json')['files'].items():require(sha(edited/'focus-recovery'/name)==pin,'Recovery frozen method changed')
    expected=dict(read(edited/'job.json')['attributes'],MANUFACTURER='QUAL-AFTER')
    returned=ch.assets(ch.load(edited/'returned.dxf'));require(len(returned)==1 and equal(returned[0]['attributes'],expected),'Recovered DXF values differ')
    receiver=root/'receiver-1';require(read(receiver/'EXIT.json')['exit']==1 and'Field expectation changed'in(receiver/'stderr.txt').read_text(encoding='utf-8'),'Original expectation-metadata refusal omitted')
    for name,pin in read(receiver/'FREEZE.json').items():require(sha(receiver/name)==pin,'Original receiver source changed')
    camera=root/'receiver-2';require(read(camera/'EXIT.json')['exit']==1 and'Native camera/canvas changed'in(camera/'stderr.txt').read_text(encoding='utf-8'),'Original camera failure omitted')
    for name,pin in read(camera/'FREEZE.json').items():require(sha(camera/name)==pin,'Original camera receiver source changed')
    plan=dict(schema='cad-edit-plan-1',source_sha256=sha(baseline/'returned.dxf'),changes=[dict(id=read(edited/'job.json')['attributes']['ICT_ID'],attribute='MANUFACTURER',before='QUAL-BEFORE',after='QUAL-AFTER',reason='Development diagnosis')])
    pair=ch.compare(ch.snapshot(baseline/'returned.dxf'),ch.snapshot(edited/'returned.dxf'),plan)
    require(len(pair['unexpected'])==57,'Historical paired differences changed')
    images={}
    out.mkdir()
    for frame in read(baseline/'job.json')['frames']:
        a,ai=analysis.capture(baseline,'source',frame);b,bi=analysis.capture(baseline,'returned',frame)
        require(a['observation']['view']==b['observation']['view']and a['canvas']['rectangle']==b['canvas']['rectangle'],'Historical camera differs')
        images[frame]=analysis.image_pair(ai,bi,None,out/(frame+'.png'));require(images[frame]['changed_pixels']==0,'Historical no-edit pixels changed')
    return dict(route='historical-development',paired_strict_differences=len(pair['unexpected']),baseline_pixels=images,original_edited_controller_failed=True,recovery_is_clean_pass=False,whole_cad_qualified=False)

def package_identity(base,source_hashes):
    require(read(base/'INVENTORY.json')['packager_sha256']in source_hashes,'UI evidence packager source not retained')

def packaging_reproduction():
    folder=BASE/'validation';rows=read(folder/'PACKAGER-REPRODUCTION.json')['cases']
    require([r['case']for r in rows]==['libre-air-water','libre-motion'],'Packaging reproduction coverage differs')
    for row in rows:
        original=BASE/'evidence'/row['case']/'INVENTORY.json';recorded=read(original)
        require(row['reproduced_inventory']==row['case']+'-current-INVENTORY.json','Packaging reproduction path differs')
        current=read(folder/row['reproduced_inventory'])
        require(sha(original)==row['recorded_inventory_sha256']and row['archive_byte_identical']is True,'Original packaging evidence differs')
        require(current['packager_sha256']==sha(HERE/'package_ui19.py'),'Reproduced packager differs')
        require(equal(dict(recorded,packager_sha256=current['packager_sha256']),current),'Reproduced archive/inventory differs')
    require(read(folder/'full-suite-1/EXIT.json')['exit']==1 and'UI evidence packager differs'in(folder/'full-suite-1/stdout.txt').read_text(encoding='utf-8'),'Original failed packaging check omitted')

def check():
    methods=read(BASE/'REPLAY-METHODS.json')
    expected=['examples/cad-handoff/qualification/'+name for name in ('check_ui19.py','diagnose_ui19.py','ui19_archive.py','ui19_metadata.py','package_ui19.py','verify_bytes.py')]+['scripts/cad_handoff.py']
    require(set(methods)==set(expected),'UI evidence replay method scope differs')
    # Repository Python text can be checked out as CRLF; native evidence retains exact byte hashes.
    for name,pin in methods.items():
        require(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==pin,'UI evidence replay method differs: '+name)
    summaries=[];live_parser_diagnostics=[];packagers={sha(HERE/'package_ui19.py')}
    with tempfile.TemporaryDirectory(prefix='ict-ui19-')as temporary:
        temp=Path(temporary)
        for packet in ['development','libre-air-water','libre-motion','libre-power','qcad-hydraulic','qcad-mechanical','qcad-template']:
            base=BASE/'evidence'/packet
            package_identity(base,packagers)
            root=unpack(base,temp/packet)
            summaries.append(historical(root,temp/(packet+'-out'))if packet=='development'else receive_case(root,temp/(packet+'-out')))
            parser_report=temp/(packet+'-out')/'candidate-comparison-parser.json'
            if parser_report.exists():live_parser_diagnostics.append(dict(case=packet,comparison=read(parser_report),status='Load-time diagnostic, not a reproducible source-metadata claim'))
            if packet=='development':
                # These exact historical sources are already checked by historical() against their freezes.
                packagers.update(sha(root/receiver/'package_ui19.py')for receiver in ('receiver-1','receiver-2'))
    packaging_reproduction()
    result=dict(packets=summaries,whole_cad_qualified=False)
    require(equal(result,read(BASE/'SUMMARY.json')),'Published UI evidence summary differs')
    return dict(result,live_parser_diagnostics=live_parser_diagnostics)
if __name__=='__main__':print(json.dumps(check(),indent=2))
