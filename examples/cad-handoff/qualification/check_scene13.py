"""Receive the retained actual-GUI paint diagnosis offline. Does not re-run native Qt or CAD."""
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
BASE=HERE/'gui-scene-13'
sys.path[:0]=[str(BASE),str(HERE)]
import check_linux7
from verify_bytes import verify
import scene_analysis as s

IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
CONFIG='2c23f1511046e1ce876753efa354185a733d88e1264713ee13cc72d735f73a6c'
def receive(root):
    historical=s.read(HERE/'root-cause-12/INVENTORY.json')['files']
    font=s.read(HERE/'font-views-9/INVENTORY.json')['files']
    for seq in (106,107):
        for ext in ('png','json'):
            name=f'reference/{seq}.{ext}'
            pin=historical['raw/'+name]if ext=='png'else font[f'raw/default-replay-2/receipts/{seq}.json']
            s.require(s.sha((root/name).read_bytes())==pin['sha256'],'Historical reference changed')
    for folder in ('ordinary','observed','observed-2','observed-3','observed-4'):
        w=root/folder;env=s.read(w/'ENVIRONMENT.json');state=env['state'];frozen=s.read(w/'FREEZE.json')
        s.require(env['image']==IMAGE and env['user']=='1001:1001' and env['network']=='none','Native receiver identity differs')
        s.require(state['Status']=='exited' and state['Running']is False and not state['OOMKilled'],'Native process is not terminal')
        s.require(state['ExitCode']==(127 if folder in('observed','observed-2')else 0),'Terminal exit changed')
        s.require(env['entrypoint']==['dbus-run-session']and env['args']==['--','/bin/sh','/work/desktop.sh'],'Native entrypoint changed')
        s.require(frozen['files']['.configuration/QCAD3.conf']['sha256']==CONFIG,'Wrong selected settings input')
        s.require((w/'selected-config-initial.sha256').read_text().split()[0]==CONFIG,'Selected config initial hash differs')
        for name in ('desktop.sh','native_views.js','capture.py','requests.json','validation-long-source.dxf','validation-long-candidate.dxf'):
            s.require(s.sha((w/name).read_bytes())==frozen['files'][name]['sha256'],'Frozen GUI input/method changed: '+name)
        s.require(s.read(w/'COMPLETE.json')==dict(inputs_unchanged=True,gui_captures=0 if folder in('observed','observed-2')else 2,actual_ui_edit_or_save=False),'Read-only capture coverage differs')
        plan=s.read(HERE/'validation-2/authored/validation-long.plan.json')
        verify(w/'validation-long-source.dxf',w/'validation-long-candidate.dxf',plan)
        log=s.read(w/'native-log.json');text=log['stdout']+log['stderr']
        if folder=='observed':s.require('libQt5Gui.so.5: cannot open shared object file'in text,'Original launcher failure omitted')
        elif folder=='observed-2':s.require('undefined symbol: _ZN10QJsonArrayC1ESt16initializer_listI10QJsonValueE'in text,'Original ABI failure omitted')
        else:
            s.require('ICT_SCENE13_PROFILE {"configuration_file":"/home/cad/.config/QCAD/QCAD3.conf"}'in text,'Actual settings selection missing')
            s.require(not(w/'failure.json').exists(),'Native view failure recorded')
    s.require(s.read(root/'old-config-recovery.json')['exit']!=0,'Historical missing-profile limit changed')
    hashes={line.split()[1]:line.split()[0]for line in(root/'build/hashes.txt').read_text().splitlines()}
    s.require(hashes['paint_trace.cpp']==s.sha((root/'methods/observer-4.cpp').read_bytes()),'Built observer source differs')
    s.require(hashes['paint_trace.so']==s.read(root/'observed-4/FREEZE.json')['files']['paint_trace.so']['sha256'],'GUI helper binary hash differs')
    for name in ('control','control4','replay','replay2','replay4','ablations'):
        env=s.read(root/'build'/f'{name}-identity.json');log=s.read(root/'build'/f'{name}-command.json')
        s.require(env['image']==IMAGE and env['state']['ExitCode']==0 and not env['state']['Running'],'Native replay/control identity differs')
        s.require(log['exit']==0 and 'Qt runtime 5.14.2'in log['stdout'],'Native replay/control runtime observation differs')
    return s.analyze(root)

def check():
    check_linux7.recheck.method_bindings()
    s.require(s.sha((BASE/'package.py').read_bytes())==s.read(BASE/'INVENTORY.json')['packager_sha256'],'Packager differs')
    with tempfile.TemporaryDirectory(prefix='ict-gui-paint-receive-')as temporary:
        root=check_linux7.unpack(BASE,Path(temporary));s.reassemble(root);result=receive(root)
    s.require(result==s.read(BASE/'SUMMARY.json'),'Retained GUI diagnosis differs from re-score')
    return result

if __name__=='__main__':print(json.dumps(check(),indent=2))
