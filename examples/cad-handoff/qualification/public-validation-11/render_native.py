"""Execute the predeclared serial matched views; no pixel edits or restart on timeout."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/work')
CONFIG=Path('/home/cad/.config/QCAD/QCAD3.conf')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def main():
    manifest=json.loads((ROOT/'RENDERS.json').read_bytes())
    out=ROOT/'renders';out.mkdir(exist_ok=False)
    supplied=ROOT/'.render-configuration/QCAD3.conf'
    if sha(supplied)!=manifest['configuration_sha256']:raise ValueError('Render profile differs')
    CONFIG.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(supplied,CONFIG)
    records=[]
    for job in manifest['jobs']:
        source=ROOT/job['path']
        if sha(source)!=job['sha256']:raise ValueError('Render input differs')
        command=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
                 '-config',str(CONFIG),'-font-substitution','Standard','DejaVu Sans',
                 '-autostart','scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js','-o',str(out/(job['id']+'.png')),
                 '-x','2400','-y','1600','-window='+','.join(str(x) for x in job['window']),
                 '-b','white','-n',str(source)]
        row=dict(id=job['id'],command=command,started=datetime.now(timezone.utc).isoformat(),
                 configuration_sha256_before=sha(CONFIG));records.append(row);write(out/'commands.json',records)
        print('START',job['id'],flush=True)
        with (out/(job['id']+'.stdout')).open('wb') as stdout,(out/(job['id']+'.stderr')).open('wb') as stderr:
            child=subprocess.Popen(command,cwd='/opt/qcad',stdout=stdout,stderr=stderr)
            row['pid']=child.pid;write(out/'commands.json',records);row['exit']=child.wait()
        row.update(finished=datetime.now(timezone.utc).isoformat(),configuration_sha256_after=sha(CONFIG))
        write(out/'commands.json',records)
        if row['exit']:raise ValueError('Native render failed; retain and stop')
        if ('absConfigFile: "'+str(CONFIG)+'"').encode() not in (out/(job['id']+'.stderr')).read_bytes():
            raise ValueError('Selected render configuration not evidenced')
        row['image_sha256']=sha(out/(job['id']+'.png'));write(out/'commands.json',records)
        if sha(source)!=job['sha256']:raise ValueError('Native renderer changed input')
        print('END',job['id'],flush=True)
    write(out/'COMPLETE.json',dict(images=len(records),whole_cad_qualified=False,
          scope='Native API-rendered views; inspect every image; not actual UI edit/save acceptance'))


if __name__=='__main__':main()
