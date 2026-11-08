"""Retain terminal native/container identities and failure logs without settings contents."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('C:/Users/Steve/.cp-scratch/cad-gui-scene-13')
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def command(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    return dict(command=cmd,exit=r.returncode,stdout=r.stdout,stderr=r.stderr)
for folder,name in [('ordinary','ordinary'),('observed','observed'),('observed-2','observed2'),('observed-3','observed3'),('observed-4','observed4')]:
    w=ROOT/folder;identity=json.loads(command(['docker','inspect','ict-cad-scene13-'+name])['stdout'])[0]
    state=identity['State'];assert state['Status']=='exited' and not state['Running']
    write(w/'ENVIRONMENT.json',dict(image=identity['Image'],image_argument=identity['Config']['Image'],
        user=identity['Config']['User'],network=identity['HostConfig']['NetworkMode'],state=state,
        entrypoint=identity['Config']['Entrypoint'],args=identity['Config']['Cmd'],
        mounts=[dict(Type=m['Type'],Destination=m['Destination'],RW=m['RW'])for m in identity['Mounts']]))
    write(w/'native-log.json',command(['docker','logs','ict-cad-scene13-'+name]))
    config=w/'.configuration/QCAD3.conf';write(w/'configuration-terminal.json',dict(sha256=hashlib.sha256(config.read_bytes()).hexdigest(),bytes=config.stat().st_size))
    for role in ('source','candidate'):
        p=w/f'validation-long-{role}.dxf';pin=json.loads((w/'FREEZE.json').read_text())['files'][p.name]
        assert hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256'],'Read-only GUI changed drawing'
    write(w/'COMPLETE.json',dict(inputs_unchanged=True,gui_captures=2 if (w/'views/107.png').exists() else 0,
        actual_ui_edit_or_save=False))
for name in ('compile','compile2','compile3','compile4','control-compile','control-compile2','replay-compile','replay-compile2','replay-compile3','control','control4','replay','replay2','replay4','ablations'):
    write(ROOT/'build'/(name+'-command.json'),command(['docker','logs','ict-cad-scene13-'+name]))
    inspected=json.loads(command(['docker','inspect','ict-cad-scene13-'+name])['stdout'])[0]
    assert not inspected['State']['Running']
    write(ROOT/'build'/(name+'-identity.json'),dict(image=inspected['Image'],state=inspected['State'],
        entrypoint=inspected['Config']['Entrypoint'],args=inspected['Config']['Cmd']))
write(ROOT/'old-config-recovery.json',command(['docker','cp','ict-cad-font-9-default2:/work/qcad-config',str(ROOT/'old-actual-settings')]))
print('Terminal identities, original failures and unchanged input hashes retained')
