"""Receive full UI development evidence offline; each CAD preservation verdict stays separate."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / 'observer-transport-21'))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / 'scripts'))
from bridge_receive import audit_history
from mailbox import wire
from contract import group_native, verify_inventory, verify_selection
import cad_handoff as ch
from PIL import Image
sys.path.insert(0, str(HERE))


def require(ok, message):
    if not ok: raise ValueError(message)


def read(path): return json.loads(Path(path).read_bytes())
def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def equal(a, b):
    # Semantic JSON object order is immaterial; lists/types remain exact.
    # Exact transport wire/staging/publication bytes are checked separately.
    return json.dumps(a,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False) == json.dumps(b,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def walk(node):
    yield node
    for child in node.get('children', []): yield from walk(child)


def fields(tree):
    found = {}
    for node in walk(tree):
        children = node.get('children', [])
        if node.get('role') != 'panel' or not children or children[0].get('role') != 'label' or children[0].get('name') != 'Attributes': continue
        require(len(children) % 2 == 1, 'Incomplete native attribute panel')
        for label, value in zip(children[1::2], children[2::2]):
            require(label['role'] == 'label' and label['name'].endswith(':'), 'Missing native attribute label')
            tag = label['name'][:-1]
            require(tag not in found, 'Ambiguous native attribute field')
            found[tag] = value
    return found


def field_values(actual, expected):
    require(set(actual) == set(expected), 'Omitted/added native fields')
    for tag, value in expected.items():
        node = actual[tag]
        require(node.get('text') == value and all(node.get(k) is True for k in ('editable', 'enabled', 'showing')), 'Native displayed value/editability differs: ' + tag)


def text_trace(row, following):
    change, node = row['change'], row['observed']
    require(following['kind'] == 'command' and following['command'] == ['python3', '/work/ui_text.py', node['path'], change['before'], change['after']] and following['exit'] == 0, 'Native value dispatch differs')
    trace = json.loads(following['stdout'])
    require(trace.get('error') is None and trace['path'] == node['path'] and trace['name'] == node['name'] and trace['role'] == node['role'], 'Native value control binding differs')
    require(trace['before'] == trace['expected_before'] == node['text'] == change['before'] and trace['proposed'] == change['after'], 'Native value before/after differs')
    require(trace['focus_result'] is True and trace['editable_text_result'] is True and trace['tab_dispatched'] is True and trace['active_window'] == 'Property Editor', 'Native accessible edit/focus/commit failed')
    require(trace['rectangle'] == node['rectangle'], 'Native value field bounds differ')
    x, y, w, h = node['rectangle']
    require(min(x, y) >= 0 and min(w, h) > 0, 'Native value field bounds unavailable')
    commands = trace['commands']
    require([r['command'] for r in commands] == [
        ['xdotool', 'mousemove', '--sync', str(x + w // 2), str(y + h // 2), 'click', '1'],
        ['xdotool', 'getactivewindow', 'getwindowname'], ['xdotool', 'key', 'Tab']]
        and all(r['exit'] == 0 and r['stderr'] == '' for r in commands) and commands[1]['stdout'].strip() == 'Property Editor', 'Native value input command result differs')
    completion = trace['completion']
    require(completion and completion[-1]['text'] == change['after'] and
            [r['elapsed'] for r in completion] == sorted(r['elapsed'] for r in completion) and
            all(0 <= r['elapsed'] <= 3.05 for r in completion) and
            all(r['text'] != change['after'] for r in completion[:-1]), 'Native exact text completion differs')


def controls(actions, basis, role):
    for row in actions:
        if row['kind'] != 'control': continue
        node, operation = row['observed'], row['operation']
        require(node['enabled'] is True and node['showing'] is True, 'Native control hidden/disabled')
        following = actions[row['event']]
        command = ['python3', '/work/ui_control.py', operation, node['path']]
        if row['text'] is not None: command.append(row['text'])
        require(following['kind'] == 'command' and following['command'] == command and following['exit'] == 0, 'Native UI control dispatch differs')
        trace = json.loads(following['stdout'])
        require(all(trace[k] == v for k, v in dict(path=node['path'], operation=operation, name=node['name'], role=node['role']).items()), 'Native UI control observation differs')
        if operation == 'focus':
            require(trace['focus_result'] is True, 'Native canvas focus failed'); continue
        x, y, w, h = node['rectangle']
        require(trace['commands'][0]['command'] == ['xdotool', 'mousemove', '--sync', str(x+w//2), str(y+h//2), 'click', '1'] and all(r['exit'] == 0 for r in trace['commands']), 'Native observed-bounds click differs')
        if operation == 'press': require(trace['event_dispatched'] is True, 'Native button dispatch failed')
        else:
            require(operation == 'type' and trace['typed_text'] == row['text'] and trace['focus_result'] is True and trace['active_window']['exit'] == 0, 'Native file/handle typing failed')
            require(trace['text_completion_observations'][-1]['text'] == row['text'] and trace['commands'][-1]['command'] == ['xdotool', 'key', 'Tab'], 'Native file/handle exact completion/commit differs')
    opening = ['Escape', 'Escape', 'ctrl+o']; selection = ['Escape', 'Escape', 't', 'h']
    clear = ['Escape', 'Escape', 't', 'n']; close = ['Escape', 'Escape', 'ctrl+w']; save = ['Escape', 'Escape', 'ctrl+shift+s']
    bindings = [r for r in actions if r['kind'] == 'selection_binding']
    n = len(basis['assets']); expected_keys = []; expected_types = []; expected_buttons = ['OK']; i = 0
    def opened(path):
        expected_keys.append(opening); expected_types.append(path); expected_buttons.append('Open')
    def selected(count):
        nonlocal i
        for _ in range(count):
            require(i < len(bindings), 'Native selection omitted')
            expected_keys.extend([clear, selection]); expected_types.append(bindings[i]['observed_handle']); expected_buttons.append('OK'); i += 1
    if role == 'receiving':
        for name in ('source', 'baseline', 'edited', 'candidate'):
            opened('/work/' + name + '.dxf'); selected(n); expected_keys.extend([clear, close])
    else:
        opened('/work/source.dxf'); selected(n); expected_keys.append(clear)
        if role == 'edited': selected(len(basis['changes']))
        expected_keys.extend([save, close]); expected_types.append('/work/returned.dxf'); expected_buttons.append('Save')
        opened('/work/returned.dxf'); selected(n); expected_keys.extend([clear, close])
    require(i == len(bindings), 'Extra native selection')
    keys = [r['command'][3:] for r in actions if r['kind'] == 'command' and r['command'][:3] == ['xdotool', 'key', '--clearmodifiers']]
    require(keys == expected_keys, 'Native open/select/clear/save/close sequence differs')
    require([r['text'] for r in actions if r['kind'] == 'control' and r['operation'] == 'type'] == expected_types, 'Native file/handle input coverage differs')
    require([r['observed']['name'] for r in actions if r['kind'] == 'control' and r['operation'] == 'press'] == expected_buttons, 'Native button coverage differs')
    edits = [r for r in actions if r['kind'] == 'native_text_edit_requested']
    require([r['change'] for r in edits] == (basis['changes'] if role == 'edited' else []), 'Native planned edit coverage differs')
    for row in edits: text_trace(row, actions[row['event']])
    commands = [r for r in actions if r['kind'] == 'command']
    require(sum('/work/ui_text.py' in r['command'] for r in commands) == len(edits), 'Extra native value command')
    for row in commands:
        command = row['command']
        allowed = (command == ['ps', '-eo', 'pid,ppid,stat,etime,args'] or
                   command[:2] == ['python3', '/work/ui_control.py'] or command[:2] == ['python3', '/work/ui_text.py'] or
                   command[:3] == ['xdotool', 'key', '--clearmodifiers'] or command == ['xdotool', 'mousemove', '--sync', '2300', '1300'] or
                   (len(command) == 2 and command[0] == 'scrot' and command[1].startswith('/work/ui/')) or
                   command == ['wmctrl', '-l'] or (len(command) == 3 and command[:2] == ['wmctrl', '-ic']))
        require(allowed and row['exit'] == 0, 'Unexpected/failed native UI command')


def observations(actions, basis, role, ui):
    before = {a['id']: copy.deepcopy(a['attributes']) for a in basis['assets']}; current = copy.deepcopy(before); after = copy.deepcopy(before)
    for change in basis['changes']: after[change['id']][change['attribute']] = change['after']
    last = None; selected = []; field_rows = []; pending = None; commits = []; observed = []
    for row in actions:
        kind = row['kind']
        if kind == 'native_observation':
            last = row['reply']; observed.append(last)
            require(last['qt'] == '5.14.2' and last['configuration_file'] == '/home/cad/.config/QCAD/QCAD3.conf', 'Native observation environment differs')
            path = last['filename']
            if path == '':
                require(last['attributes'] == [] and last['selected'] == [] and last['modified'] is False, 'Untitled native document changed'); continue
            require(path in ['/work/'+n+'.dxf' for n in ('source','returned','baseline','edited','candidate')], 'Unexpected native drawing')
            if role == 'receiving':
                require(path != '/work/returned.dxf' and last['modified'] is False, 'Receiver modified drawing')
                expected = after if path in ('/work/edited.dxf','/work/candidate.dxf') else before
            elif path == '/work/source.dxf': expected = current
            else:
                require(path == '/work/returned.dxf' and last['modified'] is False, 'Native returned document state differs')
                expected = after if role == 'edited' else before
            verify_inventory(last, expected)
            if role == 'baseline': require(last['modified'] is False, 'No-edit native process modified source')
        elif kind == 'command' and '/work/ui_text.py' in row['command']:
            require(pending is not None and row['exit'] == 0, 'Unbound native value edit')
            current[pending['id']][pending['attribute']] = pending['after']
        elif kind == 'complete_native_inventory':
            require(last is not None and equal(row['observation'], last) and row['path'] == last['filename'], 'Native inventory not bound to latest observation')
            require(equal(row['expected'], {k:v['attributes'] for k,v in verify_inventory(last, row['expected']).items()}), 'Native recorded expectation differs')
        elif kind == 'selection_binding':
            identity = row['identity']; groups = group_native(last)
            asset = next((a for a in basis['assets'] if a['id'] == identity), None)
            require(asset is not None and row['asset_id'] == identity and row['source_handle'] == asset['handle'] and row['observed_handle'] == groups[identity]['handle'], 'Native selection identity/handle differs')
            if last['filename'] in ('/work/source.dxf','/work/candidate.dxf'): require(row['observed_handle'] == asset['handle'], 'Original source handle changed')
            selected.append((last['filename'], identity))
        elif kind == 'exact_asset_selected':
            group = group_native(last)[row['asset_id']]
            require(selected and selected[-1] == (last['filename'],row['asset_id']) and equal(row['group'], group) and row['selected'] == last['selected'] and row['path'] == last['filename'], 'Exact selection binding differs')
            verify_selection(last, group)
        elif kind == 'native_fields':
            identity = row['asset_id']; path = last['filename']
            expected = (after if path in ('/work/edited.dxf','/work/candidate.dxf') else before) if role == 'receiving' else (current if path == '/work/source.dxf' else after if role == 'edited' else before)
            require(equal(row['expected'], expected[identity]), 'Native field expectation metadata differs')
            field_values(row['observed'], expected[identity]); field_rows.append(row)
        elif kind == 'native_text_edit_requested':
            change = row['change']; identity = change['id']
            require(pending is None and row['asset_id'] == identity and row['path'] == '/work/source.dxf' and current[identity][change['attribute']] == change['before'], 'Native edit source/state differs')
            require(field_rows and field_rows[-1]['asset_id'] == identity and equal(row['observed'], field_rows[-1]['observed'][change['attribute']]), 'Native edit targets wrong field')
            verify_selection(last, group_native(last)[identity]); pending = change
        elif kind == 'native_text_edit_committed':
            require(pending == row['change'] and equal(row['observation'], last) and last['modified'] is True, 'Native commit observation differs')
            verify_inventory(last, current); commits.append(pending); pending = None
    require(pending is None and commits == (basis['changes'] if role == 'edited' else []), 'Incomplete native edit commits')
    ids = [a['id'] for a in basis['assets']]
    expected_selected = ([(f'/work/{name}.dxf', i) for name in ('source','baseline','edited','candidate') for i in ids] if role == 'receiving' else
                         [('/work/source.dxf', i) for i in ids] + ([('/work/source.dxf', c['id']) for c in basis['changes']] if role == 'edited' else []) + [('/work/returned.dxf', i) for i in ids])
    require(selected == expected_selected, 'Native multi-asset selection coverage differs')
    require([r['asset_id'] for r in actions if r['kind'] == 'exact_asset_selected'] == [identity for _,identity in expected_selected], 'Native exact-selection coverage differs')
    expected_fields = (len(basis['assets']) * (4 if role == 'receiving' else 2) + (2*len(basis['changes']) if role == 'edited' else 0))
    require(len(field_rows) == expected_fields, 'Native editable-field phase coverage differs')
    trees = sorted(p for p in ui.glob('*.json') if p.name.endswith('-selected.json') or re.search(r'-edit-\d+\.json$', p.name))
    require(len(trees) == len(field_rows), 'Native field snapshot coverage differs')
    for tree, row in zip(trees, field_rows): require(equal(fields(read(tree)), row['observed']), 'Native fields differ from captured accessibility tree')
    return observed, dict(before=before, after=after, editable_field_checks=len(field_rows), committed_edits=len(commits))


def captures(actions, basis, role, job, observed):
    rows = [r for r in actions if r['kind'] == 'capture']; images = set()
    labels = ('source','baseline','edited','candidate') if role == 'receiving' else ('source','returned')
    require([(r['label'],r['frame']) for r in rows] == [(label,frame) for label in labels for frame in basis['frames']], 'Native capture coverage differs')
    for row in rows:
        obs = row['observation']; frame = basis['frames'][row['frame']]
        require(any(equal(obs, other) for other in observed), 'Native capture observation missing')
        require(obs['filename'] == '/work/'+row['label']+'.dxf' and obs['request']['frame'] == frame and obs['request']['expected_path'] == obs['filename'] and not obs['selected'], 'Native capture source/frame/selection differs')
        view, control = obs['view'], obs['camera_control']; margin = 48 if control['high_resolution'] else 24
        factor = min((view['width']-2*margin)/(frame[2]-frame[0]), (view['height']-2*margin)/(frame[3]-frame[1]))
        offset = [view['width']/(2*factor)-(frame[0]+frame[2])/2, view['height']/(2*factor)-(frame[1]+frame[3])/2]
        require(control['factor'] == view['factor'] == factor and control['offset'] == view['offset'] == offset and control['margin'] == margin and [control['width'],control['height']] == [view['width'],view['height']], 'Exact absolute camera formula differs')
        canvas = row['canvas']; x,y,w,h = canvas['rectangle']
        require(canvas['enabled'] is True and canvas['showing'] is True and canvas['name'] == 'Drawing View' and [w,h] == [view['width'],view['height']] and min(x,y) >= 0 and min(w,h) > 0, 'Native capture canvas differs')
        require(2 <= len(row['images']) <= 10 and row['images'][-1]['pixel_sha256'] == row['images'][-2]['pixel_sha256'], 'Native canvas did not stabilize')
        for i, image in enumerate(row['images']):
            name = row['label']+'-'+row['frame']+'-'+str(i)+'.png'
            require(image['path'] == name and name not in images, 'Native capture image name/reuse differs')
            cropname = Path(name).with_suffix('.canvas.png').name; images.update((name,cropname))
            with Image.open(job/'ui'/name) as full, Image.open(job/'ui'/cropname) as crop:
                require(full.size == (2400,1400) and full.mode == crop.mode == 'RGB' and crop.size == (w,h), 'Native screenshot dimensions/mode differ')
                require(full.crop((x,y,x+w,y+h)).tobytes() == crop.tobytes() and digest(crop.tobytes()) == image['pixel_sha256'], 'Native screenshot crop/pixel digest differs')
    require({p.name for p in (job/'ui').glob('*.png')} == images, 'Native screenshot omitted/extra')
    return dict(views=len(rows), images=len(images))


def receive(root, preparation, methods):
    root = Path(root); job = root/'job'; methods = read(methods); preparation = read(preparation)
    inventory = read(root/'INVENTORY.json')
    actual = {p.relative_to(root).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in root.rglob('*') if p.is_file() and p != root/'INVENTORY.json'}
    require(actual == inventory['files'], 'Complete attempt inventory differs')
    basis = read(job/'job.json'); role = basis.pop('role')
    require(role in ('baseline','edited','receiving') and role == inventory['role'], 'Native role differs')
    prepared = preparation['cases'].get(basis['case'])
    require(prepared is not None and equal(prepared['basis'],basis), 'External prepared basis differs')
    frozen = read(job/'JOB-FREEZE.json')
    require(frozen['producer_sha256'] == preparation['preparation']['producer_sha256'] == methods['files']['examples/cad-handoff/qualification/full-ui-22/prepare.py'], 'Frozen staging producer differs')
    for name,pin in frozen['files'].items():
        require((job/name).resolve().is_relative_to(job.resolve()) and sha(job/name) == pin, 'Frozen job input changed: '+name)
    staged = {'original_workflow.py':'native-ui-pairs-19/workflow.py', 'inspect_ui.py':'native-ui-pairs-19/inspect_ui.py', 'native_controls.py':'native-ui-pairs-19/native_controls.py',
              'ui_control.py':'observer-transport-21/bridge_ui_control.py', 'ui_settle.py':'observer-transport-21/ui_settle.py', 'bridge_workflow.py':'observer-transport-21/bridge_workflow.py',
              'mailbox.py':'observer-transport-21/mailbox.py','native_io.py':'observer-transport-21/native_io.py','observe_case.js':'observer-transport-21/async_bridge_observer.js','launch_case.py':'observer-transport-21/bridge_launch.py','BRIDGE-PROTOCOL.md':'observer-transport-21/BRIDGE-PROTOCOL.md'}
    staged.update({n:'full-ui-22/'+n for n in ('workflow.py','contract.py','ui_text.py','payload.js','PLAN.md','METHOD.md')})
    expected_files = set(staged)|{'job.json','source.dxf','plan.json','transport.json','.configuration/QCAD3.conf'}
    if role == 'receiving': expected_files |= {'baseline.dxf','edited.dxf','candidate.dxf'}
    require(set(frozen['files']) == expected_files, 'Frozen job input coverage differs')
    for target,source in staged.items(): require(frozen['files'][target] == methods['files']['examples/cad-handoff/qualification/'+source], 'Prospective method pin differs: '+target)
    require(sha(job/'source.dxf') == basis['source_sha256'] and sha(job/'plan.json') == basis['plan_sha256'] and frozen['files']['.configuration/QCAD3.conf'] == preparation['configuration_sha256'], 'Source/plan/configuration basis differs')
    source = ch.snapshot(job/'source.dxf'); plan = read(job/'plan.json'); ch.validate_plan(source,plan)
    require(equal(source['assets'],basis['assets']) and plan['changes'] == basis['changes'], 'Prepared assets/plan differ from original DXF')
    process = read(job/'native/PROCESS.json'); config = read(job/'transport.json'); handle = read(root/'host/HANDLE.json')
    require(process['exit'] == process['controller_exit'] == 0 and process['configuration_before'] == preparation['configuration_sha256'] and equal(process['job'],dict(basis,role=role)), 'Native process/controller/configuration differs')
    require(process['command'] == ['/opt/qcad/qcad','-allow-multiple-instances','-config','/home/cad/.config/QCAD/QCAD3.conf','-font-substitution','Standard','DejaVu Sans','-exec','/work/observe_case.js'] and isinstance(process['engine_pid'],int) and process['engine_pid'] != process['pid'] and process['engine_start_identity'].isdigit(), 'Actual native Qt child/command differs')
    require(handle['image'] == methods['image'] and config['profile'] == 'normal' and config['protocol'] == 'ict-native-mailbox/1' and config['io_protocol'] == 'ict-native-io/1', 'Image/transport profile differs')
    commands = [read(p) for p in sorted((root/'host').glob('0*.json'))]
    inspections = [json.loads(r['stdout'])[0] for r in commands if r['command'][:2] == ['docker','inspect'] and r['exit'] == 0]
    require(inspections and inspections[-1]['Id'] == handle['id'] and inspections[-1]['State'] == inventory['native_container_state'] and inspections[-1]['State']['Status'] == 'exited' and inspections[-1]['State']['ExitCode'] == 0 and not inspections[-1]['State']['OOMKilled'], 'Same-container native terminal state differs')
    environment = inspections[-1]
    require(environment['Config']['Image'] == methods['image'] and environment['Config']['User'] == '1001:1001' and environment['HostConfig']['NetworkMode'] == 'none' and environment['HostConfig']['CapDrop'] == ['ALL'] and environment['HostConfig']['SecurityOpt'] == ['no-new-privileges'], 'Actual native isolation differs')
    require(all(environment['HostConfig'][key] == value for key,value in dict(Memory=3*1024**3,NanoCpus=2000000000,ShmSize=256*1024**2,PidsLimit=256).items()) and environment['Path'] == 'dbus-run-session' and environment['Args'] == ['--','python3','/work/launch_case.py'] and len(environment['Mounts']) == 1 and environment['Mounts'][0]['Type'] == 'bind' and environment['Mounts'][0]['Destination'] == '/work', 'Native resources/entry point/mount differ')
    require(len([r for r in commands if r['command'][:3] == ['docker','run','-d']]) == 1, 'Repeated native launch')
    stdout = (job/'native/stdout.txt').read_text(encoding='utf-8'); stderr = (job/'native/stderr.txt').read_text(encoding='utf-8')
    require(not any(s in stdout+stderr for s in ('Script Exception:','ICT_MAILBOX_FATAL ')), 'Native script failure retained')
    history = audit_history(root/'mailbox',stdout,config,process['engine_pid'])
    require(not history['failures'] and not history['stopped'] and history['sealed'] == [dict(run_id=config['run_id'],seq=history['replies'],call_id=history['calls'])], 'Complete normal transport seal/history differs')
    actions = read(job/'ui/actions.json')
    require([r['event'] for r in actions] == list(range(1,len(actions)+1)) and [r['at'] for r in actions] == sorted(r['at'] for r in actions), 'Client action history missing/reordered')
    requests = [r for r in actions if r['kind'] == 'mailbox_request']; replies = [r for r in actions if r['kind'] == 'mailbox_reply']; native = [r for r in actions if r['kind'] == 'native_observation']
    ids = list(range(1,history['replies']+1))
    require([r['seq'] for r in requests] == [r['seq'] for r in replies] == ids and len(native) == len(ids), 'Client/native observation coverage differs')
    for req,rep,obs in zip(requests,replies,native):
        name = f"{req['seq']:08d}.json"; data = (root/'mailbox/requests'/name).read_bytes(); raw = (root/'mailbox/replies'/name).read_bytes()
        require(req['wire'] == data.decode('ascii') and req['sha256'] == digest(data) and rep['sha256'] == digest(raw) and rep['reply'] == json.loads(raw) and equal(rep['reply']['observation'],obs['reply']), 'Exact client/native wire/observation binding differs')
    names = set(history['completed_request_hashes'])
    for folder in ('requests','replies','staging/requests','staging/replies'): require({p.name for p in (root/'mailbox'/folder).iterdir()} == names, 'Normal message inventory differs')
    for folder in ('controls','staging/controls','errors','staging/errors'): require(not list((root/'mailbox'/folder).iterdir()), 'Unexpected normal cleanup/error records')
    require(read(root/'mailbox/requests'/f"{history['replies']:08d}.json")['body'] == dict(action='seal'), 'Final native seal missing')
    require(read(job/'ui/RESULT.json') == dict(status='controller-complete',role=role,case=basis['case'],native_ui_only_for_document_actions=True,whole_cad_qualified=False) and not (job/'ui/FAILURE.json').exists(), 'Complete normal UI result missing/failed')
    controls(actions,basis,role)
    observed, state = observations(actions,basis,role,job/'ui'); image_result = captures(actions,basis,role,job,observed)
    saved = [r for r in actions if r['kind'] == 'returned_file']; comparisons = {}
    require(len(saved) == (0 if role == 'receiving' else 1), 'Native returned-file coverage differs')
    if saved:
        require(saved[0]['path'] == '/work/returned.dxf' and saved[0]['sha256'] == sha(job/'returned.dxf'), 'Retained native return changed')
        document = ch.load(job/'returned.dxf'); require(document.dxfversion == 'AC1027', 'Native Save As format differs')
        returned = ch.assets(document); require({a['id']:a['attributes'] for a in returned} == state['after' if role == 'edited' else 'before'] and len(returned) == len(basis['assets']), 'Returned DXF asset/foreign values differ')
        comparison = ch.compare(source,ch.snapshot(job/'returned.dxf'),plan if role == 'edited' else None)
        comparisons = dict(unexpected=len(comparison['unexpected']),status=comparison['status'],report=comparison)
    return dict(status='full-ui-development-packet-received',case=basis['case'],role=role,helper_calls=history['calls'],observations=len(observed),
                editable_field_checks=state['editable_field_checks'],committed_edits=state['committed_edits'],**image_result,
                native_strict=comparisons,paper_visual_review='unfinished',revision_checks='unfinished',whole_cad_qualified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('packet',type=Path); parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--preparation',type=Path,default=HERE/'PREPARATION-1.json'); parser.add_argument('--methods',type=Path,default=HERE/'METHODS-1.json'); args = parser.parse_args()
    require(not args.out.exists(), 'New receipt destination required')
    result = receive(args.packet,args.preparation,args.methods); args.out.write_bytes(wire(result)); print(json.dumps(result,indent=2))
