"""Retain an unexecuted draft before fixing a native helper's name collision."""
from pathlib import Path
import json
import hashlib
import shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15/attempt-1')
assert not(ROOT/'native').exists()
backup=ROOT/'pre-execution-draft';backup.mkdir(exist_ok=False)
for name in('FREEZE.json','native_records.js'):shutil.copyfile(ROOT/name,backup/name)
shutil.copyfile(HERE/'native_records.js',ROOT/'native_records.js')
freeze=json.loads((ROOT/'FREEZE.json').read_bytes())
freeze['inputs']['native_records.js']=hashlib.sha256((ROOT/'native_records.js').read_bytes()).hexdigest()
data=(json.dumps(freeze,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
(ROOT/'FREEZE.json').write_bytes(data);(HERE/'FREEZE.json').write_bytes(data)
note=dict(reason='Pre-execution source review found function selected shadowed by the settings filename variable; renamed function chooseFilter before any native execution.',
    original_probe_sha256=hashlib.sha256((backup/'native_records.js').read_bytes()).hexdigest(),corrected_probe_sha256=freeze['inputs']['native_records.js'],native_executions_before_correction=0)
(ROOT/'PRE-EXECUTION-CORRECTION.json').write_text(json.dumps(note,indent=2)+'\n',encoding='utf-8')
print('Retained draft; corrected probe frozen before execution')
