"""Recheck all four retained failed/probe attempts offline; no native launch or qualification."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'


def require(ok, message):
    if not ok: raise ValueError(message)


def digest(data): return hashlib.sha256(data).hexdigest()


def unpack(packet):
    inventory = json.loads((packet / 'INVENTORY.json').read_bytes())
    blob = (packet / 'evidence.tar.xz').read_bytes()
    require(digest(blob) == inventory['archive_sha256'], 'Archive bytes differ')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:xz') as archive:
        total = 0
        for member in archive:
            name = PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and '..' not in name.parts and member.name not in files,
                    'Unsafe/duplicate archive member')
            total += member.size
            require(total <= 32 * 1024 * 1024, 'Archive exceeds scope')
            files[member.name] = archive.extractfile(member).read()
    actual = {n: dict(bytes=len(data), sha256=digest(data)) for n, data in files.items()}
    require(actual == inventory['files'], 'Archive inventory differs')
    return files


def check_files(files, frozen, kind):
    def read(name): return json.loads(files[name])
    job = 'attempt/job/'
    freeze = read(job + 'JOB-FREEZE.json')
    require(freeze['files'] == frozen['files'], 'Original input/method freeze differs')
    for name, pin in frozen['files'].items():
        require(digest(files[job + name]) == pin, 'Frozen method/input differs: ' + name)
    process = read(job + 'native/PROCESS.json')
    require(process['exit'] == 0 and process['configuration_before'] == freeze['files']['.configuration/QCAD3.conf'], 'Actual native exit/configuration differs')
    handle = read('attempt/host/HANDLE.json')
    require(handle['image'] == IMAGE, 'Pinned native image differs')
    inspections = []
    for name in files:
        if name.startswith(('attempt/host/', 'attempt/inspection/')) and name.endswith('.json'):
            row = read(name)
            if isinstance(row, dict) and row.get('command', [])[:2] == ['docker', 'inspect'] and row.get('exit') == 0:
                inspections.append(json.loads(row['stdout'])[0])
            # The first failed attempt also retains one raw inspection.
            if name.endswith('/TERMINAL.json') and isinstance(row, list): inspections.extend(row)
    terminal = [r for r in inspections if r['State']['Status'] == 'exited']
    require(terminal and all(r['Id'] == handle['id'] for r in terminal), 'Original same-container terminal evidence missing')
    actions = read(job + 'ui/actions.json')
    require([r['event'] for r in actions] == list(range(1, len(actions) + 1)), 'Action history differs')
    require(not any(r['kind'] == 'returned_file' or r.get('text') == '/work/source.dxf' for r in actions), 'Capability attempt unexpectedly opened/saved CAD')
    console = '\n'.join(files[job + 'native/' + n].decode('utf-8', errors='replace') for n in ('stdout.txt', 'stderr.txt'))
    if kind.startswith('development'):
        require(process['controller_exit'] == 1 and all(r['State']['ExitCode'] == 1 for r in terminal), 'Failed attempt exit was lost')
        require(job + 'ui/FAILURE.json' in files and job + 'native/CLEANUP.json' in files, 'Original failure or separate cleanup missing')
        require(read(job + 'native/CLEANUP.json')['close_exit'] == 0, 'Same-process normal cleanup failed')
        if kind == 'development-1':
            require('file21.size' in console and 'file21.error' in console and 'Script Exception:' in console, 'Original cascading binding failure missing')
        else:
            require("Can't find variable: QFileDevice" in console and 'ICT_MAILBOX_FATAL ' in console and
                    'ICT_MAILBOX_ERROR_PUBLICATION ' in console, 'Original complete fallback missing')
            require('Native console retains fatal transport error' in read(job + 'ui/FAILURE.json')['traceback'], 'Client did not refuse console failure')
        return dict(kind=kind, status='original-failed-attempt-retained', whole_cad_qualified=False)
    require(process['controller_exit'] == 0 and all(r['State']['ExitCode'] == 0 for r in terminal), 'Probe did not complete normally')
    report = read(job + 'native/BINDINGS.json')
    require(report == read(job + 'ui/RESULT.json')['report'], 'Native/client probe report differs')
    require(report['filename'] == '' and report['modified'] is False and report['qt'] == '5.14.2', 'Probe native state differs')
    checks = report['checks']
    require(checks['classes']['value']['QFileDevice'] == 'undefined' and checks['classes']['value']['NewOnly'] == 'undefined', 'Installed missing bindings differ')
    for method in ('size', 'error', 'errorString', 'flush'):
        require(checks['file_methods']['value'][method] == 'undefined', 'Missing inherited method differs')
    require(checks['new_only_first'] == dict(ok=True, value=True) and checks['new_only_collision'] == dict(ok=True, value=False), 'NewOnly collision result differs')
    require(files['attempt/mailbox/probe.bin'] == b'ORIGINAL CAPABILITY BYTES\n', 'Collision changed original bytes')
    require(checks['parent_error_string'] == dict(ok=True, value='File exists') and checks['parent_size'] == dict(ok=True, value=26), 'Observed parent API differs')
    if kind.endswith('-1'):
        require(checks['process_roundtrip']['ok'] is False and 'codecForName' in checks['process_roundtrip']['error'], 'Original codec refusal missing')
        status = 'probe-complete-with-retained-codec-refusal'
    else:
        require(checks['process_roundtrip'] == dict(ok=True, value=dict(exit=0, exit_status=0)), 'Actual process result differs')
        require(json.loads(checks['decode_stdout']['value']) == dict(uid=1001, value='µ valve') and checks['decode_stdout']['ok'], 'UTF-8 stdout differs')
        require(checks['decode_stderr'] == dict(ok=True, value='probe stderr\n'), 'UTF-8 stderr differs')
        status = 'probe-observed-process-and-utf8-stream-capabilities'
    return dict(kind=kind, status=status, whole_cad_qualified=False)


def check():
    freezes = json.loads((HERE / 'FROZEN-INPUTS.json').read_bytes())
    result = []
    for kind, frozen in freezes.items():
        packet = HERE / ('probes/' + kind if kind.startswith('binding') else kind)
        files = unpack(packet)
        row = check_files(files, frozen, kind)
        if kind.startswith('binding'):
            require(files['attempt/job/native/BINDINGS.json'] == (packet / 'BINDINGS.json').read_bytes(), 'Readable probe projection differs')
        result.append(row)
    return dict(attempts=result, whole_cad_qualified=False)


if __name__ == '__main__': print(json.dumps(check(), indent=2))
