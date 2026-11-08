"""Native dialog responsiveness while the same immutable-mailbox poll waits."""
import json
from pathlib import Path
import time
import traceback
from bridge_workflow import BridgeWorkflow
from original_workflow import ROOT, matching, one, require, write, sha
from mailbox import publish, wire


class Probe(BridgeWorkflow):
    def helper(self):
        parent=Path(f'/proc/{self.native_pid}')
        rows=[]
        for pid in (parent/'task'/str(self.native_pid)/'children').read_text().split():
            path=Path('/proc')/pid
            try:
                fields=(path/'stat').read_text().split();args=(path/'cmdline').read_bytes().split(b'\0')
            except FileNotFoundError: continue
            if fields[2] in ('Z','X'): continue
            require(b'/work/native_io.py' in args,'Unexpected live native child')
            rows.append(dict(pid=int(pid),parent=int(fields[3]),start_identity=fields[21],arguments=[a.decode('ascii') for a in args if a]))
        require(len(rows)==1,'Expected exactly one live waiting helper')
        require(rows[0]['parent']==self.native_pid,'Waiting helper parent differs')
        return rows[0]

    def wait_helper(self):
        for _ in range(100):
            try: return self.helper()
            except ValueError: time.sleep(.1)
        raise ValueError('Waiting helper not observed; retain same processes')

    def run(self):
        before=sha(ROOT/'source.dxf');self.startup()
        helper=self.wait_helper();start=time.monotonic()
        self.record('waiting_helper_before_ui',helper=helper)
        time.sleep(6)
        require(self.helper()==helper,'Idle helper changed before UI')
        events=Path('/home/cad/ict-mailbox-21/events')
        before_events=sorted(p.name for p in events.iterdir())
        self.keys('ctrl+o');dialog=self.dialog('Open Drawing');self.snapshot('waiting-open')
        self.control('type',one(dialog,'text','File name:'),'/work/source.dxf')
        tree=self.snapshot('waiting-filename')
        require(one(one(tree,'dialog','Open Drawing'),'text','File name:')['text']=='/work/source.dxf','Native text completion differs')
        require(self.helper()==helper,'Helper changed during native text')
        self.record('waiting_helper_after_text',helper=helper)
        self.control('press',one(one(tree,'dialog','Open Drawing'),'push button','Cancel'))
        self.wait(lambda t:not matching(t,'dialog'),'Open canceled');self.snapshot('waiting-canceled')
        require(self.helper()==helper and sorted(p.name for p in events.iterdir())==before_events,'Idle event burst/helper change')
        elapsed=time.monotonic()-start;require(elapsed>5,'Old helper deadline not exceeded')
        self.record('waiting_helper_after_cancel',helper=helper,elapsed=elapsed,events=before_events)
        observed=self.observe();require(observed['filename']=='' and observed['modified'] is False,'Probe opened/modified drawing')
        replies=Path('/home/cad/ict-mailbox-21/events')
        events_now=[json.loads(p.read_bytes()) for p in sorted(replies.iterdir())]
        completed=[r for r in events_now if r['result'].get('status')=='request' and r['result']['owner_pid']==helper['pid']]
        require(len(completed)==1,'Actual request was not served by same waiting helper')
        self.record('waiting_request_received',helper=helper,observation=observed,helper_event=completed[0])
        next_helper=self.wait_helper();marker=dict(protocol='ict-native-io/1',run_id=self.config['run_id'],scope='cleanup-only')
        publish(Path('/home/cad/ict-mailbox-21/controls/stop.json'),wire(marker))
        self.record('waiting_stop_published',helper=next_helper,marker=marker)
        for _ in range(100):
            text=(ROOT/'native/stdout.txt').read_text(encoding='utf-8')
            if 'ICT_IO_STOPPED ' in text: break
            self.mailbox.check();time.sleep(.1)
        else: raise ValueError('Waiting helper did not acknowledge stop')
        children=Path(f'/proc/{self.native_pid}/task/{self.native_pid}/children').read_text().split()
        live=[]
        for pid in children:
            try:
                if Path(f'/proc/{pid}/stat').read_text().split()[2] not in ('Z','X'): live.append(pid)
            except FileNotFoundError: pass
        require(not live and sha(ROOT/'source.dxf')==before,'Stop left helper/source changed')
        windows=[r for r in self.command(['wmctrl','-l']).splitlines() if 'Untitled 1 - QCAD Professional Trial' in r]
        require(len(windows)==1,'Unexpected native close window');self.command(['wmctrl','-ic',windows[0].split()[0]])
        write(self.out/'RESULT.json',dict(status='waiting-helper-native-probe-complete',elapsed=elapsed,
              same_waiting_helper=helper,next_waiting_helper=next_helper,source_sha256=before,whole_cad_qualified=False))


if __name__=='__main__':
    w=Probe()
    try: w.run()
    except Exception:
        write(w.out/'FAILURE.json',dict(traceback=traceback.format_exc(),native_pid=w.native_pid,
              native_start_identity=w.start_identity,native_live=w.alive(),run_id=w.config['run_id'],scope='Original waiting probe failure; same processes retained'))
        raise
