"""Receive the complete native/helper history; faults stay failed, never CAD qualification."""
import argparse
import hashlib
import json
from pathlib import Path

from mailbox import wire, validate_reply
from native_io import FOLDERS, IO_PROTOCOL, parse

HERE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return parse(Path(path).read_bytes())


def records(console, marker):
    return [parse(line[len(marker):]) for line in console.splitlines() if line.startswith(marker)]


def audit_history(root, console, config, engine_pid):
    root = Path(root)
    require(set(p.name for p in root.iterdir()) == set(FOLDERS) | {'staging'}, 'Private mailbox directory inventory differs')
    require(set(p.name for p in (root / 'staging').iterdir()) == set(FOLDERS), 'Staging directory inventory differs')
    starts, ends = records(console, 'ICT_IO_START '), records(console, 'ICT_IO_END ')
    ids = list(range(1, len(starts) + 1))
    require(ids and [r['call_id'] for r in starts] == ids and [r['call_id'] for r in ends] == ids, 'Native start/end history incomplete')
    names = {f'{i:08d}.json' for i in ids}
    require({p.name for p in (root / 'events').iterdir()} == names and
            {p.name for p in (root / 'staging/events').iterdir()} == names, 'Missing/extra helper invocation events')
    previous = None; seen = {}; pending = None; failures = []; helper_pids = []
    for number, start, end in zip(ids, starts, ends):
        name = f'{number:08d}.json'; raw = (root / 'events' / name).read_bytes(); event = parse(raw)
        require((root / 'staging/events' / name).read_bytes() == raw, 'Event staging/published bytes differ')
        require(event['previous_event_sha256'] == previous, 'Invocation hash chain differs')
        previous = sha(raw)
        require(event['input_wire'] == start['input_wire'], 'Native/helper exact call argument differs')
        call = parse(event['input_wire']); result = event['result']; response = parse(end['stdout'])
        require(response.get('event_name') == name and response.get('event_sha256') == previous, 'Native response/event binding differs')
        native_result = {k: v for k, v in response.items() if k not in ('event_name', 'event_sha256')}
        require(wire(native_result) == wire(result), 'Native/helper result differs')
        require(result['io_protocol'] == IO_PROTOCOL and result['run_id'] == config['run_id'] and result['call_id'] == number,
                'Invocation result identity differs')
        require(result['uid'] == 1001 and result['qt_parent_pid'] == engine_pid, 'Helper owner/native parent differs')
        require(isinstance(result['owner_pid'], int), 'Helper PID missing'); helper_pids.append(result['owner_pid'])
        require(end['stderr'] == '' and end['exit_status'] == 0 and end['exit'] == (0 if result['ok'] else 1), 'Actual helper terminal result differs')
        require(call['call_id'] == number and call['io_protocol'] == IO_PROTOCOL and call['seq'] == len(seen) + 1 and call['seen'] == seen,
                'Native call sequence/seen binding differs')
        require(call['run_id'] == (None if number == 1 else config['run_id']), 'Native call run differs')
        require(not failures, 'Native invoked helper after fatal result')
        if not result['ok']:
            failures.append(dict(call_id=number, result=result, call=call)); continue
        operation, status = call['operation'], result['status']
        if operation == 'initialize': require(number == 1 and status == 'initialized', 'Initialization differs')
        elif operation == 'poll':
            require(pending is None, 'Polling while a request is pending')
            if status == 'request':
                data = result['request_wire'].encode('ascii')
                require(sha(data) == result['request_sha256'] and wire(result['request']) == data, 'Polled wire differs')
                pending = result
            elif status == 'stopped':
                marker = read(root / 'controls/stop.json')
                require(marker == dict(protocol=IO_PROTOCOL, run_id=config['run_id'], scope='cleanup-only') and
                        sha(wire(marker)) == result['marker_sha256'] and number == len(starts), 'Cleanup stop marker differs')
            else: require(status == 'idle', 'Unknown poll result')
        elif operation == 'publish':
            require(pending is not None and status == 'published' and call['request_wire'] == pending['request_wire'], 'Publication lacks matching poll')
            seq = len(seen) + 1; slot = f'{seq:08d}.json'
            data = pending['request_wire'].encode('ascii'); reply_raw = (root / 'replies' / slot).read_bytes()
            validate_reply(reply_raw, data, config['run_id'], seq)
            require(read(root / 'replies' / slot)['observation'] == call['observation'] and sha(reply_raw) == result['reply_sha256'], 'Native observation/reply differs')
            require((root / 'requests' / slot).read_bytes() == data and (root / 'staging/requests' / slot).read_bytes() == data and
                    (root / 'staging/replies' / slot).read_bytes() == reply_raw, 'Successful message/staging bytes differ')
            seen[slot] = sha(data); pending = None
        else: raise ValueError('Unadmitted helper operation')
    require(len(set(helper_pids)) == len(helper_pids), 'Helper process identity repeated')
    expected_errors = set()
    for failure in failures:
        result, number = failure['result'], failure['call_id']; slot = f'{number:08d}.json'
        require('error' in result and 'history_publication_error' not in result, 'Original operation failure/history missing')
        require(result['error']['owner'] in ('python-io', 'qcad-observer'), 'Error operation owner missing')
        expected = dict(io_protocol=IO_PROTOCOL, run_id=config['run_id'], error_id=number, **result['error'])
        if 'error_publication_error' not in result:
            require(read(root / 'errors' / slot) == expected and (root / 'errors' / slot).read_bytes() == (root / 'staging/errors' / slot).read_bytes(), 'Original native error export missing/changed')
            expected_errors.add(slot)
        else:
            require((root / 'staging/errors' / slot).is_file() and read(root / 'staging/errors' / slot) == expected, 'Error publication fallback lost its original staging record')
    require({p.name for p in (root / 'errors').iterdir()} == expected_errors, 'Missing/extra error history')
    return dict(calls=len(starts), replies=len(seen), failures=failures, completed_request_hashes=seen,
                sealed=records(console, 'ICT_IO_SEALED '), stopped=records(console, 'ICT_IO_STOPPED '))


