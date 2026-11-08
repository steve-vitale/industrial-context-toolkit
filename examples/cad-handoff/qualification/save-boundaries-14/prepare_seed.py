"""Freeze two independent fixed-seed repeats of the same exposed source/default-format jobs."""
import json
from pathlib import Path
import shutil
from prepare import IDS,sha,write

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')
for label in ('seed-0-a','seed-0-b'):
    work=ROOT/label;work.mkdir(exist_ok=False);jobs=[]
    for identity in IDS:
        folder=work/'cases'/identity;(folder/'returns').mkdir(parents=True)
        for name in ('source.dxf','candidate.dxf','plan.json'):
            shutil.copyfile(ROOT/'attempt-1/cases'/identity/name,folder/name)
        jobs.append(dict(id=identity+'/default',input='/work/cases/'+identity+'/source.dxf',
            output='/work/cases/'+identity+'/returns/default.dxf',format=''))
    write(work/'export.json',dict(jobs=jobs));write(work/'fresh.json',dict(jobs=jobs,read_only=True))
    shutil.copyfile(HERE/'native_boundaries.js',work/'native_boundaries.js')
    controller=(HERE/'run_native.py').read_text(encoding='utf-8').replace('import hashlib','import hashlib\nimport os')
    controller=controller.replace('commands.append(row);',"row['qt_hash_seed']=os.environ.get('QT_HASH_SEED');commands.append(row);")
    (work/'run_native.py').write_text(controller,encoding='utf-8',newline='\n')
    (work/'.configuration').mkdir();config=ROOT/'attempt-1/.configuration/QCAD3.conf';shutil.copyfile(config,work/'.configuration/QCAD3.conf')
    inputs={p.relative_to(work).as_posix():sha(p)for p in work.rglob('*')if p.is_file() and '.configuration'not in p.parts}
    write(work/'FREEZE.json',dict(inputs=inputs,configuration_sha256=sha(config),qt_hash_seed='0',exposure='Six exposed sources; independent diagnostic process repeat'))
    shutil.copyfile(work/'FREEZE.json',HERE/(label.upper()+'-FREEZE.json'))
print('Frozen two independent fixed-seed source/default-format repeats')
