"""Retain one isolated glyph raster process, including failure and exact font/config identities."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/work');CONFIG=Path('/home/cad/.config/QCAD/QCAD3.conf')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    freeze=json.loads((ROOT/'FREEZE.json').read_bytes())
    for name,pin in freeze['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Frozen pixel input differs')
    CONFIG.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'.configuration/QCAD3.conf',CONFIG)
    if sha(CONFIG)!=freeze['configuration_sha256']:raise ValueError('Settings differ')
    font=Path('/opt/qcad/fonts/Standard.cxf')
    if sha(font)!='6e482dd6c45bd3738d6e8cc3661d82193b6385eac613b2d15730bf91a303b18a':
        raise ValueError('Pinned Standard font differs')
    command=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances','-config',str(CONFIG),'-autostart','/work/native_pixels.js']
    out=ROOT/'native';out.mkdir(exist_ok=False)
    row=dict(command=command,configuration_sha256_before=sha(CONFIG),font_sha256=sha(font),font_bytes=font.stat().st_size,started=datetime.now(timezone.utc).isoformat())
    write(out/'command.json',row)
    with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
        child=subprocess.Popen(command,cwd='/opt/qcad',stdout=stdout,stderr=stderr);row['pid']=child.pid;write(out/'command.json',row);row['exit']=child.wait()
    row.update(configuration_sha256_after=sha(CONFIG),finished=datetime.now(timezone.utc).isoformat());write(out/'command.json',row)
    if row['exit']:raise ValueError('Native process failed')
    lines=(out/'stdout').read_text(encoding='utf-8').splitlines()
    if any(s.startswith('ICT_PIXEL12_FATAL ')for s in lines):raise ValueError('Native pixel probe failed; retain original attempt')
    rows=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_PIXEL12 ')]
    if len(rows)!=24:raise ValueError('Incomplete pixel probe')
    for name,pin in freeze['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Pixel probe changed input')
    write(out/'COMPLETE.json',dict(images=len(rows),inputs_unchanged=True))
if __name__=='__main__':main()
