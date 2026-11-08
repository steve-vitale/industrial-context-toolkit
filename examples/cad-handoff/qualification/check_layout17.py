"""Receive and independently re-score native constructor diagnostics offline; no CAD launch."""
import importlib.util
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE / 'layout-construction-17'
sys.path.insert(0, str(HERE))
import check_linux7 as old

spec = importlib.util.spec_from_file_location('ict_layout17_analysis', BASE / 'analyze.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def receive(root):
    for name, pin in a.read(root / 'METHODS.json').items():
        a.require(a.sha(BASE / name) == pin, 'Layout method differs: ' + name)
    work = root / 'attempt-2'
    frozen = a.read(work / 'FREEZE.json')
    a.require(a.equal(frozen, a.read(BASE / 'FREEZE.json')), 'Pre-execution layout freeze differs')
    for name in ('FIELDS.json', 'PLAN.md', 'SOURCE-IDENTITY.json', 'layout_ctor.cpp', 'run_native.py', 'compile.py'):
        a.require(a.sha(work / name) == a.sha(BASE / name), 'Published frozen method differs: ' + name)
    prior = a.read(HERE / 'header-boundaries-16/FREEZE.json')
    a.require(frozen['image'] == prior['image'] and frozen['configuration_sha256'] == prior['configuration_sha256'], 'Prior native environment changed')
    for name, pin in frozen['inputs'].items():
        if name.startswith('cases/'):
            a.require(pin == prior['inputs'][name], 'Exposed source changed')
    env = a.read(work / 'ENVIRONMENT.json')
    state = env['state']
    a.require(env['image'] == frozen['image'] and env['user'] == '1001:1001' and env['network'] == 'none' and not env['qt_hash_seed'] and
              state['Status'] == 'exited' and state['Running'] is False and state['OOMKilled'] is False and state['ExitCode'] == 0,
              'Native terminal identity/state differs')
    a.require(a.equal(env['resources'], dict(NanoCpus=2000000000, Memory=3 * 1024**3, ShmSize=256 * 1024**2,
              PidsLimit=256, CapDrop=['ALL'], SecurityOpt=['no-new-privileges'])), 'Native resource constraints differ')
    a.require(env['path'] == 'python3' and env['args'] == ['/work/run_native.py'] and len(env['mounts']) == 1 and
              env['mounts'][0]['Type'] == 'bind' and env['mounts'][0]['Destination'] == '/work', 'Native entrypoint/mount differs')
    compiler = a.read(work / 'COMPILE.json')
    a.require(compiler['exit'] == 0 and compiler['source_sha256'] == frozen['inputs']['layout_ctor.cpp'] and
              compiler['helper_sha256'] == frozen['helper_sha256'], 'Authored helper compilation failed/differs')
    command = compiler['command']
    mount = command[command.index('--mount') + 1]
    expected = ['docker', 'run', '--name', 'ict-cad-layout17-compile1', '--network', 'none', '--read-only',
                '--memory', '2g', '--cpus', '2', '--pids-limit', '256', '--cap-drop', 'ALL', '--security-opt',
                'no-new-privileges', '--user', '1001:1001', '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m',
                '--mount', mount, '--entrypoint', '/usr/bin/g++', frozen['compiler_image'],
                '-shared', '-fPIC', '-O2', '-std=c++17', '-Wall', '-Wextra', '-Werror', '/work/layout_ctor.cpp',
                '-o', '/work/layout_ctor.so', '-ldl']
    a.require(command == expected and mount.startswith('type=bind,src=') and mount.endswith(',dst=/work'),
              'Actual compiler command differs')
    # Preserve the unexecuted preparation snapshots and the actual host preparation failure as distinct evidence.
    for folder in ('attempt-1', 'preflight-1'):
        a.require((root / folder / 'native_layouts.js').is_file() and not (root / folder / 'native').exists(), 'Unexecuted preflight omitted/promoted')
    failure = a.read(root / 'HOST-PREPARATION-FAILURE.json')
    a.require('FileNotFoundError before output folder creation' in failure['failure'], 'Host preparation failure omitted')
    a.require(a.read(root / 'first-receiver-failure/RESULT.json')['exit'] == 1 and
              "KeyError: 'exit'" in (root / 'first-receiver-failure/stderr.txt').read_text(encoding='utf-8'), 'Earlier offline receiver failure omitted')
    a.require(a.read(root / 'second-receiver-failure/RESULT.json')['exit'] == 1 and
              'Actual compiler command differs' in (root / 'second-receiver-failure/stderr.txt').read_text(encoding='utf-8'), 'Compiler-check failure omitted')
    summary, detail = a.analyze(work)
    a.require(a.equal(summary, a.read(work / 'analysis/summary.json')) and a.equal(detail, a.read(work / 'analysis/detail.json')),
              'Retained layout diagnosis differs from re-score')
    return summary


def check():
    old.recheck.method_bindings()
    a.require(a.sha(BASE / 'package.py') == a.read(BASE / 'INVENTORY.json')['packager_sha256'], 'Layout evidence packager differs')
    with tempfile.TemporaryDirectory(prefix='ict-layout17-') as temporary:
        result = receive(old.unpack(BASE, Path(temporary)))
    a.require(a.equal(result, a.read(BASE / 'SUMMARY.json')), 'Published layout diagnosis differs')
    return result


if __name__ == '__main__':
    import json
    print(json.dumps(check(), indent=2))
