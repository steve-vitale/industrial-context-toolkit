"""Recheck the retained first bridge failure, including both separate cleanup outcomes."""
import json
from pathlib import Path
import tempfile

from bridge_receive import audit_history
from native_io import FOLDERS
from recheck_evidence import unpack, require, digest, HERE, IMAGE


def check_files(files):
    def read(name): return json.loads(files['attempt/' + name])
    manifest = json.loads((HERE / 'BRIDGE-METHODS-1.json').read_bytes())
    freeze = read('job/JOB-FREEZE.json')
    require(freeze['stage_sha256'] == manifest['producers']['stage.py'], 'Original staging method differs')
    for name, pin in freeze['files'].items():
        require(digest(files['attempt/job/' + name]) == pin, 'Frozen original differs: ' + name)
    for name, pin in manifest['staged_methods'].items():
        require(freeze['files'][name] == pin, 'Original prospective method differs: ' + name)
    inner = read('INVENTORY.json')
    actual = {n.removeprefix('attempt/'): dict(bytes=len(v), sha256=digest(v)) for n, v in files.items()
              if n != 'attempt/INVENTORY.json'}
    require(inner['files'] == actual and inner['whole_cad_qualified'] is False, 'Complete inner inventory differs')
    process = read('job/native/PROCESS.json'); handle = read('host/HANDLE.json')
    terminal = json.loads(read('inspection/terminal.json')['stdout'])[0]
    require(handle['image'] == IMAGE and terminal['Id'] == handle['id'] and terminal['State'] == inner['native_container_state'], 'Actual native handle/terminal differs')
    require(terminal['State']['Status'] == 'exited' and terminal['State']['ExitCode'] == 1 and
            process['controller_exit'] == 1 and process['exit'] == 0 and read('host-run/EXIT.json')['exit'] == 1, 'Original failed exits lost')
    require(process['configuration_before'] == freeze['files']['.configuration/QCAD3.conf'], 'Original configuration differs')
    actions = read('job/ui/actions.json')
    require([r['event'] for r in actions] == list(range(1, len(actions) + 1)), 'Original action history differs')
    require('Native command failed' in read('job/ui/FAILURE.json')['traceback'] and
            any(r['kind'] == 'command' and r.get('exit') == 1 and
                'Typed native field text differs; do not commit' in r.get('stderr', '') for r in actions), 'Original typing refusal lost')
    require(not any(r['kind'] in ('returned_file', 'native_fields', 'absolute_frame') for r in actions), 'Failed attempt promoted to CAD open/save')
    first = read('inspection/CANCEL-AND-CLEANUP.json')
    require(first['exit'] == 1 and 'Observation timeout, native not restarted: Separate cancellation completed' in first['stderr'], 'First Cancel timeout lost')
    second = read('inspection/STOP-CANCEL-CLEANUP.json')
    require(second['exit'] == 0 and second['source_sha256'] == digest(files['attempt/inspection/sources/stop_cancel_cleanup.py']), 'Separate stop/cancel cleanup differs')
    for name, receipt in [('cancel_failed_open.py', first), ('stop_cancel_cleanup.py', second)]:
        require(receipt['command'][:4] == ['docker', 'exec', handle['name'], 'python3'] and
                receipt['command'][-1].encode('utf-8') == files['attempt/inspection/sources/' + name], 'Actual cleanup command/source differs')
    cleanup = read('job/stop-before-cancel-cleanup/actions.json')
    require(cleanup[0]['kind'] == 'stop_marker' and cleanup[-1]['kind'] == 'normal_cleanup_complete' and
            cleanup[-1]['native_pid'] == process['engine_pid'] and
            cleanup[-1]['native_start_identity'] == process['engine_start_identity'] and
            cleanup[-1]['live_helpers_before_close'] == [], 'Same-process stopped cleanup missing')
    console = files['attempt/job/native/stdout.txt'].decode('utf-8')
    require('ICT_MAILBOX_FATAL ' not in console and 'Script Exception:' not in console, 'Unexpected helper/native failure')
    with tempfile.TemporaryDirectory(prefix='ict-bridge-failed-') as tmp:
        root = Path(tmp)
        for name in FOLDERS:
            (root / name).mkdir(); (root / 'staging' / name).mkdir(parents=True, exist_ok=True)
        for name, value in files.items():
            if name.startswith('attempt/mailbox/'):
                path = root / name.removeprefix('attempt/mailbox/'); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        history = audit_history(root, console, read('job/transport.json'), process['engine_pid'])
    require(history['calls'] == 1645 and history['replies'] == 2 and not history['sealed'] and not history['failures'] and
            history['stopped'] == [dict(run_id=read('job/transport.json')['run_id'], call_id=1645)], 'Complete failed bridge history differs')
    for seq in (1, 2):
        request = read(f'mailbox/requests/{seq:08d}.json')
        require(request['body'] == dict(action='status'), 'Unexpected CAD observation before failure')
    return dict(status='original-bridge-and-first-cleanup-failures-retained', helper_calls=history['calls'],
                replies=history['replies'], separate_stopped_cleanup='native0-controller1-container1', whole_cad_qualified=False)


def check(): return check_files(unpack(HERE / 'bridge-development-1'))


if __name__ == '__main__': print(json.dumps(check(), indent=2))
