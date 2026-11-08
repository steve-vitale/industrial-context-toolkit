"""Retain failed payload-2, copy exact data into a separately frozen complete-probe successor."""
from pathlib import Path
import shutil
from prepare import sha,write
import json

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')
old=ROOT/'payload-2';new=ROOT/'payload-3'
probe=HERE/'native_payload_observed.js'
assert 'm.jobs.length'in probe.read_text(encoding='utf-8') and 'known:{USERI5:'in probe.read_text(encoding='utf-8')
shutil.copytree(old,new,ignore=shutil.ignore_patterns('native','FREEZE.json'))
shutil.copyfile(probe,new/'native_payload.js')
previous=json.loads((old/'FREEZE.json').read_bytes())
for name,pin in previous['inputs'].items():
    if name!='native_payload.js':assert sha(new/name)==pin
inputs={p.relative_to(new).as_posix():sha(p)for p in new.rglob('*')if p.is_file()and'.configuration'not in p.parts}
write(new/'FREEZE.json',dict(inputs=inputs,configuration_sha256=previous['configuration_sha256'],
    exposure=previous['exposure'],successor_of='payload-2 incomplete native probe; data unchanged'))
shutil.copyfile(new/'FREEZE.json',HERE/'PAYLOAD-COMPLETE-FREEZE.json')
print('Exact payload data copied; complete successor probe frozen separately')
