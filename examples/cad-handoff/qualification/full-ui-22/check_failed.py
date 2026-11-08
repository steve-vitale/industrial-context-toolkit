"""Recheck original failed attempts and challenge failure/completion semantics offline."""
import copy
import json
from failed_receiving import HERE, audit, unpack, read, require, equal, digest


def controls(original, identity):
    outcomes=[]
    for control in ('changed-final-call','changed-final-error','hidden-controller-failure','invented-completion'):
        files=dict(original);pins=copy.deepcopy(identity)
        def replace(name,value):
            files[name]=value
            if name in pins['original_identity']: pins['original_identity'][name]=digest(value)
        if control in ('changed-final-call','changed-final-error'):
            name='attempt/mailbox-terminal/events/00004097.json';event=json.loads(files[name])
            if control=='changed-final-call':
                call=json.loads(event['input_wire']);call['call_id']=4098
                event['input_wire']=json.dumps(call,separators=(',',':'))
            else: event['result']['error']['stage']='read-open'
            replace(name,(json.dumps(event,separators=(',',':'))+'\n').encode('ascii'))
            files['attempt/mailbox-terminal/staging/events/00004097.json']=files[name]
        elif control=='hidden-controller-failure':
            name='attempt/job/native/PROCESS.json';value=json.loads(files[name]);value['controller_exit']=0
            replace(name,json.dumps(value).encode('ascii'))
        else: files['attempt/job/ui/RESULT.json']=b'{"status":"controller-complete"}\n'
        try: audit(files,pins)
        except ValueError as error: outcomes.append(dict(control=control,refused=True,reason=str(error)))
        else: raise AssertionError('Failed-attempt semantic control accepted: '+control)
    return outcomes


def check():
    results={}
    for case,label in [('CP1251','cp1251-receiving-1'),('BRACES','braces-receiving-1')]:
        packet=HERE/'failed-development-1'/label;identity=read(HERE/f'FAILED-{case}-1.json')
        files=unpack(packet);result=audit(files,identity)
        require(equal(result,read(packet/'RESULT.json')), 'Readable failed receipt differs')
        results[label]=dict(receipt=result,controls=controls(files,identity))
    return results


if __name__=='__main__': print(json.dumps(check(),indent=2))
