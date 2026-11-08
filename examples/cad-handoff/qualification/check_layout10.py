"""Rebuild proposed layout revisions and replay retained native comparisons; no CAD/UI execution."""
import copy
import json
from pathlib import Path
import sys
import tempfile

from PIL import Image,ImageChops

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import check_linux7 as old
import check_receiver8
import prepare_layout10 as prepare
import verify_layout10
import layout_controls10

BASE=HERE/'layout-preparation-10'
read,require,ch=old.read,old.require,old.ch
IDS=('validation-braces','validation-cp1251','validation-foreign','validation-long','validation-unicode')
ROUTES=('original','library','library-main','prepared','candidate')


def native_values(observed,expected):
    grouped={}
    for attr in observed:
        bucket=grouped.setdefault(attr['parent'],{})
        require(attr['tag'] not in bucket,'Duplicated native field')
        bucket[attr['tag']]=attr['text']
    require(all('ICT_ID' in g for g in grouped.values()),'Native identity missing')
    require(len({g['ICT_ID'] for g in grouped.values()})==len(grouped),'Duplicate native asset identity')
    require({g['ICT_ID']:g for g in grouped.values()}==expected,'Native planned/foreign values differ')


def native_layout(row,job,source):
    require(not row.get('error') and row['id']==job['id'] and row['path']==job['path'],'Native route identity/error')
    blocks=[b for b in row['observed']['layouts'] if b['layout']==job['layout']]
    require(len(blocks)==1,'Native paper block missing/duplicated')
    expected=[]
    if job['route'] in ('library-main','prepared','candidate'):
        doc=ch.load(source)
        for v in doc.layouts.get(job['layout']).query('VIEWPORT'):
            if v.dxf.id==1:continue
            x,y=v.dxf.center.x,v.dxf.center.y
            expected.append(dict(type=47,bounds=[x-v.dxf.width/2,y-v.dxf.height/2,x+v.dxf.width/2,y+v.dxf.height/2]))
    actual=[{k:v for k,v in e.items() if k!='id'} for e in blocks[0]['entities']]
    require(actual==expected,'Original native display viewport bounds differ')


def image(path):
    with Image.open(path) as im:
        require(im.size==(2400,1600),'Native paper image dimensions differ')
        return im.convert('RGB')


def delta(a,b):
    im=ImageChops.difference(a,b);raw=im.tobytes()
    return dict(different_pixels=sum(1 for r,g,b in zip(raw[::3],raw[1::3],raw[2::3]) if r or g or b),
                bbox=list(im.getbbox()) if im.getbbox() else None)


def coverage(rows,jobs):
    require([r['id'] for r in rows]==[j['id'] for j in jobs],'Native route omitted/reordered')


def selected_profile(receipt,expected):
    require(receipt['configuration_file']==expected,'Actual selected native configuration not verified')


def comparison(actual,retained,label,metadata_observations):
    # The frozen comparator already excludes named save metadata from strict fields.
    # Loading the same zero-date bytes across a clock tick can change this boolean.
    # Keep both observations; never discard a strict field or a retained failure.
    require({k:v for k,v in actual.items() if k!='save_metadata_changed'}==
            {k:v for k,v in retained.items() if k!='save_metadata_changed'},label)
    metadata_observations.append(dict(case=label,retained=retained['save_metadata_changed'],
                                      observed=actual['save_metadata_changed']))


