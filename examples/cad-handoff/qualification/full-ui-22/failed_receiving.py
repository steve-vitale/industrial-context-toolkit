"""Retain a failed call-boundary attempt, without issuing a normal CAD receipt."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

from receive import HERE, read, require, sha, digest, equal, audit_history
from bridge_receive import records
from mailbox import wire
from native_io import FOLDERS

MAX_FILE, MAX_RAW, MAX_FILES = 32*1024**2, 192*1024**2, 16000


def audit(files, identity):
    for name, pin in identity['original_identity'].items():
        require(name in files and digest(files[name]) == pin, 'Original failed-attempt identity differs: '+name)
    def data(name): return json.loads(files[name])
    base = 'attempt/job/'
    freeze = data(base+'JOB-FREEZE.json')
    require(freeze == identity['freeze'], 'Original failed job freeze differs')
    for name, pin in freeze['files'].items():
        require(digest(files[base+name]) == pin, 'Frozen failed input/method changed: '+name)
    process = data(base+'native/PROCESS.json'); config = data(base+'transport.json')
    handle = data('attempt/host/HANDLE.json')
    inspection = json.loads(files['attempt/failure-inspection/4-stdout.txt'])[0]
    state = inspection['State']; cleanup = data(base+'native/CLEANUP.json')
    require(data('execution/EXIT.json')['exit'] == 1 and process['controller_exit'] == 1 and
            process['exit'] == 0 and state['Status'] == 'exited' and state['ExitCode'] == 1 and
            not state['OOMKilled'] and inspection['Id'] == handle['id'], 'Actual failed/cleanup outcomes differ')
    require(handle['image'] == read(HERE/'METHODS-1.json')['image'], 'Original failure image differs')
    require(data('cleanup/EXIT.json')['exit'] == 0 and cleanup['native_pid'] == process['engine_pid'] and
            cleanup['native_start_identity'] == process['engine_start_identity'] and
            cleanup['live_helpers_before_close'] == [] and cleanup['close_exit'] == 0, 'Same-process cleanup differs')
    require(digest(files['cleanup/cleanup.py']) == data('cleanup/FREEZE.json')['source_sha256'] and
            digest(files['methods/FAILED-RECEIVING-PLAN.md']) == data('cleanup/FREEZE.json')['plan_sha256'], 'Separate cleanup freeze differs')
    require(base+'ui/RESULT.json' not in files and base+'ui/FAILURE.json' in files, 'Failure hidden by completion')
    console = files[base+'native/stdout.txt'].decode('utf-8')
    starts, ends = records(console, 'ICT_IO_START '), records(console, 'ICT_IO_END ')
    require(len(starts) == len(ends) == 4097 and starts[-1]['call_id'] == ends[-1]['call_id'] == 4097, 'Complete call boundary missing')
    require(not records(console, 'ICT_IO_SEALED ') and len(records(console, 'ICT_MAILBOX_FATAL ')) == 1, 'Native failure/seal differs')
    prefix = 'attempt/mailbox-terminal/'
    expected_events = {f'{i:08d}.json' for i in range(1,4098)}
    for folder in ('events','staging/events'):
        require({n[len(prefix+folder+'/'):] for n in files if n.startswith(prefix+folder+'/')} == expected_events, 'Complete failed event inventory differs')
    final_name = '00004097.json'; raw = files[prefix+'events/'+final_name]; event = json.loads(raw)
    require(files[prefix+'staging/events/'+final_name] == raw and event['input_wire'] == starts[-1]['input_wire'] and
            event['previous_event_sha256'] is None, 'Original admission event/wire differs')
    call, result = json.loads(event['input_wire']), event['result']; response = json.loads(ends[-1]['stdout'])
    require(call['call_id'] == 4097 and call['operation'] == 'poll' and call['run_id'] == config['run_id'] and
            call['io_protocol'] == config['io_protocol'], 'Last rejected call differs')
    require(response.pop('event_name') == final_name and response.pop('event_sha256') == digest(raw) and
            equal(response,result), 'Last native response/event binding differs')
    require(result['ok'] is False and result['call_id'] is None and result['run_id'] is None and
            result['qt_parent_pid'] == process['engine_pid'] and result['uid'] == 1001 and
            isinstance(result['owner_pid'],int) and ends[-1]['exit'] == 1 and
            ends[-1]['exit_status'] == 0 and ends[-1]['stderr'] == '', 'Original admission identity/terminal differs')
    error = dict(owner='python-io',exception='ValueError',errno=None,message='Invalid invocation identity',
                 stage='admission',path=None,seq=call['seq'],request_wire=None)
    require(result['error'] == error and set(result) == {'io_protocol','ok','call_id','run_id','owner_pid','qt_parent_pid','uid','error'}, 'Original admission error differs')
    expected_error = dict(io_protocol=config['io_protocol'],run_id=None,error_id=4097,**error)
    for folder in ('errors','staging/errors'):
        require({n[len(prefix+folder+'/'):] for n in files if n.startswith(prefix+folder+'/')} == {final_name}, 'Original error inventory differs')
        require(files[prefix+folder+'/'+final_name] == wire(expected_error), 'Original published/staged error differs')
    require(data(prefix+'controls/stop.json') == cleanup['stop_marker'], 'Terminal stop marker differs')
    # Explicit prefix view only: full originals remain retained and checked above.
    with tempfile.TemporaryDirectory(prefix='ict-ui22-failed-prefix-') as temporary:
        root = Path(temporary)
        for folder in FOLDERS:
            (root/folder).mkdir(parents=True); (root/'staging'/folder).mkdir(parents=True)
        for name, value in files.items():
            if not name.startswith(prefix): continue
            relative = name[len(prefix):]
            if relative in ('events/'+final_name,'staging/events/'+final_name,'errors/'+final_name,'staging/errors/'+final_name): continue
            path = root/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(value)
        lines = []
        for line in console.splitlines():
            if line.startswith(('ICT_IO_START ','ICT_IO_END ')) and json.loads(line.split(' ',1)[1])['call_id'] == 4097: continue
            lines.append(line)
        history = audit_history(root,'\n'.join(lines),config,process['engine_pid'])
    require(history['calls'] == 4096 and not history['failures'] and not history['sealed'] and
            call['seen'] == history['completed_request_hashes'] and call['seq'] == history['replies']+1, 'Successful prefix/last seen binding differs')
    # The pre-cleanup snapshot must contain the same original messages/events.
    for name, value in files.items():
        if name.startswith('attempt/mailbox-failed/'):
            require(files.get(prefix+name[len('attempt/mailbox-failed/'):]) == value, 'Cleanup changed original mailbox evidence')
    actions = data(base+'ui/actions.json')
    require([r['event'] for r in actions] == list(range(1,len(actions)+1)) and actions[-1]['kind'] == 'mailbox_failure', 'Client refusal/action sequence differs')
    requests = [r for r in actions if r['kind'] == 'mailbox_request']
    require([r['seq'] for r in requests] == list(range(1,call['seq']+1)), 'Client request coverage differs')
    for row in requests:
        slot = f"{row['seq']:08d}.json"; request = files[prefix+'requests/'+slot]
        require(request == files[prefix+'staging/requests/'+slot] and row['wire'].encode('ascii') == request and row['sha256'] == digest(request), 'Client actual request bytes differ')
    require('Native error journal retained' in files[base+'ui/FAILURE.json'].decode('utf-8'), 'Original client refusal missing')
    counts = Counter(json.loads(files[prefix+f'events/{i:08d}.json'])['result'].get('status','failed') for i in range(1,4098))
    views = [r for r in actions if r['kind'] == 'capture']
    return dict(status='failed-receiving-attempt-retained',case=data(base+'job.json')['case'],helper_calls=4097,
                successful_prefix_calls=4096,completed_requests=history['replies'],call_status_counts=dict(counts),
                captured_views=len(views),last_rejected_sequence=call['seq'],native_cleanup_exit=0,
                original_controller_exit=1,original_host_exit=1,normal_receiving_complete=False,whole_cad_qualified=False)


def unpack(packet):
    index=read(packet/'INVENTORY.json'); archive=(packet/'evidence.tar.xz').read_bytes()
    require(digest(archive) == index['archive_sha256'] and 0 < len(index['files']) <= MAX_FILES and
            sum(r['bytes'] for r in index['files'].values()) <= MAX_RAW, 'Failed archive bounds/hash differ')
    files={}; total=0
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:xz') as source:
        for member in source:
            path=PurePosixPath(member.name)
            require(member.isfile() and not path.is_absolute() and '..' not in path.parts and ':' not in member.name and
                    '\\' not in member.name and path.as_posix() == member.name and member.name not in files and member.name in index['files'], 'Unsafe/unregistered failed archive member')
            require(0 <= member.size <= MAX_FILE and member.size == index['files'][member.name]['bytes'], 'Failed archive member size differs')
            total+=member.size; require(total <= MAX_RAW and len(files)<MAX_FILES, 'Failed archive exceeds bounds')
            value=source.extractfile(member).read(member.size+1)
            require(len(value)==member.size and digest(value)==index['files'][member.name]['sha256'], 'Failed archive member hash differs')
            files[member.name]=value
    require(set(files)==set(index['files']), 'Failed archive member omitted')
    return files


def package(attempt, execution, cleanup, out, identity):
    require(not out.exists(), 'New failed packet destination required')
    files={}
    for prefix,folder in [('attempt',attempt),('execution',execution),('cleanup',cleanup)]:
        for path in folder.rglob('*'):
            if path.is_file(): files[prefix+'/'+path.relative_to(folder).as_posix()]=path.read_bytes()
    for name in ('FAILED-RECEIVING-PLAN.md','FAILURE-ARCHIVE-PLAN.md','failed_receiving.py'):
        files['methods/'+name]=(HERE/name).read_bytes()
    require(0 < len(files)<=MAX_FILES and sum(map(len,files.values()))<=MAX_RAW and max(map(len,files.values()))<=MAX_FILE, 'Failure package exceeds declared bounds')
    result=audit(files,read(identity)); out.mkdir(parents=True)
    archive=out/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',preset=6) as target:
        for name,value in sorted(files.items()):
            member=tarfile.TarInfo(name); member.size=len(value);member.mode=0o644;member.mtime=0
            target.addfile(member,io.BytesIO(value))
    for name,value in [('INVENTORY.json',dict(archive_sha256=sha(archive),files={n:dict(bytes=len(v),sha256=digest(v)) for n,v in sorted(files.items())})),('RESULT.json',result)]:
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('package')
    for name in ('attempt','execution','cleanup','out','identity'): a.add_argument(name,type=Path)
    a=sub.add_parser('check');a.add_argument('packet',type=Path);a.add_argument('identity',type=Path)
    args=vars(p.parse_args());action=args.pop('action')
    if action=='package': result=package(**args)
    else:
        result=audit(unpack(args['packet']),read(args['identity']))
        require(equal(result,read(args['packet']/'RESULT.json')), 'Published failed receipt differs')
    print(json.dumps(result,indent=2))
