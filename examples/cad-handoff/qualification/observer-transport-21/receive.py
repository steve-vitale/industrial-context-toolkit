"""Receive actual native development evidence; failed controls stay failed attempts."""
import argparse
import hashlib
import json
from pathlib import Path

from mailbox import audit, PROTOCOL

HERE = Path(__file__).resolve().parent


def read(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)


def receive(root, basis_path, methods_path):
    root = Path(root); job = root / 'job'; mailbox = root / 'mailbox'
    inventory = read(root / 'INVENTORY.json')
    actual = {p.relative_to(root).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
              for p in root.rglob('*') if p.is_file() and p != root / 'INVENTORY.json'}
    require(actual == inventory['files'], 'Complete packet inventory differs')
    methods = read(methods_path)
    frozen = read(job / 'JOB-FREEZE.json')
    for name, pin in frozen['files'].items():
        require(sha(job / name) == pin, 'Frozen job input changed: ' + name)
    for name, allowed in methods['staged_methods'].items():
        require(frozen['files'][name] in allowed, 'Method is not in independently retained freeze: ' + name)
    basis = read(basis_path); basis['role'] = 'receiving'
    require(read(job / 'job.json') == basis, 'Declared case basis differs')
    require(sha(job / 'source.dxf') == basis['source_sha256'], 'Source differs from original case basis')
    config = read(job / 'transport.json'); profile = config['profile']
    require(profile == inventory['profile'] and config['protocol'] == PROTOCOL, 'Run/profile binding differs')
    process = read(job / 'native/PROCESS.json')
    require(process.get('exit') == 0, 'Native process did not complete normal exit')
    require(process['configuration_before'] == frozen['files']['.configuration/QCAD3.conf'], 'Native configuration differs')
    require(isinstance(process.get('engine_pid'), int) and process['engine_pid'] != process['pid'], 'Actual Qt child identity missing')
    handle = read(root / 'host/HANDLE.json')
    require(handle['image'] == methods['image'], 'Native image differs')
    commands = [read(p) for p in sorted((root / 'host').glob('0*.json'))]
    launches = [c for c in commands if c['command'][:3] == ['docker', 'run', '-d']]
    require(len(launches) == 1 and launches[0]['exit'] == 0, 'Native launch history differs')
    launch = launches[0]['command']
    for option, expected in [('--network', 'none'), ('--user', '1001:1001'), ('--cap-drop', 'ALL'), ('--security-opt', 'no-new-privileges')]:
        require(launch[launch.index(option) + 1] == expected, 'Native isolation differs: ' + option)
    require('--rm' not in launch, 'Native container must be retained')
    inspections = [json.loads(c['stdout'])[0] for c in commands if c['command'][:2] == ['docker', 'inspect'] and c['exit'] == 0]
    require(bool(inspections), 'Actual container inspections missing')
    final = inspections[-1]
    require(final['Id'] == handle['id'] and final['State']['Status'] == 'exited', 'Actual same-container terminal evidence missing')
    require(final['State'] == inventory['native_container_state'], 'Final terminal state differs')
    actions = read(job / 'ui/actions.json')
    require([r['event'] for r in actions] == list(range(1, len(actions) + 1)), 'Action history is incomplete')
    requests = [r for r in actions if r['kind'] == 'mailbox_request']
    consoles = [(job / 'native' / n).read_text(encoding='utf-8', errors='replace') for n in ('stdout.txt', 'stderr.txt')]
    console = '\n'.join(consoles)
    fatal = 'ICT_MAILBOX_FATAL ' in console
    if profile == 'normal':
        require(process.get('controller_exit') == 0 and final['State']['ExitCode'] == 0, 'Normal controller/container failed')
        require(not fatal and 'Script Exception:' not in console, 'Native console retains observer failure')
        require(not (job / 'ui/FAILURE.json').exists() and (job / 'ui/RESULT.json').is_file(), 'Normal result missing or failed')
        require([r['seq'] for r in requests] == list(range(1, len(requests) + 1)), 'Request action sequence differs')
        bodies = []
        for r in requests:
            data = (mailbox / 'requests' / f"{r['seq']:08d}.json").read_bytes()
            require(data.decode('ascii') == r['wire'] and hashlib.sha256(data).hexdigest() == r['sha256'], 'Client request wire differs')
            bodies.append(json.loads(data)['body'])
        receipt = audit(mailbox, config['run_id'], bodies)
        replies = [r for r in actions if r['kind'] == 'mailbox_reply']
        require([r['seq'] for r in replies] == list(range(1, len(requests) + 1)), 'Client reply history differs')
        for seq, row in enumerate(replies, 1):
            path = mailbox / 'replies' / f'{seq:08d}.json'
            require(read(path) == row['reply'] and sha(path) == row['sha256'], 'Client reply bytes differ')
        fields = [r for r in actions if r['kind'] == 'native_fields']
        require(len(fields) == 1 and fields[0]['expected'] == basis['attributes'], 'Native field verification missing')
        observed = fields[0]['observed']
        require(set(observed) == set(basis['attributes']), 'Native UI field set differs')
        for tag, value in basis['attributes'].items():
            require(observed[tag]['text'] == value and observed[tag]['enabled'] and observed[tag]['editable'], 'Native field/value/editability differs')
        frames = [r for r in actions if r['kind'] == 'absolute_frame']
        require([r['frame'] for r in frames] == list(basis['frames']), 'Native frame coverage differs')
        for row in frames:
            out = row['observation']; wanted = out['camera_control']; view = out['view']
            require(out['request']['frame'] == basis['frames'][row['frame']], 'Native frame basis differs')
            require(wanted['factor'] == view['factor'] and wanted['offset'] == view['offset'], 'Exact absolute camera differs')
        for out in receipt['observations']:
            require(out['qt'] == '5.14.2' and out['configuration_file'] == '/home/cad/.config/QCAD/QCAD3.conf', 'Native observation environment differs')
            if out['filename'] == '/work/source.dxf':
                require({a['tag']: a['text'] for a in out['attributes']} == basis['attributes'], 'Native source attributes differ')
        return dict(status='normal-development-received', case=basis['case'], profile=profile,
                    requests=len(requests), fields=len(fields), frames=len(frames), whole_cad_qualified=False)

    require(process.get('controller_exit') != 0 and final['State']['ExitCode'] != 0, 'Deliberate fault lost original failure exit')
    require((job / 'ui/FAILURE.json').is_file(), 'Original fault receipt missing')
    errors = [read(p) for p in sorted((mailbox / 'errors').glob('*.json'))]
    native_profiles = {'malformed', 'wrong-sequence', 'wrong-run', 'unsupported', 'read-open', 'reply-collision', 'reply-write', 'error-write'}
    if profile in native_profiles:
        require(fatal and 'Script Exception:' not in console, 'Detailed native error/fallback missing or itself failed')
        if profile == 'error-write':
            require(not errors and 'ICT_MAILBOX_ERROR_PUBLICATION ' in console, 'Error publication fault/fallback not retained')
        else:
            require(len(errors) == 1, 'Native error history missing/extra')
            row = errors[0]
            require(row['run_id'] == config['run_id'] and row['error_id'] == 1 and row['protocol'] == PROTOCOL, 'Native error binding differs')
            require('diagnostic_failure' not in row['file'], 'Native error facts themselves failed')
            if profile in ('read-open', 'reply-write'):
                require(row['file']['code'] != 0 and isinstance(row['file']['code'], int) and bool(row['file']['message']), 'Actual QFile code/message missing')
                require(row['stage'] == ('read-open' if profile == 'read-open' else 'write-open'), 'Fault did not reach intended native operation')
    require(any(r['kind'] == 'mailbox_failure' for r in actions), 'Client did not retain a transport refusal')
    if profile != 'native-exit': require((job / 'native/CLEANUP.json').is_file(), 'Separate same-process cleanup receipt missing')
    return dict(status='failed-attempt-retained', case=basis['case'], profile=profile, native_error_records=len(errors),
                console_fatal=fatal, whole_cad_qualified=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('packet', type=Path); p.add_argument('basis', type=Path)
    p.add_argument('--methods', type=Path, default=HERE / 'METHODS.json'); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists(): p.exit(1, 'New receipt destination required\n')
    try: result = receive(a.packet, a.basis, a.methods)
    except Exception as error: p.exit(1, str(error) + '\n')
    a.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8'); print(json.dumps(result))
