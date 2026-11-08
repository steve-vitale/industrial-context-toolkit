"""Replay installed asynchronous capability evidence, preserving the failed predecessor."""
import json
from recheck_evidence import HERE, IMAGE, digest, require, unpack


def check_files(files, number):
    def read(name): return json.loads(files['attempt/' + name])
    frozen = json.loads((HERE / 'ASYNC-FROZEN-INPUTS.json').read_bytes())[f'async-probe-{number}']
    freeze = read('job/JOB-FREEZE.json')
    require(freeze == frozen, 'Original probe freeze differs')
    for name, pin in frozen['files'].items():
        require(digest(files['attempt/job/' + name]) == pin, 'Frozen probe source/input differs: ' + name)
    methods = json.loads((HERE / f'ASYNC-METHODS-{number}.json').read_bytes())
    require(freeze['stage_sha256'] == methods['files']['stage.py'], 'Prospective stage method differs')
    for source, target in [('async_probe.js', 'observe_case.js'), ('async_workflow.py', 'workflow.py'),
                           ('bridge_launch.py', 'launch_case.py'), ('bridge_ui_control.py', 'ui_control.py'),
                           ('ui_settle.py', 'ui_settle.py'), ('async_helper.py', 'async_helper.py'), ('ASYNC-PLAN.md', 'ASYNC-PLAN.md')]:
        require(freeze['files'][target] == methods['files'][source], 'Prospective probe method differs: ' + source)
    inner = read('INVENTORY.json')
    actual = {n.removeprefix('attempt/'): dict(bytes=len(v), sha256=digest(v)) for n, v in files.items()
              if n != 'attempt/INVENTORY.json'}
    require(inner['files'] == actual and inner['whole_cad_qualified'] is False, 'Complete probe inventory differs')
    handle = read('host/HANDLE.json'); process = read('job/native/PROCESS.json')
    receipts = [read(n.removeprefix('attempt/')) for n in files if n.startswith(('attempt/host/', 'attempt/inspection/')) and n.endswith('.json')]
    terminals = [json.loads(r['stdout'])[0] for r in receipts if isinstance(r, dict) and r.get('command', [])[:2] == ['docker', 'inspect'] and
                 r.get('exit') == 0 and json.loads(r['stdout'])[0]['State']['Status'] == 'exited']
    expected = 1 if number == 1 else 0
    require(handle['image'] == IMAGE and terminals and all(r['Id'] == handle['id'] and r['State']['ExitCode'] == expected for r in terminals), 'Original native terminal/handle differs')
    require(process['controller_exit'] == expected and process['exit'] == 0 and read('host-run/EXIT.json')['exit'] == expected and
            process['configuration_before'] == freeze['files']['.configuration/QCAD3.conf'], 'Original probe process/configuration differs')
    require(terminals[-1]['State'] == inner['native_container_state'], 'Terminal/inventory differs')
    actions = read('job/ui/actions.json')
    require([r['event'] for r in actions] == list(range(1, len(actions) + 1)), 'Probe action history differs')
    console = files['attempt/job/native/stdout.txt'].decode('utf-8')
    require('Script Exception:' not in console, 'Unhandled native probe exception')
    if number == 1:
        error = read('job/native/ASYNC-FAILURE.json')
        require(error['started'] is False and error['terminal'] is False and
                'ambiguous connect' in error['error'] and 'finished(int,QProcess::ExitStatus)' in error['error'] and
                'ICT_ASYNC_FAILURE ' + error['error'] in console and 'ICT_ASYNC_STARTED' not in console, 'Original signal failure missing')
        require('attempt/job/native/ASYNC-HELPER-READY.json' not in files and 'attempt/job/ui/FAILURE.json' in files, 'Failed probe incorrectly promoted')
        cleanup = read('inspection/cleanup.json')
        require(cleanup['exit'] == 0 and cleanup['command'][-1].encode('utf-8') == files['attempt/inspection/async_cleanup.py'], 'Separate cleanup source/action differs')
        require(read('job/async-separate-cleanup/RESULT.json')['original_controller_exit'] == 1, 'Original failure lost during cleanup')
        return dict(status='original-ambiguous-signal-failure-retained', whole_cad_qualified=False)
    require('ICT_ASYNC_FAILURE ' not in console and 'attempt/job/ui/FAILURE.json' not in files, 'Successful probe retains a failure')
    report = read('job/native/ASYNC.json')
    require(report == read('job/ui/RESULT.json')['report'], 'Native/client report differs')
    published = [json.loads(line[len('ICT_ASYNC_FINISHED '):]) for line in console.splitlines() if line.startswith('ICT_ASYNC_FINISHED ')]
    require(published == [report] and console.count('ICT_ASYNC_STARTED') == 1, 'Actual native start/finish report differs')
    helper = read('job/native/ASYNC-HELPER-READY.json')
    require(helper['uid'] == 1001 and helper['qt_parent_pid'] == process['engine_pid'] and
            json.loads(report['stdout']) == dict(helper, value='\u00b5 valve') and report['stderr'] == 'async probe stderr\n', 'Actual owner/UTF-8 output differs')
    require(report['qt'] == '5.14.2' and report['started'] is True and report['exit'] == report['exit_status'] == 0 and
            report['filename'] == '' and report['modified'] is False and report['ticks_at_finish'] - report['ticks_at_start'] >= 20, 'Native scheduling/unnamed document differs')
    events = [r['kind'] for r in actions if r['kind'].startswith('async_')]
    require(events == ['async_helper_live_before_ui', 'async_helper_live_after_text', 'async_helper_live_after_cancel', 'async_release', 'async_probe'], 'Live-helper/UI/release ordering differs')
    for row in actions:
        if row['kind'].startswith('async_helper_live_'): require(row['helper'] == helper, 'Same helper identity lost')
    require(read('job/native/ASYNC-RELEASE.json') == dict(helper=helper), 'Release identity differs')
    types = [r for r in actions if r['kind'] == 'control' and r['operation'] == 'type']
    require(len(types) == 1 and types[0]['text'] == '/work/source.dxf' and types[0]['observed']['name'] == 'File name:', 'Single filename dispatch differs')
    typed = [json.loads(r['stdout']) for r in actions if r['kind'] == 'command' and r.get('command', [])[:3] == ['python3', '/work/ui_control.py', 'type']]
    require(len(typed) == 1 and typed[0]['typed_text'] == '/work/source.dxf' and
            typed[0]['text_completion_observations'][-1]['text'] == '/work/source.dxf', 'Exact bounded text observation missing')
    require(sum(r['command'][:2] == ['xdotool', 'type'] for r in typed[0]['commands']) == 1, 'Filename was retyped')
    require(not any(r['kind'] == 'command' and r.get('exit') != 0 for r in actions), 'Probe UI command failed')
    require(not any(r['kind'] == 'returned_file' for r in actions), 'Probe unexpectedly saved CAD')
    return dict(status='asynchronous-helper-and-ui-observed', native_timer_ticks=report['ticks_at_finish'] - report['ticks_at_start'],
                single_filename_dispatch=True, whole_cad_qualified=False)


def check():
    results = []
    for number in (1, 2):
        packet = HERE / f'probes/async-probe-{number}'; files = unpack(packet)
        projection = 'ASYNC-FAILURE.json' if number == 1 else 'ASYNC.json'
        require(files['attempt/job/native/' + projection] == (packet / projection).read_bytes(), 'Readable report projection differs')
        results.append(dict(probe=number, **check_files(files, number)))
    return dict(probes=results, whole_cad_qualified=False)


if __name__ == '__main__': print(json.dumps(check(), indent=2))
