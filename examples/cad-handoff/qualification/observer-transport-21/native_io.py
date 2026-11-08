"""Pinned private-mailbox I/O owner. No CAD interpretation, arbitrary path or shell CLI."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from mailbox import PROTOCOL, wire, validate_reply

IO_PROTOCOL = 'ict-native-io/1'
LIMIT = 65536
ARG_LIMIT = 60000
FOLDERS = ('requests', 'replies', 'errors', 'events', 'controls')


def sha(data): return hashlib.sha256(data).hexdigest()


def parse(data):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out: raise ValueError('Duplicate JSON key: ' + key)
            out[key] = value
        return out
    def bad_constant(value): raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(data, object_pairs_hook=unique, parse_constant=bad_constant)


def integer(value, minimum=1):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


class Runner:
    def __init__(self, root, configuration):
        self.root, self.configuration = Path(root), Path(configuration)
        self.stage, self.path, self.request_wire = 'admission', None, None
        self.run_id, self.seq, self.call_id = None, None, None

    def require(self, ok, message):
        if not ok: raise ValueError(message)

    def read(self, path, limit=LIMIT):
        self.stage, self.path = 'read-open', str(path)
        with Path(path).open('rb') as stream:
            self.stage = 'read-bytes'; data = stream.read(limit + 1)
        self.require(len(data) <= limit, 'File exceeds declared byte limit')
        return data

    def publish(self, folder, name, data, limit=LIMIT):
        self.require(folder in FOLDERS and re.fullmatch(r'[0-9]{8}\.json|stop\.json', name), 'Invalid publication slot')
        self.require(len(data) <= limit, 'Publication exceeds declared byte limit')
        stage, target = self.root / 'staging' / folder / name, self.root / folder / name
        self.stage, self.path = 'write-open', str(stage)
        with stage.open('xb') as stream:
            self.stage = 'write-bytes'; stream.write(data)
            self.stage = 'write-flush'; stream.flush(); os.fsync(stream.fileno())
        self.stage, self.path = 'publish-link', str(target)
        os.link(stage, target)
        self.stage = 'publish-readonly'; target.chmod(0o444)

    def error(self, exc, owner='python-io'):
        return dict(owner=owner, exception=type(exc).__name__, errno=getattr(exc, 'errno', None),
                    message=str(exc), stage=self.stage, path=self.path, seq=self.seq,
                    request_wire=self.request_wire)

    def prior_event(self):
        names = {p.name for p in (self.root / 'events').iterdir()}
        expected = {f'{i:08d}.json' for i in range(1, self.call_id)}
        self.require(names == expected, 'Invocation history is not contiguous')
        if self.call_id == 1: return None
        data = self.read(self.root / 'events' / f'{self.call_id - 1:08d}.json', 4 * LIMIT)
        previous = parse(data)
        self.require(previous['result']['ok'] is True, 'Invocation after a fatal helper error')
        self.require(previous['result']['run_id'] == self.run_id, 'Invocation run changed')
        return sha(data)

    def requests(self, seen):
        self.require(isinstance(seen, dict), 'Seen request hashes must be an object')
        expected = {f'{i:08d}.json' for i in range(1, self.seq)}
        self.require(set(seen) == expected, 'Seen request sequence differs')
        names = {p.name for p in (self.root / 'requests').iterdir()}
        self.require(names in (expected, expected | {f'{self.seq:08d}.json'}), 'Request inventory/sequence differs')
        for name, pin in seen.items():
            self.require(isinstance(pin, str) and re.fullmatch('[a-f0-9]{64}', pin), 'Invalid request hash')
            self.require(sha(self.read(self.root / 'requests' / name)) == pin, 'Previously published request changed')
        return f'{self.seq:08d}.json' in names

    def current(self):
        data = self.read(self.root / 'requests' / f'{self.seq:08d}.json')
        self.request_wire = data.decode('ascii')
        self.stage = 'request-envelope'
        request = parse(self.request_wire)
        self.require(isinstance(request, dict) and set(request) == {'protocol', 'run_id', 'seq', 'body'}, 'Request envelope differs')
        self.require(request['protocol'] == PROTOCOL and request['run_id'] == self.run_id and
                     integer(request['seq']) and request['seq'] == self.seq, 'Request run/sequence differs')
        self.require(isinstance(request['body'], dict), 'Request body must be an object')
        self.require(data == wire(request), 'Request wire is not its canonical ASCII representation')
        return request, data

    def execute(self, call):
        operation = call['operation']
        if operation == 'initialize':
            self.require(self.call_id == 1 and self.seq == 1 and call['seen'] == {}, 'Initialization sequence differs')
            return dict(status='initialized')
        self.require(operation in ('poll', 'publish'), 'Unsupported I/O operation')
        if operation == 'poll':
            control = self.root / 'controls/stop.json'
            if control.exists():
                marker = parse(self.read(control))
                self.require(marker == dict(protocol=IO_PROTOCOL, run_id=self.run_id, scope='cleanup-only'), 'Invalid cleanup stop marker')
                return dict(status='stopped', marker_sha256=sha(wire(marker)))
            present = self.requests(call['seen'])
            if not present: return dict(status='idle')
            request, data = self.current()
            return dict(status='request', request=request, request_wire=data.decode('ascii'), request_sha256=sha(data))
        self.requests(call['seen'])
        request, data = self.current()
        self.require(call['request_wire'] == data.decode('ascii'), 'Publication request wire changed')
        if 'native_error' in call:
            native = call['native_error']
            self.require(isinstance(native, dict) and set(native) == {'message', 'stage'} and isinstance(native['message'], str), 'Native error envelope differs')
            error = dict(owner='qcad-observer', exception='NativeObservationError', errno=None,
                         message=native['message'], stage=native['stage'], path=None,
                         seq=self.seq, request_wire=self.request_wire)
            return dict(status='native-error', native_error=error)
        reply = dict(protocol=PROTOCOL, run_id=self.run_id, seq=self.seq, request_wire=data.decode('ascii'), observation=call['observation'])
        serialized = wire(reply)
        validate_reply(serialized, data, self.run_id, self.seq)
        self.publish('replies', f'{self.seq:08d}.json', serialized)
        return dict(status='published', reply_sha256=sha(serialized))

    def run(self, input_wire):
        result = dict(io_protocol=IO_PROTOCOL, ok=False, call_id=None, run_id=None,
                      owner_pid=os.getpid(), qt_parent_pid=os.getppid(), uid=os.getuid() if hasattr(os, 'getuid') else None)
        previous = None
        try:
            self.require(len(input_wire.encode('ascii')) <= ARG_LIMIT, 'Helper argument exceeds bound')
            call = parse(input_wire)
            self.require(isinstance(call, dict), 'Helper call must be an object')
            self.call_id, self.seq = call.get('call_id'), call.get('seq')
            self.require(integer(self.call_id) and self.call_id <= 4096 and integer(self.seq), 'Invalid invocation identity')
            result['call_id'] = self.call_id
            config = parse(self.read(self.configuration))
            self.run_id = config['run_id']; result['run_id'] = self.run_id
            self.require(config['protocol'] == PROTOCOL and config['io_protocol'] == IO_PROTOCOL and re.fullmatch('[a-f0-9]{32}', self.run_id), 'Frozen helper configuration differs')
            self.stage = 'call-envelope'; self.path = None
            base_keys = {'io_protocol', 'call_id', 'operation', 'run_id', 'seq', 'seen'}
            keys = set(call)
            if call['operation'] == 'publish':
                self.require(keys in (base_keys | {'request_wire', 'observation'}, base_keys | {'request_wire', 'native_error'}), 'Publish call keys differ')
            else: self.require(keys == base_keys, 'Helper call keys differ')
            self.require(call['io_protocol'] == IO_PROTOCOL and
                         (call['run_id'] == self.run_id or (call['operation'] == 'initialize' and call['run_id'] is None)), 'Helper run binding differs')
            previous = self.prior_event()
            self.require(not list((self.root / 'errors').iterdir()), 'Helper called after recorded native error')
            result.update(self.execute(call))
            result['ok'] = 'native_error' not in result
            if not result['ok']: result['error'] = result.pop('native_error')
        except Exception as exc:
            result['error'] = self.error(exc)
        if not result['ok']:
            try:
                record = dict(io_protocol=IO_PROTOCOL, run_id=self.run_id, error_id=self.call_id, **result['error'])
                self.publish('errors', f'{self.call_id:08d}.json', wire(record))
            except Exception as exc:
                result['error_publication_error'] = self.error(exc)
        try:
            event = dict(input_wire=input_wire, previous_event_sha256=previous, result=result)
            data = wire(event)
            self.publish('events', f'{self.call_id:08d}.json', data, 4 * LIMIT)
            result = dict(result, event_name=f'{self.call_id:08d}.json', event_sha256=sha(data))
        except Exception as exc:
            result = dict(result, ok=False, history_publication_error=self.error(exc))
        response = wire(result)
        if len(response) > LIMIT:
            # Never truncate an observation. Retain the full event and fail output.
            result = dict(io_protocol=IO_PROTOCOL, ok=False, call_id=self.call_id, run_id=self.run_id,
                          output_error='Helper response exceeds declared bound', event_sha256=result.get('event_sha256'))
        return result


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('Exactly one structured helper argument required')
        response = Runner('/home/cad/ict-mailbox-21', '/work/transport.json').run(sys.argv[1])
    except Exception as exc:
        response = dict(io_protocol=IO_PROTOCOL, ok=False, entry_error=type(exc).__name__ + ': ' + str(exc))
    sys.stdout.buffer.write(wire(response)); sys.stdout.buffer.flush()
    raise SystemExit(0 if response['ok'] else 1)
