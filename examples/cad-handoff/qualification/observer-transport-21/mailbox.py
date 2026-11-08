"""Private serial native-observer mailbox; no CAD actions or plant connection."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

PROTOCOL = 'ict-native-mailbox/1'
MAX_BYTES = 65536


def wire(value):
    return (json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def publish(path, data):
    """Exclusive publication on one filesystem; retain complete staging bytes."""
    path = Path(path)
    stage = path.parent.parent / 'staging' / (path.parent.name + '-' + path.name)
    with stage.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(stage, path)  # Atomic no-replace publication, unlike Path.replace.
    path.chmod(0o444)


def validate_reply(raw, request_bytes, run_id, seq):
    request = json.loads(request_bytes)
    value = json.loads(raw)
    if set(value) != {'protocol', 'run_id', 'seq', 'request_wire', 'observation'}:
        raise ValueError('Reply envelope differs')
    if (value['protocol'], value['run_id'], value['seq']) != (PROTOCOL, run_id, seq):
        raise ValueError('Reply sequence/run binding differs')
    if not isinstance(value['seq'], int) or isinstance(value['seq'], bool):
        raise ValueError('Reply sequence type differs')
    if value['request_wire'].encode('ascii') != request_bytes:
        raise ValueError('Reply request wire binding differs')
    if request != dict(protocol=PROTOCOL, run_id=run_id, seq=seq, body=request.get('body')):
        raise ValueError('Request envelope differs')
    if not isinstance(value['observation'], dict) or value['observation'].get('request') != dict(seq=seq, **request['body']):
        raise ValueError('Observation request binding differs')
    return value['observation']


class Mailbox:
    def __init__(self, root, run_id, alive, record, console_path, timeout=20):
        self.root, self.run_id = Path(root), run_id
        if not re.fullmatch('[a-f0-9]{32}', run_id):
            raise ValueError('Invalid mailbox run identity')
        self.alive, self.record, self.console_path = alive, record, Path(console_path)
        self.timeout, self.seq, self.failed = timeout, 0, False
        self.published = {}

    def check(self):
        if self.failed:
            raise ValueError('Mailbox already failed; no dependent request')
        if list((self.root / 'errors').iterdir()):
            raise ValueError('Native error journal retained')
        if self.console_path.exists() and b'ICT_MAILBOX_FATAL ' in self.console_path.read_bytes():
            raise ValueError('Native console retains fatal transport error')
        if not self.alive():
            raise ValueError('Actual native process exited; no restart')
        for name, data in self.published.items():
            if not (self.root / 'requests' / name).is_file() or (self.root / 'requests' / name).read_bytes() != data:
                raise ValueError('Published request changed or disappeared')

    def request(self, body, inject=None, after_publish=None):
        try:
            self.check()
            self.seq += 1
            name = f'{self.seq:08d}.json'
            envelope = dict(protocol=PROTOCOL, run_id=self.run_id, seq=self.seq, body=body)
            data = wire(envelope)
            if len(data) > MAX_BYTES:
                raise ValueError('Request exceeds bounded wire size')
            if inject:
                data = inject(self, envelope, data)
            self.published[name] = data
            path = self.root / 'requests' / name
            # A fault injector may publish an unreadable request itself, atomically.
            if not path.exists():
                publish(path, data)
            self.record('mailbox_request', seq=self.seq, path=str(path), sha256=sha(data), wire=data.decode('ascii'))
            if after_publish:
                after_publish(self, path)
            target = self.root / 'replies' / name
            deadline = time.monotonic() + self.timeout
            while not target.is_file():
                self.check()
                if time.monotonic() >= deadline:
                    raise ValueError('Native reply deadline; same process retained')
                time.sleep(.1)
            self.check()
            raw = target.read_bytes()
            observation = validate_reply(raw, data, self.run_id, self.seq)
            self.record('mailbox_reply', seq=self.seq, sha256=sha(raw), reply=json.loads(raw))
            return observation
        except Exception as error:
            self.failed = True
            self.record('mailbox_failure', seq=self.seq, error=str(error))
            raise


def audit(root, run_id, expected_requests):
    """Receive a complete normal mailbox; errors/partials never become a pass."""
    root = Path(root)
    if set(p.name for p in root.iterdir()) != {'requests', 'replies', 'errors', 'staging'}:
        raise ValueError('Mailbox directory inventory differs')
    if list((root / 'errors').iterdir()):
        raise ValueError('Native errors present; packet failed')
    expected_names = {f'{i:08d}.json' for i in range(1, len(expected_requests) + 1)}
    for folder in ('requests', 'replies'):
        if set(p.name for p in (root / folder).iterdir()) != expected_names:
            raise ValueError('Missing/extra ' + folder)
    stages = {f'{role}-{name}' for role in ('requests', 'replies') for name in expected_names}
    if set(p.name for p in (root / 'staging').iterdir()) != stages:
        raise ValueError('Incomplete staging history')
    observations = []
    for seq, body in enumerate(expected_requests, 1):
        name = f'{seq:08d}.json'
        req, rep = (root / 'requests' / name).read_bytes(), (root / 'replies' / name).read_bytes()
        if req != wire(dict(protocol=PROTOCOL, run_id=run_id, seq=seq, body=body)):
            raise ValueError('Request differs from intended action')
        for folder, data in [('requests', req), ('replies', rep)]:
            if (root / 'staging' / (folder + '-' + name)).read_bytes() != data:
                raise ValueError('Published/staging bytes differ')
        observations.append(validate_reply(rep, req, run_id, seq))
    return dict(status='normal-mailbox-received', requests=len(observations), observations=observations,
                whole_cad_qualified=False)