def check():
    old.recheck.method_bindings()
    freeze,correction,inputs=(read(BASE/name) for name in ('FREEZE.json','NATIVE-SETUP-CORRECTION.json','INPUTS.json'))
    actual=read(BASE/'ACTUAL-PROFILE-FREEZE.json')
    for path,pin in freeze['methods_lf'].items():
        expected=actual['driver_sha256_lf'] if path=='layout-preparation-10/run_native.py' else pin
        require(old.recheck.text_hash(HERE/path)==expected,'Frozen/corrected layout method differs: '+path)
    require(old.recheck.text_hash(BASE/'native_profile.js')==actual['observer_sha256_lf']
            and actual['unchanged_routes']==freeze['routes'] and actual['excluded_batches']==['native-1','native-2'],
            'Actual-profile correction changed/waived inputs')
    require(correction['original_driver_lf']==freeze['methods_lf']['layout-preparation-10/run_native.py'], 'Driver correction lost original binding')
    require(old.recheck.text_hash(HERE/'package_layout10.py')==read(BASE/'INVENTORY.json')['packager_sha256_lf'],'Packager changed')
    require([(j['case_id'],j['route']) for j in inputs['jobs']]==[(c,r) for c in IDS for r in ROUTES], 'Declared five-route cohort changed')
    pixels=[];field_count=0;strict_counts=[];metadata_observations=[]
    with tempfile.TemporaryDirectory(prefix='ict-layout10-replay-') as temp:
        root=Path(temp);raw=old.unpack(BASE,root/'evidence')
        raw3=old.unpack(BASE/'receiving-4',root/'receiving-4')
        require(read(BASE/'receiving-4/INVENTORY.json')['packager_sha256_lf']==old.recheck.text_hash(HERE/'package_layout10.py'),
                'Supplementary archive packager differs')
        failed=raw3/'native-3'
        failed_state=read(failed/'terminal.json');failed_env=read(failed/'environment.json')
        require(failed_state['Status']=='exited' and failed_state['Running'] is False
                and failed_state['ExitCode']==137 and failed_state['OOMKilled'] is False
                and failed_env['State']==failed_state and failed_env['Path']=='dbus-run-session'
                and failed_env['Args']==['--','/opt/desktop.sh','/usr/bin/python3','/work/run_native.py']
                and not (failed/'native').exists() and not (failed/'native-profile.json').exists(),
                'Unintended desktop launch promoted to native evidence')
        require(read(failed/'MANIFEST.json')==inputs and read(failed/'ENTRYPOINT-FAILURE.json')['observed_path']=='dbus-run-session',
                'Unintended desktop failure/input record changed')
        require(all(ch.digest(failed/j['path'])==j['sha256'] for j in inputs['jobs']),
                'Unintended desktop changed a frozen drawing')
        cases=old.recheck.cohort()
        expected_cohort=[]
        for case in cases:
            output=root/'rebuilt'/case['id']
            output.parent.mkdir(exist_ok=True)
            try:receipt=prepare.apply(case['source'],output)
            except ch.InputError as error:
                row=dict(id=case['id'],status='refused',error=str(error))
            else:
                checked=verify_layout10.verify(case['source'],output/'prepared.dxf',ch.digest(case['source']))
                row=dict(id=case['id'],status=receipt['status'],layouts=len(receipt['layouts']),byte_check=checked)
                retained=raw/'development-3/cohort'/case['id']
                require((retained/'original.dxf').read_bytes()==case['source'].read_bytes(),'Retained original changed')
                require((retained/'prepared.dxf').read_bytes()==(output/'prepared.dxf').read_bytes(),'Prepared bytes do not rebuild')
                require(read(retained/'revision.json')==receipt,'Producer receipt does not rebuild')
                comparison(ch.compare(ch.snapshot(case['source']),ch.snapshot(output/'prepared.dxf')),
                           read(retained/'original-to-prepared-strict.json'),
                           'Deliberate source-revision strict differences: '+case['id'],metadata_observations)
            expected_cohort.append(row)
        require(expected_cohort==inputs['cohort']==read(raw/'development-3/cohort-results.json'),'21-case structural results differ')
        require([sum(r['status']==status for r in expected_cohort) for status in ('proposed_source_revision','exact_noop','refused')]==[5,14,2],
                'Original preparation/refusal coverage differs')
        controls=layout_controls10.check(root/'controls')
        require(controls==read(raw/'controls-1/controls.json') and len(controls['controls'])==17,'Semantic controls do not reproduce')
        states={}
        for batch in ('native-1','native-2','native-4'):
            work=(raw3 if batch=='native-4' else raw)/batch;manifest=read(work/'MANIFEST.json')
            require(manifest==inputs,'Retained input manifest differs')
            state=read(work/'terminal.json');check_receiver8.normal_exit(state);states[batch]=state
            environment=read(work/'environment.json')
            require(environment['State']==state and environment['Image']==freeze['image'],'Native receiver identity/state differs')
            require(old.recheck.text_hash(work/'native_probe.js')==freeze['methods_lf']['layout-preparation-10/native_probe.js'], 'Executed native probe differs')
            wanted_driver=({'native-1':correction['original_driver_lf'],
                            'native-2':correction['corrected_driver_lf'],
                            'native-4':actual['driver_sha256_lf']})[batch]
            require(old.recheck.text_hash(work/'run_native.py')==wanted_driver,'Executed native driver differs')
            configuration=work/'native/configuration-before.json'
            if batch=='native-1':
                require(not configuration.exists() and read(work/'HOST-NOTES.json')['excluded_from_declared_profile'] is True,
                        'Wrong-profile batch promoted to accepted evidence')
            else:
                config=read(configuration)
                require(config['source_sha256']==config['installed_sha256']==freeze['config_sha256']
                        and config['verified_before_native_start'] is True,'Native setup profile not verified')
            if batch=='native-4':
                created=read(work/'HOST-CREATED.json')
                require(created['verified_before_start'] is True and created['Path']=='/usr/bin/python3'
                        and created['Args']==['/work/run_native.py'] and created['Image']==freeze['image']
                        and created['User']=='cad' and not created['PortBindings']
                        and len(created['Mounts'])==1 and created['Mounts'][0]['Destination']=='/work',
                        'Receiving CLI setup was not verified before start')
                require(old.recheck.text_hash(work/'native_profile.js')==actual['observer_sha256_lf'],
                        'Selected-profile observer changed')
                selected_profile(read(work/'native-profile.json'),actual['planned_actual_configuration_file'])
            commands=read(work/'native/commands.json')
            require([r['id'] for r in commands]==['probe']+[j['id'] for j in inputs['jobs']]
                    and all(r['exit']==0 and r['finished']>=r['started'] for r in commands),'Native commands incomplete/failed')
            require(all(a['finished']<=b['started'] for a,b in zip(commands,commands[1:])),'Native commands overlapped')
            selected=actual['planned_actual_configuration_file'] if batch=='native-4' else '/work/qcad-config'
            for command in commands:
                require(command['command'][command['command'].index('-config')+1]==selected
                        and ('absConfigFile: "'+selected+'"').encode() in (work/'native'/(command['id']+'.stderr')).read_bytes(),
                        'Actual native command/settings selection differs')
                if batch=='native-4':
                    require(all(len(command[k])==64 for k in ('configuration_sha256_before','configuration_sha256_after')),
                            'Per-command settings digest missing')
            if batch=='native-4':
                require(commands[0]['configuration_sha256_before']==freeze['config_sha256'],
                        'First native command did not start with intended settings')
                require(all(a['configuration_sha256_after']==b['configuration_sha256_before']
                            for a,b in zip(commands,commands[1:])),'Settings reset/changed between native commands')
            complete=read(work/'native/COMPLETE.json')
            require(complete['commands']==26 and complete['paper_images']==25 and complete['input_unchanged'] is True,'Native completion differs')
            require(read(work/'native/before.json')==read(work/'native/after.json')==freeze['routes'],'Native input pins changed')
            rows=read(work/'native-probe.json')['rows'];coverage(rows,inputs['jobs'])
            for row,job in zip(rows,inputs['jobs']):
                path=work/job['path']
                require(ch.digest(path)==job['sha256']==freeze['routes'][job['path']],'Native route bytes changed')
                case=next(c for c in cases if c['id']==job['case_id'])
                native_layout(row,job,case['source'])
                expected={a['id']:a['attributes'] for a in ch.snapshot(path)['assets']}
                native_values(row['observed']['attributes'],expected)
                if batch=='native-4':field_count+=sum(len(a) for a in expected.values())
                result=ch.compare(ch.snapshot(case['source']),ch.snapshot(path))
                comparison(result,read(work/job['case_id']/(job['route']+'-from-original-strict.json')),
                           batch+':'+job['id'],metadata_observations)
                require(len(result['unexpected'])==job['strict_from_original'],'Strict source-revision count differs')
                if batch=='native-4':strict_counts.append(dict(id=job['id'],differences=len(result['unexpected'])))
            for case_id in IDS:
                case=next(c for c in cases if c['id']==case_id)
                prepared=work/case_id/'prepared.dxf';candidate=work/case_id/'candidate.dxf'
                plan=copy.deepcopy(read(case['plan']));plan['source_sha256']=ch.digest(prepared)
                require(plan==read(work/case_id/'candidate-plan.json'),'Rebound plan changed')
                old.cad_value_patch.apply(prepared,plan,root/(batch+'-'+case_id))
                require((root/(batch+'-'+case_id)/'candidate.dxf').read_bytes()==candidate.read_bytes(),'Attribute candidate does not rebuild')
                require(old.verify(prepared,candidate,plan)==read(work/case_id/'candidate-byte-check.json'),'Independent attribute byte reconstruction differs')
                require(ch.compare(ch.snapshot(prepared),ch.snapshot(candidate),plan)['unexpected']==[],'Prepared-to-candidate strict failure')
                ims={r:image(work/'native'/(case_id+'-'+r+'.png')) for r in ROUTES}
                for a,b in (('original','library'),('library-main','prepared'),('prepared','candidate')):
                    pixels.append(dict(batch=batch,case_id=case_id,before=a,after=b,**delta(ims[a],ims[b])))
                if batch=='native-4':
                    require(delta(ims['library-main'],ims['prepared'])['different_pixels']==0,'Minimal/library-main native paper images differ')
                for r in ROUTES:
                    command=next(c for c in commands if c['id']==case_id+'-'+r)
                    require(ch.digest(work/'native'/(case_id+'-'+r+'.png'))==command['image_sha256'],'Native image digest differs')
        require(states['native-1']['FinishedAt']<states['native-2']['StartedAt'],'Wrong-profile and verified native batches overlapped')
        require(states['native-2']['FinishedAt']<states['native-4']['StartedAt'],'Selected-profile native batch overlapped a previous live batch')
        require(states['native-2']['FinishedAt']<failed_state['StartedAt']
                and failed_state['FinishedAt']<states['native-4']['StartedAt'],'Unintended desktop overlapped evidence batches')
        repeat=[dict(id=j['id'],**delta(image(raw/'native-2/native'/(j['id']+'.png')),
                                       image(raw3/'native-4/native'/(j['id']+'.png')))) for j in inputs['jobs']]
        require(repeat==read(BASE/'profile-repeat-comparisons.json') and all(r['different_pixels']==0 for r in repeat),
                'Reused visual inspection does not match selected-profile images')
        require(pixels==read(BASE/'pixel-comparisons.json'),'Native pixel comparisons do not reproduce')
        summary=read(BASE/'summary.json')
        require(summary['whole_cad_qualified'] is False and summary['native_field_values_verified']==field_count
                and summary['original_to_route_strict_counts']==strict_counts,'Summary changed/promoted to qualification')
        require(summary['receiving_batch']=='native-4' and summary['excluded_native_batches']==['native-1','native-2','native-3']
                and summary['actual_configuration_file']==actual['planned_actual_configuration_file'],
                'Published receiving profile promoted an excluded batch')
        require([summary[k] for k in ('structural_cases','minimal_proposals','exact_noops','unsupported_r12_refusals',
                'verified_profile_paper_images','semantic_input_controls','receiving_controls',
                'prepared_to_candidate_strict_unexpected','prepared_to_candidate_unplanned_bytes')]
                ==[21,5,14,2,25,17,3,0,0],'Published coverage differs')
        require(summary['library_main_to_minimal_prepared_pixels']==[p for p in pixels
                if p['batch']=='native-4' and p['before']=='library-main'],'Published paper comparison differs')
        visual=read(BASE/'VISUAL-REVIEW.json')['observations']
        coverage(visual,inputs['jobs'])
        require(all(v['inspected'] is True and v['complete_readability'] is False
                and v['paper_content_visible']==(j['route'] in ('library-main','prepared','candidate'))
                and v['image']=='native-4/native/'+j['id']+'.png' for v,j in zip(visual,inputs['jobs'])),
                'Visual review omitted a route or overclaimed readability')
        for name,member in summary['published_images'].items():
            require((BASE/name).read_bytes()==(raw3/member).read_bytes(),'Published native image differs')
        # Receiving controls operate on decoded semantic data after archive verification.
        try:coverage(rows[:-1],inputs['jobs'])
        except ValueError:pass
        else:raise ValueError('Omitted native route accepted')
        corrupt=copy.deepcopy(rows[0]['observed']['attributes']);corrupt[0]['text']='lost'
        expected={a['id']:a['attributes'] for a in ch.snapshot(raw3/'native-4'/inputs['jobs'][0]['path'])['assets']}
        try:native_values(corrupt,expected)
        except ValueError:pass
        else:raise ValueError('Changed native field accepted')
        wrong_profile=copy.deepcopy(read(raw3/'native-4/native-profile.json'))
        wrong_profile['configuration_file']='/work/qcad-config'
        try:selected_profile(wrong_profile,actual['planned_actual_configuration_file'])
        except ValueError:pass
        else:raise ValueError('Installed-but-unselected native settings accepted')
    print('PASS: 21-case structural replay, 5 minimal source revisions/candidates, 25 verified-profile paper views, 17 semantic/input controls')
    print('Original layout/full-save failures retained; compatibility proposals are exposed development, not fresh qualification or company authority')
    print('Informational save-metadata flags (retained and current loaded observations): '+json.dumps(metadata_observations))
    return summary


if __name__=='__main__':check()
