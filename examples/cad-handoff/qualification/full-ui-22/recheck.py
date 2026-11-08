"""Reproduce a retained full native development receipt; no CAD launch or result promotion."""
import json
from pathlib import Path
import tempfile
from evidence import unpack
from receive import HERE, receive, read, require, equal, digest
from native_io import FOLDERS


def check_files(files,label):
    pins = read(HERE/'RETAINED-ATTEMPTS-1.json')[label]
    for name,pin in pins['original_identity'].items(): require(digest(files[name]) == pin, 'Original attempt identity differs: '+name)
    require(json.loads(files['attempt/job/JOB-FREEZE.json']) == pins['freeze'], 'Original input/method freeze differs')
    require(json.loads(files['methods/METHODS-1.json']) == read(HERE/'METHODS-1.json') and json.loads(files['methods/PREPARATION-1.json']) == read(HERE/'PREPARATION-1.json'), 'External method/preparation differs')
    require(json.loads(files['execution/EXIT.json'])['exit'] == 0 and json.loads(files['receiving/EXIT.json'])['exit'] == 0, 'Actual execution/receiving outcome differs')
    require(json.loads(files['failed-receiving/EXIT.json'])['exit'] == 1 and b'Native recorded expectation differs' in files['failed-receiving/stderr.txt'], 'Original receiver-order failure omitted')
    with tempfile.TemporaryDirectory(prefix='ict-full-ui22-') as temporary:
        root = Path(temporary)
        for name,data in files.items():
            path = root/name; require(path.resolve().is_relative_to(root.resolve()), 'Unsafe received path')
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        for name in FOLDERS:
            for folder in (root/'attempt/mailbox'/name,root/'attempt/mailbox/staging'/name): folder.mkdir(parents=True,exist_ok=True)
        result = receive(root/'attempt',HERE/'PREPARATION-1.json',HERE/'METHODS-1.json')
    require(equal(result,json.loads(files['receiving/RESULT.json'])), 'Original complete receiving receipt differs')
    require(json.loads(files['receiving/stdout.txt']) == result, 'Original receiving console differs')
    return result


def check():
    result = {}
    for label in read(HERE/'RETAINED-ATTEMPTS-1.json'):
        packet = HERE/'development-1'/label; result[label] = check_files(unpack(packet),label)
        require(equal(result[label],read(packet/'RESULT.json')), 'Readable receipt differs')
    return result


if __name__ == '__main__':
    results = check()
    print(json.dumps({label:{k:v for k,v in row.items() if k != 'native_strict'} for label,row in results.items()},indent=2))
