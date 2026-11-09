"""Select pinned public paths from metadata only, excluding previously retained DXF blobs."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def select():
    require=lambda ok,message:None if ok else (_ for _ in ()).throw(ValueError(message))
    require(not (HERE/'SELECTION.json').exists(),'Selection already exists')
    seen={}
    for p in ROOT.rglob('*.dxf'):
        raw=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        seen.setdefault(blob,[]).append(p.relative_to(ROOT).as_posix())
    libre=json.loads((HERE/'librecad-tree.json').read_bytes())
    ez=json.loads((HERE/'ezdxf-tree.json').read_bytes())
    require(not libre['truncated'] and not ez['truncated'],'Truncated selection tree')
    pools=[('public-air-water','LibreCAD/LibreCAD',libre['sha'],'librecad/support/library/plan/air_water/',libre['tree']),
           ('public-mechanical','LibreCAD/LibreCAD',libre['sha'],'librecad/support/library/kinetics/',libre['tree']),
           ('public-power','LibreCAD/LibreCAD',libre['sha'],'librecad/support/library/plan/power_engineering/',libre['tree']),
           ('public-hatch','mozman/ezdxf','c498560bb491c357deda538360ed0c8fdb11f5a7','examples_dxf/',[dict(r,path='examples_dxf/'+r['path']) for r in ez['tree'] if 'hatch' in r['path'].lower()])]
    selected=[];audit=[]
    for identity,repository,commit,prefix,tree in pools:
        candidates=[r for r in tree if r['type']=='blob' and r['path'].startswith(prefix) and r['path'].endswith('.dxf')]
        available=[r for r in candidates if r['sha'] not in seen]
        require(bool(available),'No unseen public blob in '+identity)
        score=lambda r:hashlib.sha256(('ICT-FINAL-23:'+r['path']).encode()).hexdigest()
        row=min(available,key=score)
        selected.append(dict(id=identity,repository=repository,commit=commit,path=row['path'],git_blob_sha1=row['sha'],bytes=row['size'],pool_size=len(candidates),unseen_pool_size=len(available),selection_score=score(row)))
        audit.append(dict(id=identity,prefix=prefix,candidates=[dict(r,previously_retained=r['sha'] in seen,selection_score=score(r)) for r in candidates]))
    def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    write('SELECTION.json',dict(rule='Minimum SHA256 of ICT-FINAL-23: plus path in each declared metadata pool, excluding existing repository DXF Git blobs; no selected contents read',cases=selected))
    write('SELECTION-AUDIT.json',dict(pools=audit,previously_retained_dxf_blobs=seen,exclusion_scope='Current repository unarchived DXF bytes; no claim to enumerate unretained human/model exposure'))
    print([(r['id'],r['path']) for r in selected])


if __name__=='__main__':select()
