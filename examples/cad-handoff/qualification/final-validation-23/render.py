"""Serial reserved model/paper observations using the existing native bitmap exporter."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from window import xywh

ROOT = Path('/work')
CONFIG = Path('/home/cad/.config/QCAD/QCAD3.conf')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_bytes())
    out = ROOT / 'native'
    out.mkdir(exist_ok=False)
    supplied = ROOT / '.configuration/QCAD3.conf'
    if sha(supplied) != manifest['configuration_sha256']:
        raise ValueError('Paper configuration differs; no native process starts')
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(supplied, CONFIG)
    if sha(CONFIG) != manifest['configuration_sha256']:
        raise ValueError('Installed paper configuration differs')
    before = {job['path']: sha(ROOT / job['path']) for job in manifest['jobs']}
    if before != {job['path']: job['sha256'] for job in manifest['jobs']}:
        raise ValueError('Paper input differs; no native process starts')
    write(out / 'BEFORE.json', before)
    records = []
    for job in manifest['jobs']:
        image = out / (job['id'] + '.png')
        command = ['/opt/qcad/qcad', '-platform', 'offscreen', '-no-gui',
                   '-allow-multiple-instances', '-config', str(CONFIG),
                   '-font-substitution', 'Standard', 'DejaVu Sans', '-autostart',
                   'scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js', '-o', str(image),
                   '-x', '2400', '-y', '1600',
                   '-window=' + ','.join(str(v) for v in xywh(job['window'])),
                   *(['-block=' + job['layout']] if job['layout'] != 'Model' else []), '-b', 'white', '-n',
                   str(ROOT / job['path'])]
        row = dict(id=job['id'], command=command,
                   started=datetime.now(timezone.utc).isoformat(),
                   configuration_sha256_before=sha(CONFIG))
        records.append(row)
        write(out / 'commands.json', records)
        print('START', job['id'], flush=True)
        with (out / (job['id'] + '.stdout')).open('wb') as stdout, \
                (out / (job['id'] + '.stderr')).open('wb') as stderr:
            child = subprocess.Popen(command, cwd='/opt/qcad', stdout=stdout, stderr=stderr)
            row['pid'] = child.pid
            write(out / 'commands.json', records)
            row['exit'] = child.wait()
        row.update(finished=datetime.now(timezone.utc).isoformat(),
                   configuration_sha256_after=sha(CONFIG))
        write(out / 'commands.json', records)
        if row['exit']:
            raise ValueError('Native paper process failed; preserve original attempt')
        if ('absConfigFile: "' + str(CONFIG) + '"').encode() not in (out / (job['id'] + '.stderr')).read_bytes():
            raise ValueError('Selected paper configuration not evidenced')
        row['image_sha256'] = sha(image)
        write(out / 'commands.json', records)
        if sha(ROOT / job['path']) != job['sha256']:
            raise ValueError('Native paper reader changed source')
        print('END', job['id'], flush=True)
    after = {job['path']: sha(ROOT / job['path']) for job in manifest['jobs']}
    write(out / 'AFTER.json', after)
    if before != after:
        raise ValueError('Paper source changed')
    write(out / 'COMPLETE.json', dict(images=len(records), input_unchanged=True,
          whole_cad_qualified=False, visual_inspection='separate gate',
          scope='Native paper rendering only; no drawing repair or save'))


if __name__ == '__main__':
    main()
