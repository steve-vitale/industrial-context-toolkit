"""Receive and re-score retained causal CAD controls offline; never launches native software."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
BASE=HERE/'root-cause-12'
sys.path[:0]=[str(BASE),str(HERE)]
import analyze
import diagnose
import pixel_analysis
import check_linux7 as old
from verify_bytes import verify

require=analyze.require
read=analyze.read
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
FREEZES={'attempt-1':'FREEZE.json','attempt-2':'PRESERVE-FREEZE.json','attempt-3':'BEFORE-LOAD-FREEZE.json',
    'pixels-1':'PIXEL-FREEZE.json','pixels-2':'PIXEL-BEGIN-FREEZE.json','pixels-3':'PIXEL-DEVICE-FREEZE.json',
    'pixels-4':'PIXEL-COPY-FREEZE.json','pixels-5':'PIXEL-HAIRLINE-FREEZE.json'}

def equal_report(actual,retained):
    require(actual==retained,'Retained causal report differs from exact re-score')

def receive_environment(root,folder):
    env=read(root/folder/'ENVIRONMENT.json');state=env['state']
    require(env['image']==IMAGE and env['user']=='1001:1001' and env['network']=='none','Wrong receiver isolation/profile')
    require(state['Status']=='exited' and state['Running']is False and not state['OOMKilled'] and
            state['ExitCode']==(1 if folder=='pixels-1' else 0),'Native controller not terminal as recorded')
    require(env['path']=='/usr/bin/python3' and env['args']==['/work/'+('run_native.py' if folder.startswith('attempt') else 'run_pixels.py')],
            'Wrong explicit container entrypoint')
    require(len(env['mounts'])==1 and env['mounts'][0]['Type']=='bind' and env['mounts'][0]['Destination']=='/work',
            'Unexpected mounted receiving input')

def receive_pixels(root,folder):
    work=root/folder;command=read(work/'native/command.json')
    require(command['exit']==0 and command['configuration_sha256_before']==read(work/'FREEZE.json')['configuration_sha256'],
            'Native raster command/profile differs')
    require(command['command']==['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
        '-config',analyze.CONFIG,'-autostart','/work/native_pixels.js'],'Raster command differs')
    require(command['font_sha256']=='6e482dd6c45bd3738d6e8cc3661d82193b6385eac613b2d15730bf91a303b18a' and command['font_bytes']==23818,'Raster font differs')
    require(('absConfigFile: "'+analyze.CONFIG+'"').encode()in(work/'native/stderr').read_bytes(),'Raster actual settings missing')
    lines=(work/'native/stdout').read_text(encoding='utf-8').splitlines()
    profiles=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_PIXEL12_PROFILE ')]
    require(profiles==[dict(configuration_file=analyze.CONFIG)],'Raster selected profile differs')
    rows=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_PIXEL12 ')]
    if folder=='pixels-1':
        require(not rows and not list((work/'images').glob('*.png')) and any('could not find a function match' in s for s in lines),
            'Original raster failure omitted/upgraded')
        require(not(work/'native/COMPLETE.json').exists(),'Failed raster attempt has a success receipt')
        return
    spec=read(work/'PIXEL-INPUTS.json')
    require([(r['role'],r['profile'])for r in rows]==[(role,p['id'])for role in ('source','candidate')for p in spec['profiles']],
            'Raster case/profile coverage differs')
    require(not any(s.startswith('ICT_PIXEL12_FATAL ')for s in lines),'Successful raster attempt reported fatal')
    require(read(work/'native/COMPLETE.json')==dict(images=len(rows),inputs_unchanged=True),'Raster completion differs')
    expected={role+'-'+p['id']+'.png'for role in ('source','candidate')for p in spec['profiles']}
    if folder=='pixels-3':expected.add('device-control.png')
    require({p.name for p in(work/'images').glob('*.png')}==expected,'Raster images omitted/added')
    if folder=='pixels-3':
        devices=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_PIXEL12_DEVICE ')]
        paths=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_PIXEL12_PATH ')]
        require(len(devices)==1 and devices[0]['pixel']==devices[0]['expected_yellow']==4294967040,'Known-answer painter device failed')
        require(len(paths)==4 and all(p['elements']<0 for p in paths),'Invalid inherited-path observations concealed')
    if folder in ('pixels-4','pixels-5'):
        elements=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_PIXEL12_ELEMENTS ')]
        require([e['role']for e in elements]==['source','candidate'] and all(e['paths'] and all(p for p in e['paths'])for e in elements),
            'Copied native path elements absent')

def summary(root,analyses,pixels):
    first=analyses[0]['comparisons'];fixed=analyses[1]['comparisons']
    total=lambda name:sum(r['strict_differences']for r in first if r['comparison']==name)
    return dict(source_cases=6,exposure='All six sources exposed development; no fresh holdout',
        native_exports=sum(r['exports']for r in analyses),fresh_process_fields=sum(r['native_fields_per_stage']for r in analyses),
        fresh_keyed_property_repeats=sum(r['fresh_keyed_property_repeats']for r in analyses),
        original_noedit_strict_rows=total('source_to_noop'),second_noedit_strict_rows=total('first_to_second'),
        fixed_default_matched_differences=[r['strict_differences']for r in fixed if r['comparison']=='noop_to_edited' and r['format']=='default'],
        fixed_r15_matched_differences=[r['strict_differences']for r in fixed if r['comparison']=='noop_to_edited' and r['format']=='r15'],
        before_load_count_vectors_equal=[r['strict_differences']for r in analyses[1]['comparisons']]==[r['strict_differences']for r in analyses[2]['comparisons']],
        original_outside_text_pixels=pixels['pixels-4']['original_outside_pixels'],
        raster_profiles_with_exact_gui_delta=sum(r['whole_canvas_delta_mismatching_pixels']==0 for name in ('pixels-4','pixels-5')for r in pixels[name]['profiles']),
        whole_cad_qualified=False,remaining=['Native full-save strict preservation and unresolved record payloads',
            'Exact 62-pixel renderer cause; geometric/stroked-bound hypothesis not fully reproduced',
            'Complete readable receiving / fresh native UI and revision qualification','Engineering/company acceptance'])

def check():
    old.recheck.method_bindings()
    require(old.recheck.text_hash(BASE/'package.py')==read(BASE/'INVENTORY.json')['packager_sha256_lf'],'Packager differs')
    analyses=[];pixels={}
    with tempfile.TemporaryDirectory(prefix='ict-root12-')as temporary:
        root=old.unpack(BASE,Path(temporary)/'evidence')
        previous=read(HERE/'public-validation-11/NATIVE-INPUTS.json')['inputs']
        for folder,manifest in FREEZES.items():
            freeze=read(root/folder/'FREEZE.json');equal_report(freeze,read(BASE/manifest))
            for name,pin in freeze['inputs'].items():require(analyze.sha(root/folder/name)==pin,'Frozen native input differs')
            for name,pin in freeze['methods_sha256_lf'].items():require(old.recheck.text_hash(BASE/name)==pin,'Frozen causal method differs: '+name)
            receive_environment(root,folder)
            if folder.startswith('attempt'):
                for identity in analyze.IDS:
                    base=root/folder/'cases'/identity;plan=read(base/'plan.json')
                    for name in ('source.dxf','candidate.dxf','plan.json'):
                        require(analyze.sha(base/name)==previous['cases/'+identity+'/'+name],'Prior public input differs')
                    require(verify(base/'source.dxf',base/'candidate.dxf',plan)['unplanned_byte_changes']==0,'Exact candidate byte failure')
                actual=analyze.analyze(root/folder);equal_report(actual,read(root/'reports'/('analysis-'+folder[-1]+'.json')));analyses.append(actual)
                if folder=='attempt-3':
                    jobs=read(root/folder/'export.json')['jobs']
                    for phase,wanted in (('export',[p for j in jobs for p in (j['input'],j['output'])]),('fresh',[j['output']for j in jobs])):
                        documents=[json.loads(s.split(' ',1)[1])for s in(root/folder/'native'/(phase+'.stdout')).read_text(encoding='utf-8').splitlines()
                            if s.startswith('ICT_ROOT12_DOCUMENT ')]
                        require([d['path']for d in documents]==wanted and all(len(d['initial'])==60 for d in documents),
                            'Before-load document observations omitted/different')
            else:
                receive_pixels(root,folder)
                if folder!='pixels-1':
                    pixels[folder]=pixel_analysis.analyze(root,folder);equal_report(pixels[folder],read(root/'reports'/(folder+'-analysis.json')))
        pins=read(root/'reference/PINS.json');old_inventory=read(HERE/'font-views-9/INVENTORY.json')['files']
        require(set(pins)=={'106.json','106.png','107.png'},'GUI reference omitted')
        for name,pin in pins.items():
            require({k:v for k,v in pin.items()if k!='member'}==old_inventory[pin['member']] and
                analyze.sha(root/'reference'/name)==pin['sha256'],'Original GUI reference differs')
        diagnosis=diagnose.diagnose(root/'attempt-1',root/'attempt-2');rows=diagnosis.pop('first_attempt_full_save')
        equal_report(diagnosis,read(root/'reports/residuals.json'))
        require({p.name for p in(root/'reports').glob('full-save-*.json')}=={f'full-save-{i:02}.json'for i in range(24)},'Full-save diagnosis omitted')
        for index,row in enumerate(rows):equal_report(row,read(root/'reports'/f'full-save-{index:02}.json'))
        result=summary(root,analyses,pixels);equal_report(result,read(BASE/'SUMMARY.json'))
    return result

if __name__=='__main__':print(json.dumps(check(),indent=2))
