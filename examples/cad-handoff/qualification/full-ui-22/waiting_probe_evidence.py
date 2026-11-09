"""Receive complete waiting-helper probes; retain failed predecessor separately."""
import argparse
import io
import json
from pathlib import Path
import tarfile
import tempfile
from evidence import unpack, MAX_FILES, MAX_FILE, MAX_RAW
from receive import HERE, read, require, digest, sha, equal, audit_history
from native_io import FOLDERS


def check_files(files,identity,number):
    def data(name): return json.loads(files[name])
    for name,pin in identity['original_identity'].items(): require(digest(files[name])==pin,'Original probe identity differs: '+name)
    base='attempt/job/';freeze=data(base+'JOB-FREEZE.json')
    require(freeze==identity['freeze'],'Original probe freeze differs')
    for name,pin in freeze['files'].items(): require(digest(files[base+name])==pin,'Frozen probe input differs: '+name)
    methods=read(HERE/f'WAITING-METHODS-{number}.json');prefix='examples/cad-handoff/qualification/'
    for target,source in [('native_io.py','full-ui-22/native_io_wait.py'),('base_native_io.py','observer-transport-21/native_io.py'),
                          ('observe_case.js','full-ui-22/waiting_observer.js'),('workflow.py','full-ui-22/waiting_probe.py')]:
        require(freeze['files'][target]==methods['files'][prefix+source],'Prospective waiting probe method differs')
    require(freeze['producer_sha256']==methods['files'][prefix+'full-ui-22/prepare_wait.py'],'Frozen probe staging differs')
    process=data(base+'native/PROCESS.json');config=data(base+'transport.json');handle=data('attempt/host/HANDLE.json')
    expected=1 if number==1 else 0
    require(handle['image']==methods['image'] and process['exit']==0 and process['controller_exit']==expected and
            data('execution/EXIT.json')['exit']==expected and process['configuration_before']==read(HERE/'PREPARATION-1.json')['configuration_sha256'],'Actual probe outcomes/configuration differ')
    inspections=[]
    for name in files:
        if name.startswith(('attempt/host/','attempt/inspection/')) and name.endswith('.json'):
            row=data(name)
            if isinstance(row,dict) and row.get('command',[])[:2]==['docker','inspect'] and row['exit']==0:
                inspections+=json.loads(row['stdout'])
    terminal=[r for r in inspections if r['State']['Status']=='exited']
    require(terminal and all(r['Id']==handle['id'] and r['State']['ExitCode']==expected and not r['State']['OOMKilled'] for r in terminal),'Same-container terminal probe missing')
    console=files[base+'native/stdout.txt'].decode('utf-8')
    require('ICT_MAILBOX_FATAL ' not in console and 'Script Exception:' not in console,'Native transport probe failure')
    with tempfile.TemporaryDirectory(prefix='ict-wait22-probe-') as temp:
        root=Path(temp)
        for folder in FOLDERS:
            (root/folder).mkdir(parents=True);(root/'staging'/folder).mkdir(parents=True)
        for name,value in files.items():
            if name.startswith('attempt/mailbox/'):
                path=root/name[len('attempt/mailbox/'):];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        history=audit_history(root,console,config,process['engine_pid'])
    require(not history['failures'] and not history['sealed'] and len(history['stopped'])==1 and
            history['calls']==6 and history['replies']==2,'Waiting helper request/stop history differs')
    events=[data(f'attempt/mailbox/events/{i:08d}.json') for i in range(1,7)]
    require([r['result'].get('status') for r in events]==['initialized','request','published','request','published','stopped'],'Idle events or unexpected helper lifecycle')
    actions=data(base+'ui/actions.json');require([r['event'] for r in actions]==list(range(1,len(actions)+1)),'Probe action sequence differs')
    states=[r for r in actions if r['kind'].startswith('waiting_helper_')]
    require([r['kind'] for r in states]==['waiting_helper_before_ui','waiting_helper_after_text','waiting_helper_after_cancel'],'Live-helper UI coverage differs')
    helper=states[0]['helper']
    require(all(r['helper']==helper for r in states) and states[-1]['elapsed']>5 and
            states[-1]['at']-states[0]['at']>5 and helper['parent']==process['engine_pid'] and
            events[3]['result']['owner_pid']==helper['pid'],'Same live child during UI/request differs')
    require(json.loads(helper['arguments'][-1])['operation']=='poll' and
            json.loads(helper['arguments'][-1])['seq']==2,'Waiting helper actual arguments differ')
    typed=[r for r in actions if r['kind']=='command' and r.get('command',[])[:3]==['python3','/work/ui_control.py','type']]
    require(len(typed)==1 and typed[0]['exit']==0,'Single native filename dispatch missing')
    completion=json.loads(typed[0]['stdout'])
    require(completion['typed_text']=='/work/source.dxf' and completion['text_completion_observations'][-1]['text']=='/work/source.dxf','Native text completion differs')
    cancelled=[r for r in actions if r['kind']=='control' and r['operation']=='press' and r['observed']['name']=='Cancel']
    require(len(cancelled)==1 and not any(r['kind']=='returned_file' for r in actions),'Cancel/save probe coverage differs')
    observation=events[4]['result'];call=json.loads(events[4]['input_wire'])
    require(observation['status']=='published' and call['observation']['filename']=='' and call['observation']['modified'] is False,'Probe opened/modified a drawing')
    require(digest(files[base+'source.dxf'])==data(base+'job.json')['source_sha256'],'Probe source changed')
    if number==1:
        require(base+'ui/RESULT.json' not in files and 'dict() got multiple values for keyword argument' in data(base+'ui/FAILURE.json')['traceback'],'Original recorder failure omitted')
        cleanup=data(base+'native/CLEANUP.json')
        require(data('cleanup/EXIT.json')['exit']==0 and cleanup['native_pid']==process['engine_pid'] and
                cleanup['native_start_identity']==process['engine_start_identity'] and cleanup['live_helpers_before_close']==[] and cleanup['close_exit']==0,'Original failed probe cleanup differs')
        return dict(status='original-waiting-probe-recorder-failure-retained',helper_calls=6,requests=2,idle_events=0,whole_cad_qualified=False)
    require(base+'ui/FAILURE.json' not in files,'Successful probe contains failure')
    result=data(base+'ui/RESULT.json')
    received=[r for r in actions if r['kind']=='waiting_request_received'];stopped=[r for r in actions if r['kind']=='waiting_stop_published']
    require(result['status']=='waiting-helper-native-probe-complete' and result['same_waiting_helper']==helper and
            len(received)==len(stopped)==1 and equal(received[0]['helper_event'],events[3]) and
            stopped[0]['helper']['pid']==events[5]['result']['owner_pid'] and result['next_waiting_helper']==stopped[0]['helper'],'Complete waiting probe/request/cleanup binding differs')
    return dict(status='waiting-helper-native-probe-received',helper_calls=6,requests=2,idle_events=0,
                same_child_native_typing_cancel=True,idle_and_ui_seconds=states[-1]['elapsed'],whole_cad_qualified=False)


