"""Recheck externally pinned initial native concurrent returns without launching CAD."""
import json
from pathlib import Path
import tempfile
from native_revisions import HERE, read, sha, lf, require, receiving
from evidence import unpack
from receive import equal
from native_io import FOLDERS


def restore(files,root):
    for name,data in files.items():
        path=root/name;require(path.resolve().is_relative_to(root.resolve()),'Unsafe received path')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    # File-only archives omit empty protocol directories. Same restoration as
    # the original recheck.py; no missing files or failed history are invented.
    for name in FOLDERS:
        for path in (root/'attempt/mailbox'/name,root/'attempt/mailbox/staging'/name):
            path.mkdir(parents=True,exist_ok=True)


def check_packet(packet):
    saved=unpack(packet)
    for name in ('native_revisions.py','NATIVE-REVISION-FREEZE-1.json'):
        require(saved['receiving/'+name].replace(b'\r\n',b'\n')==(HERE/name).read_bytes().replace(b'\r\n',b'\n'),'Original derived method changed')
    with tempfile.TemporaryDirectory(prefix='ict-native-revision-replay-') as temporary:
        root=Path(temporary);restore(saved,root)
        result=receiving(root/'attempt',root/'receiving/PREPARATION.json',root/'receiving/METHODS.json')
        require(equal(result,read(root/'receiving/RESULT.json')) and equal(result,read(packet/'RESULT.json')),'Native revision replay differs')
        require(read(root/'execution/EXIT.json')['exit']==0,'Original native host failed')
    return dict(status='native-revision-replayed',case=result['case'],role=result['role'],committed_edits=result['committed_edits'],whole_cad_qualified=False)


def main():
    frozen=read(HERE/'NATIVE-REVISION-RESTORE-1.json')
    for name,pin in frozen['files_sha256_lf'].items():require(lf(HERE/name)==pin,'Frozen restoration method changed: '+name)
    identities=read(HERE/'NATIVE-CONCURRENT-RETAINED-1.json')
    launch=read(HERE/'NATIVE-REVISION-LAUNCH-1.json')
    require(set(identities['attempts'])=={r['label'] for r in launch['runs']},'Initial concurrent cohort omitted/extra')
    results=[]
    for label,pins in identities['attempts'].items():
        packet=HERE/'concurrent-development-1'/label
        require(lf(packet/'INVENTORY.json')==pins['inventory_sha256_lf'] and lf(packet/'RESULT.json')==pins['result_sha256_lf'] and sha(packet/'evidence.tar.xz')==pins['archive_sha256'],'Externally pinned original native packet changed: '+label)
        result=check_packet(packet);require(result['role']=='edited' and result['committed_edits']==3,'Incomplete initial native concurrent edit')
        results.append(result)
    print(json.dumps(dict(status='pass',attempts=results,whole_cad_qualified=False)))


if __name__=='__main__':main()
