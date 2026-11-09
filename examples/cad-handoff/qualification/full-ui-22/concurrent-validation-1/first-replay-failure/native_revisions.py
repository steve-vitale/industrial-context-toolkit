"""Prepare and receive explicitly derived native revision cases without changing historical methods."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(HERE.parent))
import cad_handoff as ch
from prepare import frame
from run_cases import run_case
from receive import receive, equal
from evidence import unpack, MAX_RAW, MAX_FILE, MAX_FILES


def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lf(path): return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def write(path,value): Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8',newline='\n')
def require(value,message):
    if not value: raise ValueError(message)
def files(path): return {p.relative_to(path).as_posix():sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def binding():
    frozen=read(HERE/'NATIVE-REVISION-FREEZE-1.json')
    for name,pin in frozen['files_sha256_lf'].items():
        require(lf(ROOT/name)==pin,'Native revision frozen method changed: '+name)
    for row in frozen['inputs']:
        require(sha(ROOT/row['source'])==row['source_sha256'] and sha(ROOT/row['plan'])==row['plan_sha256'],'Declared native revision input changed')
        require(sha(ROOT/row['candidate'])==row['candidate_sha256'] and lf(ROOT/row['baseline_inventory'])==row['baseline_inventory_sha256_lf'],'Declared candidate/baseline packet changed')
    return frozen


def preparation(out):
    frozen=binding();require(not out.exists(),'Use a new preparation folder')
    parent=read(HERE/'PREPARATION-1.json')
    out.mkdir(parents=True);(out/'cases').mkdir()
    value=dict(scope='Derived exposed native concurrent cases; preparation field is retained original-parent lineage, not this adapter producer',
        configuration_sha256=parent['configuration_sha256'],preparation=parent['preparation'],
        derivation=dict(producer_sha256_lf=lf(__file__),parent_preparation_sha256_lf=lf(HERE/'PREPARATION-1.json'),
                        freeze_sha256_lf=lf(HERE/'NATIVE-REVISION-FREEZE-1.json'),phase='concurrent',inputs=frozen['inputs']),cases={})
    for row in frozen['inputs']:
        label=row['case'];folder=out/'cases'/label;folder.mkdir()
        source=folder/'source.dxf';planpath=folder/'plan.json'
        shutil.copyfile(ROOT/row['source'],source);shutil.copyfile(ROOT/row['plan'],planpath)
        plan=read(planpath);snapshot=ch.snapshot(source);ch.validate_plan(snapshot,plan)
        old=parent['cases'][label]['basis']
        require(equal(snapshot['assets'],old['assets']) and snapshot['sha256']==old['source_sha256'],'Original parent/source differs')
        assets=snapshot['assets'];changes=plan['changes']
        require(len(assets)==2 and len(changes)==3,'Concurrent input needs exactly two assets/three changes')
        require([(c['id'],c['attribute'],c['after']) for c in changes]==[(assets[0]['id'],'MODEL','OTHER-CHOICE'),
            (assets[1]['id'],'MODEL',old['changes'][1]['after']),(assets[1]['id'],'SERIAL','FIELD-OBSERVED')], 'Declared concurrent story differs')
        result=run_case(label,source,planpath,folder/'software')
        write(folder/'SOFTWARE.json',result)
        candidate=folder/'software/candidate/candidate.dxf'
        require(result['routes']['value-spans']['strict_status']=='pass' and result['routes']['value-spans']['byte_check']['status']=='pass','Concurrent candidate failed')
        expected=ROOT/row['candidate']
        require(candidate.read_bytes()==expected.read_bytes(),'Concurrent candidate differs from retained software branch')
        docs=[ch.load(source),ch.load(candidate)];models=[d.modelspace() for d in docs]
        frames=dict(overview=frame([e for m in models for e in m]))
        for number,asset in enumerate(assets,1):
            inserts=[d.entitydb[asset['handle']] for d in docs];attrs=[a for insert in inserts for a in insert.attribs]
            frames['asset-'+str(number)]=frame(inserts+attrs);frames['labels-'+str(number)]=frame(attrs)
        basis=dict(case=label,source_sha256=sha(source),plan_sha256=sha(planpath),assets=assets,changes=changes,frames=frames,
            scope='Exposed native concurrent UI rehearsal; FIELD-OBSERVED is fictional; no engineering acceptance')
        write(folder/'basis.json',basis)
        value['cases'][label]=dict(basis=basis,files=files(folder))
        write(out/'PREPARATION.json',value)
    return value


def validate_preparation(path):
    frozen=binding();value=read(path);parent=read(HERE/'PREPARATION-1.json')
    require(lf(path)==lf(HERE/'NATIVE-REVISION-PREPARATION-1.json'),'External pre-launch derived preparation differs')
    require(equal(value['preparation'],parent['preparation']) and value['configuration_sha256']==parent['configuration_sha256'],'Original preparation lineage differs')
    derived=value['derivation']
    require(derived==dict(producer_sha256_lf=lf(__file__),parent_preparation_sha256_lf=lf(HERE/'PREPARATION-1.json'),
        freeze_sha256_lf=lf(HERE/'NATIVE-REVISION-FREEZE-1.json'),phase='concurrent',inputs=frozen['inputs']), 'Derived preparation lineage differs')
    require(set(value['cases'])=={r['case'] for r in frozen['inputs']},'Derived case omitted/extra')
    for row in frozen['inputs']:
        case=value['cases'][row['case']];basis=case['basis'];original=parent['cases'][row['case']]['basis']
        require(basis['source_sha256']==row['source_sha256'] and basis['plan_sha256']==row['plan_sha256'] and equal(basis['assets'],original['assets']) and basis['changes']==read(ROOT/row['plan'])['changes'],'Derived source/plan/assets differ')
        require(case['files']['software/candidate/candidate.dxf']==sha(ROOT/row['candidate']),'Derived candidate differs')
    return value


def receiving(attempt,prepared,methods):
    value=validate_preparation(prepared)
    require(lf(methods)==read(HERE/'NATIVE-REVISION-FREEZE-1.json')['selected_methods_sha256_lf'],'Selected native revision methods differ')
    basis=read(attempt/'job/job.json');label=basis['case']
    if basis['role']=='receiving':
        row=next(r for r in binding()['inputs'] if r['case']==label)
        baseline=read(ROOT/row['baseline_inventory'])['files']['attempt/job/returned.dxf']['sha256']
        require(sha(attempt/'job/baseline.dxf')==baseline,'Reused no-edit baseline differs from original complete packet')
    return receive(attempt,prepared,methods)


def package(attempt,execution,receipt,prepared,methods,out):
    require(not out.exists(),'Use a new packet directory')
    result=receiving(attempt,prepared,methods)
    require(equal(result,read(receipt)) and read(execution/'EXIT.json')['exit']==0,'Received result/original host differs')
    saved={}
    for prefix,folder in [('attempt',attempt),('execution',execution)]:
        for p in folder.rglob('*'):
            if p.is_file():saved[prefix+'/'+p.relative_to(folder).as_posix()]=p.read_bytes()
    for name,path in [('RESULT.json',receipt),('PREPARATION.json',prepared),('METHODS.json',methods),
                      ('native_revisions.py',Path(__file__)),('NATIVE-REVISION-FREEZE-1.json',HERE/'NATIVE-REVISION-FREEZE-1.json')]:
        saved['receiving/'+name]=path.read_bytes()
    require(len(saved)<=MAX_FILES and sum(map(len,saved.values()))<=MAX_RAW and max(map(len,saved.values()))<=MAX_FILE,'Revision packet exceeds existing archive bounds')
    out.mkdir(parents=True)
    with tarfile.open(out/'evidence.tar.xz','w:xz',preset=6) as archive:
        for name,data in sorted(saved.items()):
            member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644;member.mtime=0
            archive.addfile(member,io.BytesIO(data))
    write(out/'INVENTORY.json',dict(archive_sha256=sha(out/'evidence.tar.xz'),files={n:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for n,v in sorted(saved.items())}))
    write(out/'RESULT.json',result)
    return dict(files=len(saved),raw_bytes=sum(map(len,saved.values())),archive_bytes=(out/'evidence.tar.xz').stat().st_size)


def check(packet):
    data=unpack(packet)
    require(data['receiving/native_revisions.py'].replace(b'\r\n',b'\n')==Path(__file__).read_bytes().replace(b'\r\n',b'\n') and data['receiving/NATIVE-REVISION-FREEZE-1.json'].replace(b'\r\n',b'\n')==(HERE/'NATIVE-REVISION-FREEZE-1.json').read_bytes().replace(b'\r\n',b'\n'),'Revision receiving method changed')
    with tempfile.TemporaryDirectory(prefix='ict-native-revision-') as temporary:
        root=Path(temporary)
        for name,content in data.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        result=receiving(root/'attempt',root/'receiving/PREPARATION.json',root/'receiving/METHODS.json')
        require(equal(result,read(root/'receiving/RESULT.json')) and equal(result,read(packet/'RESULT.json')),'Native revision replay differs')
        require(read(root/'execution/EXIT.json')['exit']==0,'Original revision host failed')
    return dict(status='native-revision-replayed',case=result['case'],role=result['role'],committed_edits=result['committed_edits'],whole_cad_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    prepare=sub.add_parser('prepare');prepare.add_argument('out',type=Path)
    receive_parser=sub.add_parser('receive')
    for name in ('attempt','prepared','methods','out'):receive_parser.add_argument(name,type=Path)
    pack=sub.add_parser('package')
    for name in ('attempt','execution','receipt','prepared','methods','out'):pack.add_argument(name,type=Path)
    replay=sub.add_parser('check');replay.add_argument('packet',type=Path)
    a=p.parse_args()
    if a.action=='prepare':result=preparation(a.out);print('Prepared',len(result['cases']),'exposed native concurrent cases')
    elif a.action=='receive':
        require(not a.out.exists(),'Use a new receiving file');result=receiving(a.attempt,a.prepared,a.methods);write(a.out,result);print('Received',result['case'],result['role'],result['committed_edits'],'edits')
    elif a.action=='package':print(json.dumps(package(a.attempt,a.execution,a.receipt,a.prepared,a.methods,a.out)))
    else:print(json.dumps(check(a.packet)))


if __name__=='__main__':main()
