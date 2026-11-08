"""Receive every frozen event-driven normal/fault packet offline, without QCAD."""
import json
from pathlib import Path
import tempfile
from bridge_receive import receive
from native_io import FOLDERS
from recheck_evidence import HERE, unpack, require


def check_files(files, label):
    catalog = json.loads((HERE / 'BRIDGE-FROZEN-INPUTS-2.json').read_bytes())
    freeze = json.loads(files['attempt/job/JOB-FREEZE.json'])
    require(freeze == catalog[label]['freeze'] and json.loads(files['case/basis.json']) == catalog[label]['basis'], 'Original event-driven input/method freeze differs')
    require(json.loads(files['methods/BRIDGE-METHODS-2.json']) == json.loads((HERE / 'BRIDGE-METHODS-2.json').read_bytes()), 'Original method manifest differs')
    with tempfile.TemporaryDirectory(prefix='ict-native-bridge-') as tmp:
        root = Path(tmp); attempt = root / 'attempt'
        for name, data in files.items():
            if name.startswith('attempt/') or name == 'case/basis.json':
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        for role in FOLDERS:
            for path in (attempt / 'mailbox' / role, attempt / 'mailbox/staging' / role): path.mkdir(parents=True, exist_ok=True)
        result = receive(attempt, root / 'case/basis.json', HERE / 'BRIDGE-METHODS-2.json')
    require(result == json.loads(files['receiving/result.json']), 'Original receiving receipt differs')
    command = json.loads(files['receiving/command.json'])
    require(command['exit'] == 0 and json.loads(command['stdout']) == result, 'Original receiving command differs')
    original = json.loads(files['execution/EXIT.json'])
    require(original['exit'] == (0 if result['profile'] == 'normal' else 1), 'Original controller host exit differs')
    return result


def check():
    catalog = json.loads((HERE / 'BRIDGE-FROZEN-INPUTS-2.json').read_bytes())
    expected = {'normal-air', 'normal-template'} | {'fault-' + p for p in (
        'malformed', 'wrong-sequence', 'wrong-run', 'unsupported', 'read-open', 'reply-collision',
        'reply-write', 'error-write', 'missing-reply', 'changed-request', 'native-exit')}
    require(set(catalog) == expected, 'Complete normal/fault campaign differs')
    results = {}
    for label in sorted(catalog):
        packet = HERE / 'bridge-2' / label; files = unpack(packet)
        result = check_files(files, label)
        require(result == json.loads((packet / 'RESULT.json').read_bytes()), 'Readable receiving projection differs')
        results[label] = result
    require(results == json.loads((HERE / 'BRIDGE-RESULTS-2.json').read_bytes()), 'Campaign summary differs')
    return dict(attempts=results, whole_cad_qualified=False)


if __name__ == '__main__': print(json.dumps(check(), indent=2))