def receive(root, basis_path, methods_path):
    root = Path(root); job = root / 'job'; mailbox = root / 'mailbox'
    inventory = read(root / 'INVENTORY.json')
    actual = {p.relative_to(root).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
              for p in root.rglob('*') if p.is_file() and p != root / 'INVENTORY.json'}
    require(actual == inventory['files'], 'Complete attempt inventory differs')
    methods = read(methods_path); freeze = read(job / 'JOB-FREEZE.json')
    for name, pin in freeze['files'].items(): require(sha((job / name).read_bytes()) == pin, 'Frozen input changed: ' + name)
    require(freeze['stage_sha256'] == methods['producers']['stage.py'], 'Staging method differs')
    for name, pin in methods['staged_methods'].items(): require(freeze['files'][name] == pin, 'Prospective method pin differs: ' + name)
    basis = read(basis_path); basis['role'] = 'receiving'
    require(read(job / 'job.json') == basis and sha((job / 'source.dxf').read_bytes()) == basis['source_sha256'], 'Original case basis/source differs')
    config = read(job / 'transport.json'); profile = config['profile']; process = read(job / 'native/PROCESS.json')
    require(config['io_protocol'] == IO_PROTOCOL and profile == inventory['profile'], 'Bridge/profile binding differs')
    require(process['exit'] == 0 and process['configuration_before'] == freeze['files']['.configuration/QCAD3.conf'], 'Native exit/configuration differs')
    handle = read(root / 'host/HANDLE.json'); require(handle['image'] == methods['image'], 'Native image differs')
    commands = [read(p) for p in sorted((root / 'host').glob('0*.json'))]
    inspections = [parse(r['stdout'])[0] for r in commands if r['command'][:2] == ['docker', 'inspect'] and r['exit'] == 0]
    require(inspections and inspections[-1]['Id'] == handle['id'] and inspections[-1]['State'] == inventory['native_container_state'] and
            inspections[-1]['State']['Status'] == 'exited', 'Actual same-container terminal state differs')
    launches = [r for r in commands if r['command'][:3] == ['docker', 'run', '-d']]
    require(len(launches) == 1 and launches[0]['exit'] == 0, 'Launch history differs')
    launch = launches[0]['command']
    for option, value in [('--network', 'none'), ('--user', '1001:1001'), ('--cap-drop', 'ALL'), ('--security-opt', 'no-new-privileges')]:
        require(launch[launch.index(option) + 1] == value, 'Native isolation differs')
    require('--rm' not in launch, 'Container not retained')
    stdout = (job / 'native/stdout.txt').read_text(encoding='utf-8'); stderr = (job / 'native/stderr.txt').read_text(encoding='utf-8')
    require('Script Exception:' not in stderr and 'Script Exception:' not in stdout, 'Unhandled native script exception')
    history = audit_history(mailbox, stdout, config, process['engine_pid'])
    actions = read(job / 'ui/actions.json'); require([r['event'] for r in actions] == list(range(1, len(actions) + 1)), 'Client action history differs')
    failures = [r for r in actions if r['kind'] == 'mailbox_failure']
    if profile == 'normal':
        require(process['controller_exit'] == 0 and inventory['native_container_state']['ExitCode'] == 0 and
                not failures and not history['failures'] and 'ICT_MAILBOX_FATAL ' not in stdout, 'Normal attempt retains failure')
        require((job / 'ui/RESULT.json').is_file() and not (job / 'ui/FAILURE.json').exists(), 'Normal result missing/failed')
        names = set(history['completed_request_hashes'])
        for role in ('requests', 'replies'):
            require({p.name for p in (mailbox / role).iterdir()} == names and
                    {p.name for p in (mailbox / 'staging' / role).iterdir()} == names, 'Normal message inventory differs')
        require(not list((mailbox / 'controls').iterdir()) and not list((mailbox / 'staging/controls').iterdir()) and
                not list((mailbox / 'staging/errors').iterdir()), 'Unexpected normal cleanup/error files')
        requests = [r for r in actions if r['kind'] == 'mailbox_request']; replies = [r for r in actions if r['kind'] == 'mailbox_reply']
        ids = list(range(1, history['replies'] + 1))
        require([r['seq'] for r in requests] == ids and [r['seq'] for r in replies] == ids, 'Client message coverage differs')
        for req, rep in zip(requests, replies):
            slot = f"{req['seq']:08d}.json"; data = (mailbox / 'requests' / slot).read_bytes(); raw = (mailbox / 'replies' / slot).read_bytes()
            require(req['wire'] == data.decode('ascii') and req['sha256'] == sha(data) and rep['sha256'] == sha(raw) and rep['reply'] == parse(raw), 'Client wire binding differs')
        require(len(history['sealed']) == 1 and history['sealed'][0] == dict(run_id=config['run_id'], seq=history['replies'], call_id=history['calls']), 'Complete native seal missing')
        require(read(mailbox / 'requests' / f"{history['replies']:08d}.json")['body'] == dict(action='seal'), 'Final transport status seal missing')
        fields = [r for r in actions if r['kind'] == 'native_fields']; frames = [r for r in actions if r['kind'] == 'absolute_frame']
        require(len(fields) == 1 and fields[0]['expected'] == basis['attributes'] and set(fields[0]['observed']) == set(basis['attributes']), 'Native UI fields differ')
        for tag, value in basis['attributes'].items():
            node = fields[0]['observed'][tag]
            require(node['text'] == value and node['editable'] and node['enabled'] and node['showing'], 'Actual native field/value/editability differs')
        require([r['frame'] for r in frames] == list(basis['frames']), 'Absolute frame coverage differs')
        for row in frames:
            observed = row['observation']; control, view = observed['camera_control'], observed['view']; frame = basis['frames'][row['frame']]
            require(observed['request']['frame'] == frame and control['width'] == view['width'] and control['height'] == view['height'], 'Frame/native view basis differs')
            margin = 48 if control['high_resolution'] else 24
            factor = min((view['width'] - 2 * margin) / (frame[2] - frame[0]), (view['height'] - 2 * margin) / (frame[3] - frame[1]))
            offset = [view['width'] / (2 * factor) - (frame[0] + frame[2]) / 2, view['height'] / (2 * factor) - (frame[1] + frame[3]) / 2]
            require(control['margin'] == margin and view['factor'] == control['factor'] == factor and view['offset'] == control['offset'] == offset, 'Exact absolute view formula differs')
        for row in replies:
            observed = row['reply']['observation']
            require(observed['qt'] == '5.14.2' and observed['configuration_file'] == '/home/cad/.config/QCAD/QCAD3.conf', 'Native observation environment differs')
            if observed['filename'] == '/work/source.dxf':
                attrs = observed['attributes']
                require(len(attrs) == len(basis['attributes']) and {r['tag']: r['text'] for r in attrs} == basis['attributes'] and
                        {r['parent_handle'] for r in attrs} == {basis['handle']}, 'Native source attribute coverage differs')
        return dict(status='normal-native-bridge-received', profile=profile, case=basis['case'], helper_calls=history['calls'],
                    requests=history['replies'], fields=1, absolute_frames=len(frames), whole_cad_qualified=False)
    require(process['controller_exit'] != 0 and inventory['native_container_state']['ExitCode'] != 0 and
            failures and (job / 'ui/FAILURE.json').is_file(), 'Original fault refusal missing')
    native_profiles = {'malformed', 'wrong-sequence', 'wrong-run', 'unsupported', 'read-open', 'reply-collision', 'reply-write', 'error-write'}
    if profile in native_profiles:
        require(len(history['failures']) == 1 and 'ICT_MAILBOX_FATAL ' in stdout, 'Original helper/native failure missing')
        result = history['failures'][0]['result']; error = result['error']
        if profile in ('read-open', 'reply-write'):
            require(error['owner'] == 'python-io' and error['errno'] == 13 and error['stage'] == ('read-open' if profile == 'read-open' else 'write-open'), 'Actual intended OS operation/errno differs')
        if profile == 'error-write': require(result.get('error_publication_error', {}).get('errno') == 13, 'Actual journal publication failure missing')
        if profile == 'reply-collision':
            request = next(r for r in actions if r['kind'] == 'fault_injection')
            require((mailbox / 'replies' / f"{request['seq']:08d}.json").read_bytes() == b'ORIGINAL COLLISION BYTES\n', 'Collision overwrote original bytes')
    if profile != 'native-exit':
        cleanup = read(job / 'native/CLEANUP.json')
        require(cleanup['native_pid'] == process['engine_pid'] and cleanup['native_start_identity'] == process['engine_start_identity'] and
                cleanup['close_exit'] == 0 and cleanup['live_helpers_before_close'] == [], 'Separate same-process cleanup differs')
        require(read(mailbox / 'controls/stop.json') == cleanup['stop_marker'], 'Cleanup marker binding differs')
    return dict(status='original-failed-bridge-attempt-retained', profile=profile, case=basis['case'],
                helper_calls=history['calls'], helper_failures=len(history['failures']), whole_cad_qualified=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('packet', type=Path); p.add_argument('basis', type=Path)
    p.add_argument('--methods', type=Path, default=HERE / 'BRIDGE-METHODS-1.json'); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists(): p.exit(1, 'New receipt required\n')
    try: result = receive(a.packet, a.basis, a.methods)
    except Exception as error: p.exit(1, str(error) + '\n')
    a.out.write_bytes(wire(result)); print(json.dumps(result))
