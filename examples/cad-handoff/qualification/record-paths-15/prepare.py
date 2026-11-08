"""Freeze paired raw namespace revisions and crossed native jobs before execution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[3]/'scripts')]
import cad_handoff as ch
import cad_value_patch
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15/attempt-1')
OLD=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14/attempt-1')
IDS=('libre-air-water','libre-power','libre-motion','qcad-hydraulic','qcad-mechanical','qcad-template')
FORMATS={'AC1015':'R15','AC1021':'R21','AC1024':'R24'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def rename(data):
    lines=data.splitlines(keepends=True)
    positions=[i for i in range(0,len(lines)-1,2)if lines[i].strip()==b'3'and lines[i+1].strip()==b'QCAD_OBJECTS']
    if len(positions)!=1:raise ValueError('Ambiguous namespace substitution')
    lines[positions[0]+1]=lines[positions[0]+1].replace(b'QCAD_OBJECTS',b'ICT15_FOREIGN_OBJECTS',1)
    return b''.join(lines)
def main():
    ROOT.mkdir(parents=True,exist_ok=False);cases=[];jobs=[];provenance=[]
    frozen=json.loads((OLD/'FREEZE.json').read_bytes())['inputs']
    for index,identity in enumerate(IDS):
        original=OLD/'cases'/identity/'source.dxf'
        assert sha(original)==frozen['cases/'+identity+'/source.dxf']
        base=ROOT/'cases'/identity;base.mkdir(parents=True);shutil.copyfile(original,base/'original.dxf')
        doc=ch.load(original);dictionary=doc.rootdict.get('QCAD_OBJECTS')
        inherited=list(dictionary.keys())if dictionary is not None else []
        if dictionary is None:dictionary=doc.rootdict.add_new_dict('QCAD_OBJECTS',hard_owned=False)
        values={'ICT15_STRING':[(1,'ict15-string/'+identity)],'ICT15_INTEGER':[(90,1234567+index)],
            'ICT15_REAL':[(40,2.718281828+index)],
            'ICT15_ORDERED':[(1,'ict15-ordered/'+identity),(90,7654321+index),(40,1.23456789+index)],
            'ICT15_PRIVATE_STRING':[(1000,'ict15-private/'+identity)]}
        for name,tags in values.items():
            assert name not in dictionary;dictionary.add_xrecord(name).extend(tags)
        private=base/'qcad';private.mkdir();doc.saveas(private/'source.dxf')
        foreign=base/'foreign';foreign.mkdir();(foreign/'source.dxf').write_bytes(rename((private/'source.dxf').read_bytes()))
        for namespace in('qcad','foreign'):
            folder=base/namespace;source=folder/'source.dxf'
            plan=json.loads((OLD/'cases'/identity/'plan.json').read_bytes());plan['source_sha256']=sha(source);write(folder/'plan.json',plan)
            cad_value_patch.apply(source,plan,folder/'patch');shutil.copyfile(folder/'patch/candidate.dxf',folder/'candidate.dxf')
            (folder/'returns').mkdir();version=ch.load(source).dxfversion
            cases.append(dict(id=identity+'/'+namespace,identity=identity,namespace=namespace,source_version=version,
                dictionary_name='QCAD_OBJECTS'if namespace=='qcad'else'ICT15_FOREIGN_OBJECTS',
                records={name:[list(t)for t in tags]for name,tags in values.items()},inherited_names=inherited))
            for importer in('OpenDesign','dxflib'):
                for exporter in('OpenDesign','dxflib'):
                    route=importer+'-'+exporter
                    jobs.append(dict(id=identity+'/'+namespace+'/'+route,input='/work/cases/'+identity+'/'+namespace+'/source.dxf',
                        output='/work/cases/'+identity+'/'+namespace+'/returns/'+route+'.dxf',importer=importer,exporter=exporter,
                        version=FORMATS[version]if exporter=='OpenDesign'else'R15'))
        provenance.append(dict(id=identity,original_sha256=sha(original),original_pin='save-boundaries-14/FREEZE.json:cases/'+identity+'/source.dxf',inherited_names=inherited))
    write(ROOT/'CASES.json',cases);write(ROOT/'PROVENANCE.json',provenance)
    write(ROOT/'export.json',dict(jobs=jobs));write(ROOT/'fresh.json',dict(jobs=jobs,read_only=True))
    for name in('native_records.js','run_native.py'):shutil.copyfile(HERE/name,ROOT/name)
    (ROOT/'.configuration').mkdir();shutil.copyfile(OLD/'.configuration/QCAD3.conf',ROOT/'.configuration/QCAD3.conf')
    freeze=dict(inputs={p.relative_to(ROOT).as_posix():sha(p)for p in ROOT.rglob('*')if p.is_file()and'.configuration'not in p.parts},
        configuration_sha256=sha(ROOT/'.configuration/QCAD3.conf'),image='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8',
        exposure='Twelve authored paired revisions of six exposed sources; no fresh qualification')
    write(ROOT/'FREEZE.json',freeze);write(HERE/'FREEZE.json',freeze)
    print('Frozen',len(cases),'paired sources;',len(jobs),'crossed native jobs')
if __name__=='__main__':main()
