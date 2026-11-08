"""Run one frozen read-only native probe and serial matched paper renders; retain every command/log."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
from datetime import datetime,timezone

ROOT=Path('/work')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def main():
    manifest=json.loads((ROOT/'MANIFEST.json').read_bytes())
    out=ROOT/'native'
    out.mkdir(exist_ok=False)
    supplied=ROOT/'.local-configuration/QCAD3.conf'
    expected='5d2fe06c831c2c8032d446d51801a73f754cd120a2c0b415e051483c81b14550'
    if digest(supplied)!=expected:raise ValueError('Local configuration identity mismatch; no CAD starts')
    installed=Path('/home/cad/.config/QCAD/QCAD3.conf')
    installed.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(supplied,installed)
    if digest(installed)!=expected:raise ValueError('Installed configuration mismatch; no CAD starts')
    write(out/'configuration-before.json',dict(source_sha256=digest(supplied),installed_sha256=digest(installed),
          verified_before_native_start=True,contents='Local only; excluded from published evidence'))
    rows=[]
    base=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
          '-config','/work/qcad-config','-font-substitution','Standard','DejaVu Sans']
    def run(name,command):
        entry=dict(id=name,command=command,started=datetime.now(timezone.utc).isoformat())
        rows.append(entry);write(out/'commands.json',rows)
        print('START',name,flush=True)
        with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
            child=subprocess.Popen(command,cwd='/opt/qcad',stdout=stdout,stderr=stderr)
            entry['pid']=child.pid;write(out/'commands.json',rows)
            # No timeout/restart. The host retains the running container/process handle.
            entry['exit']=child.wait()
        entry['finished']=datetime.now(timezone.utc).isoformat();write(out/'commands.json',rows)
        if entry['exit']:raise RuntimeError('Native command failed: '+name)
        print('END',name,entry['exit'],flush=True)
    pins={j['path']:digest(ROOT/j['path']) for j in manifest['jobs']}
    if pins!={j['path']:j['sha256'] for j in manifest['jobs']}:raise ValueError('Input pin mismatch')
    write(out/'before.json',pins)
    run('probe',base+['-autostart','/work/native_probe.js','-m','/work/MANIFEST.json'])
    probe=json.loads((ROOT/'native-probe.json').read_bytes())
    if [r['id'] for r in probe['rows']]!=[j['id'] for j in manifest['jobs']] or any(r.get('error') for r in probe['rows']):
        raise ValueError('Native probe incomplete/error; retain and stop')
    for job in manifest['jobs']:
        output=out/(job['id']+'.png')
        command=base+['-autostart','scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js','-o',str(output),
                      '-x','2400','-y','1600','-window='+','.join(str(x) for x in job['window']),
                      '-block='+job['layout'],'-b','white','-n',str(ROOT/job['path'])]
        run(job['id'],command)
        rows[-1]['image_sha256']=digest(output);write(out/'commands.json',rows)
    after={j['path']:digest(ROOT/j['path']) for j in manifest['jobs']}
    write(out/'after.json',after)
    if after!=pins:raise ValueError('Native reader/renderer changed drawing inputs')
    write(out/'COMPLETE.json',dict(commands=len(rows),paper_images=len(manifest['jobs']),
         input_unchanged=True,role='Read-only native/API rendering development; no new UI edit or CAD qualification'))


if __name__=='__main__':main()
