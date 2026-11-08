"""Actual subprocess controls for the new waiting-helper lifecycle; no CAD claim."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent


class WaitingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ict-wait22-');self.work=Path(self.temp.name)
        for source,target in [(HERE/'native_io_wait.py','native_io_wait.py'),
                              (HERE.parent/'observer-transport-21/native_io.py','base_native_io.py'),
                              (HERE.parent/'observer-transport-21/mailbox.py','mailbox.py')]:
            shutil.copyfile(source,self.work/target)
        self.root=self.work/'mailbox';self.root.mkdir()
        for name in ('requests','replies','errors','events','controls'):
            (self.root/name).mkdir();(self.root/'staging'/name).mkdir(parents=True)
        self.run_id='a'*32;self.seq=1;self.number=0;self.seen={};self.children=[]
        self.config=self.work/'transport.json'
        self.config.write_text(json.dumps(dict(protocol='ict-native-mailbox/1',io_protocol='ict-native-io/1',run_id=self.run_id)))
        self.assertEqual(self.call('initialize')['status'],'initialized')

    def tearDown(self):
        for child in self.children:
            if child.poll() is None: child.kill();child.communicate()
        for path in self.work.rglob('*'):
            if path.is_file(): path.chmod(0o600)
        self.temp.cleanup()

    @staticmethod
    def wire(value): return (json.dumps(value,ensure_ascii=True,separators=(',',':'))+'\n').encode('ascii')

    def start(self,operation,**extra):
        self.number+=1
        value=dict(io_protocol='ict-native-io/1',call_id=self.number,operation=operation,
                   run_id=None if self.number==1 else self.run_id,seq=self.seq,seen=self.seen,**extra)
        code='import sys;from native_io_wait import Runner,wire;r=Runner(sys.argv[1],sys.argv[2]).run(sys.argv[3]);sys.stdout.buffer.write(wire(r));raise SystemExit(0 if r["ok"] else 1)'
        child=subprocess.Popen([sys.executable,'-c',code,str(self.root),str(self.config),self.wire(value).decode('ascii')],
                               cwd=self.work,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(child);return child

    def finish(self,child,ok=True):
        stdout,stderr=child.communicate(timeout=8);self.assertEqual(stderr,b'')
        result=json.loads(stdout);self.assertEqual(child.returncode,0 if ok else 1);self.assertIs(result['ok'],ok)
        event=self.root/'events'/result['event_name'];self.assertTrue(event.is_file())
        self.assertEqual(event.read_bytes(),(self.root/'staging/events'/event.name).read_bytes())
        if not ok:
            error=json.loads((self.root/'errors'/event.name).read_bytes());self.assertEqual(error['message'],result['error']['message'])
            self.assertEqual((self.root/'errors'/event.name).read_bytes(),(self.root/'staging/errors'/event.name).read_bytes())
        return result

    def call(self,operation,ok=True,**extra): return self.finish(self.start(operation,**extra),ok)

    def post(self,data):
        name=f'{self.seq:08d}.json'
        for folder in ('requests','staging/requests'): (self.root/folder/name).write_bytes(data)

    def request(self,**changes):
        return self.wire(dict(protocol='ict-native-mailbox/1',run_id=self.run_id,seq=self.seq,body=dict(action='status'),**changes))

    def test_idle_beyond_old_deadline_request_then_stop(self):
        child=self.start('poll');time.sleep(6)
        self.assertIsNone(child.poll());self.assertEqual(len(list((self.root/'events').iterdir())),1)
        request=self.request();self.post(request);result=self.finish(child)
        self.assertEqual(result['status'],'request');self.assertEqual(result['owner_pid'],child.pid)
        self.assertEqual(result['request_wire'],request.decode('ascii'))
        self.call('publish',request_wire=request.decode('ascii'),observation=dict(request=dict(seq=1,action='status')))
        import hashlib
        self.seen={'00000001.json':hashlib.sha256(request).hexdigest()};self.seq=2
        child=self.start('poll');time.sleep(.25);self.assertIsNone(child.poll())
        marker=self.wire(dict(protocol='ict-native-io/1',run_id=self.run_id,scope='cleanup-only'))
        (self.root/'controls/stop.json').write_bytes(marker)
        self.assertEqual(self.finish(child)['status'],'stopped')
        self.assertEqual(len(list((self.root/'events').iterdir())),4)

    def rejected_request(self,raw,expected):
        child=self.start('poll');time.sleep(.2);self.assertIsNone(child.poll());self.post(raw)
        result=self.finish(child,False);self.assertIn(expected,result['error']['message'])

    def test_malformed_after_wait(self): self.rejected_request(b'{invalid\n','Expecting property')

    def test_wrong_run_after_wait(self):
        value=json.loads(self.request());value['run_id']='0'*32
        self.rejected_request(self.wire(value),'Request run/sequence differs')

    def test_wrong_sequence_after_wait(self):
        value=json.loads(self.request());value['seq']=2
        self.rejected_request(self.wire(value),'Request run/sequence differs')

    def test_prior_request_mutation_while_waiting(self):
        request=self.request();self.post(request);self.call('poll')
        self.call('publish',request_wire=request.decode('ascii'),observation=dict(request=dict(seq=1,action='status')))
        import hashlib
        self.seen={'00000001.json':hashlib.sha256(request).hexdigest()};self.seq=2
        child=self.start('poll');time.sleep(.25);self.assertIsNone(child.poll())
        (self.root/'requests/00000001.json').write_bytes(request+b' ')
        self.assertIn('Previously published request changed',self.finish(child,False)['error']['message'])

    def test_publication_collision_keeps_original(self):
        request=self.request();self.post(request);self.call('poll')
        target=self.root/'replies/00000001.json';target.write_bytes(b'ORIGINAL COLLISION BYTES\n')
        result=self.call('publish',ok=False,request_wire=request.decode('ascii'),observation=dict(request=dict(seq=1,action='status')))
        self.assertEqual(result['error']['exception'],'FileExistsError')
        self.assertEqual(target.read_bytes(),b'ORIGINAL COLLISION BYTES\n')


if __name__=='__main__': unittest.main()