def package(attempt,execution,cleanup,out,identity,number):
    require(not out.exists(),'New probe packet destination required');files={}
    folders=[('attempt',attempt),('execution',execution)]
    if str(cleanup)!='-': folders.append(('cleanup',cleanup))
    for prefix,folder in folders:
        for path in folder.rglob('*'):
            if path.is_file(): files[prefix+'/'+path.relative_to(folder).as_posix()]=path.read_bytes()
    result=check_files(files,read(identity)[str(number)],number)
    require(len(files)<=MAX_FILES and sum(map(len,files.values()))<=MAX_RAW and max(map(len,files.values()))<=MAX_FILE,'Probe archive exceeds normal bounded retention')
    out.mkdir(parents=True);archive=out/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',preset=6) as target:
        for name,value in sorted(files.items()):
            member=tarfile.TarInfo(name);member.size=len(value);member.mode=0o644;member.mtime=0;target.addfile(member,io.BytesIO(value))
    for name,value in [('INVENTORY.json',dict(archive_sha256=sha(archive),files={n:dict(bytes=len(v),sha256=digest(v)) for n,v in sorted(files.items())})),('RESULT.json',result)]:
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('package')
    for name in ('attempt','execution','cleanup','out','identity'): a.add_argument(name,type=Path)
    a.add_argument('number',type=int);sub.add_parser('check');args=vars(p.parse_args());action=args.pop('action')
    if action=='package': print(json.dumps(package(**args),indent=2))
    else:
        results={};identity=read(HERE/'WAITING-PROBES-1.json')
        for number in (1,2):
            packet=HERE/f'waiting-probes/probe-{number}';result=check_files(unpack(packet),identity[str(number)],number)
            require(equal(result,read(packet/'RESULT.json')),'Published probe receipt differs');results[number]=result
        print(json.dumps(results,indent=2))
