"""Native bridge development; same UI methods, explicit transport seal and failure retention."""
import copy
import json
import os
from pathlib import Path
import signal
import time
import traceback

from original_workflow import Workflow, ROOT, write, require
from mailbox import Mailbox, PROTOCOL, wire


class BridgeWorkflow(Workflow):
    def __init__(self):
        super().__init__()
        self.config = json.loads((ROOT / 'transport.json').read_bytes())
        self.native_pid = json.loads((ROOT / 'native/PROCESS.json').read_bytes())['engine_pid']
        self.start_identity = Path(f'/proc/{self.native_pid}/stat').read_text().split()[21]
        self.mailbox = Mailbox('/home/cad/ict-mailbox-21', self.config['run_id'], self.alive,
                               self.record, ROOT / 'native/stdout.txt', timeout=5)

    def record(self, kind, **kw):
        super().record(kind, **copy.deepcopy(kw))

    def alive(self):
        p = Path(f'/proc/{self.native_pid}/stat')
        if not p.exists():
            return False
        fields = p.read_text().split()
        return fields[2] not in ('Z', 'X') and fields[21] == self.start_identity

    def observe(self, **kw):
        body = dict(action='status', **kw) if 'action' not in kw else kw
        result = self.mailbox.request(body)
        self.seq = self.mailbox.seq
        self.record('native_observation', reply=result)
        return result

    def signal(self, value):
        self.record('fault_signal', pid=self.native_pid, signal=value, start_identity=self.start_identity)
        require(self.alive(), 'Fault native PID changed or exited')
        os.kill(self.native_pid, value)
        if value == signal.SIGSTOP:
            for _ in range(100):
                children=Path(f'/proc/{self.native_pid}/task/{self.native_pid}/children').read_text().split()
                states=[]
                for child in children:
                    p=Path('/proc')/child
                    try:states.append(dict(pid=int(child),state=(p/'stat').read_text().split()[2],arguments=(p/'cmdline').read_bytes().decode('utf-8',errors='replace').split('\0')))
                    except FileNotFoundError:pass
                if all(r['state'] in ('Z','X') for r in states):break
                time.sleep(.1)
            else:raise ValueError('Existing helper not terminal after deliberate native pause; retain same handles')
            self.record('paused_helper_drain', native_pid=self.native_pid, observed_children=states)

    def finish(self):
        require(self.observe()['modified'] is False, 'Refuse native close with modified document')
        observation = self.mailbox.request(dict(action='seal'))
        self.seq = self.mailbox.seq
        self.record('native_observation', reply=observation)
        for _ in range(100):
            lines=(ROOT/'native/stdout.txt').read_text(encoding='utf-8',errors='replace').splitlines()
            acknowledgements=[json.loads(line.split('ICT_IO_SEALED ',1)[1]) for line in lines if 'ICT_IO_SEALED ' in line]
            if any(r['run_id']==self.config['run_id'] and r['seq']==self.seq for r in acknowledgements):break
            time.sleep(.1)
        else:raise ValueError('Native transport seal not acknowledged; keep same process')
        self.record('native_transport_sealed', seq=self.seq, run_id=self.config['run_id'])
        windows=[r for r in self.command(['wmctrl','-l']).splitlines() if ' - QCAD Professional Trial' in r]
        require(len(windows)==1,'Ambiguous native window for normal close')
        self.command(['wmctrl','-ic',windows[0].split()[0]])

    def run(self):
        self.startup()
        profile = self.config['profile']
        if profile == 'normal':
            self.open_file('/work/source.dxf')
            self.select_and_verify('/work/source.dxf', self.job['attributes'], True)
            self.focus_canvas(); self.keys('Escape', 'Escape', 't', 'n')
            for name, frame in self.job['frames'].items():
                observed = self.observe(action='frame', expected_path='/work/source.dxf', frame=frame)
                expected, actual = observed['camera_control'], observed['view']
                require(expected['factor'] == actual['factor'] and expected['offset'] == actual['offset'], 'Absolute camera differs')
                self.record('absolute_frame', frame=name, observation=observed)
            self.close_doc(); self.finish()
            write(self.out / 'RESULT.json', dict(status='controller-complete', case=self.job['case'], profile=profile,
                                                whole_cad_qualified=False))
            return
        if profile == 'native-exit':
            self.finish()
            for _ in range(100):
                if not self.alive(): break
                time.sleep(.1)
            require(not self.alive(), 'Normal UI exit not observed')
            self.mailbox.request(dict(action='status'))
            raise ValueError('Native exit fault was not refused')

        def inject(client, envelope, data):
            seq = client.seq; name = f'{seq:08d}.json'; root = client.root
            self.record('fault_injection', profile=profile, seq=seq, native_pid=self.native_pid)
            if profile == 'malformed': return b'{invalid\n'
            if profile == 'wrong-sequence': envelope['seq'] += 1; return wire(envelope)
            if profile == 'wrong-run': envelope['run_id'] = '0' * 32; return wire(envelope)
            if profile == 'unsupported': envelope['body'] = dict(action='save'); return wire(envelope)
            if profile == 'reply-collision':
                (root / 'replies' / name).write_bytes(b'ORIGINAL COLLISION BYTES\n')
            elif profile == 'error-write':
                (root / 'errors').chmod(0o500); return b'{invalid\n'
            elif profile in ('read-open', 'reply-write', 'missing-reply', 'changed-request'):
                self.signal(signal.SIGSTOP)
            else:
                raise ValueError('Unknown frozen fault profile')
            return data

        def after(client, path):
            if profile == 'read-open': path.chmod(0)
            if profile == 'reply-write': (client.root / 'staging/replies').chmod(0o500)
            if profile == 'changed-request':
                path.chmod(0o644); path.write_bytes(b'{changed after publication}\n')
            if profile in ('read-open', 'reply-write', 'changed-request'):
                self.signal(signal.SIGCONT)
        self.mailbox.request(dict(action='status'), inject=inject, after_publish=after)
        raise ValueError('Deliberate fault did not refuse')


if __name__ == '__main__':
    workflow = BridgeWorkflow()
    try:
        workflow.run()
    except Exception:
        write(workflow.out / 'FAILURE.json', dict(traceback=traceback.format_exc(), native_pid=workflow.native_pid,
                                                native_live=workflow.alive(), native_start_identity=workflow.start_identity, run_id=workflow.config['run_id'], scope='Original controller failure; same process retained'))
        # Wait for a native error/fallback without issuing any further request.
        time.sleep(1)
        state=Path(f'/proc/{workflow.native_pid}/stat')
        paused=state.exists() and state.read_text().split()[2] in ('T','t')
        if paused:workflow.record('failure_snapshot_unavailable',reason='Deliberately paused actual Qt child; no AT-SPI request',native_pid=workflow.native_pid)
        else:
            try:workflow.snapshot('failure')
            except Exception:pass
        raise
