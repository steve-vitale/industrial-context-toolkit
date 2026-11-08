"""Replay the existing matched-brace diagnosis from committed sources and archives."""
from collections import Counter
import copy
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
# Use qualification/recheck.py, which owns the existing diagnostic, explicitly.
sys.path.insert(0,str(HERE.parent))
import correspondence5,check_correspondence5
sys.path.insert(0,str(HERE))
from evidence import unpack
from receive import require, equal, digest, read, ROOT


def check():
    folder=HERE/'analysis/braces-pair-1';basis=read(folder/'BEFORE.json')
    for name,pin in basis['methods']['methods_sha256_lf'].items():
        require(digest((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==pin,'Original diagnostic method differs')
    case=next(r for r in read(HERE/'DEVELOPMENT-INPUTS.json')['cases'] if r['case']=='validation-braces')
    raw={'source':(ROOT/case['source']).read_bytes(),'plan':(ROOT/case['plan']).read_bytes()}
    for role in ('baseline','edited'):
        files=unpack(HERE/'development-1'/('braces-'+role+'-1'))
        raw[role]=files['attempt/job/returned.dxf']
    for name,value in raw.items():require(digest(value)==basis['inputs'][name]['sha256'],'Original paired input differs: '+name)
    plan=json.loads(raw['plan']);ch=correspondence5.recheck.ch;summary=[]
    with tempfile.TemporaryDirectory(prefix='ict-brace-pair22-') as temporary:
        snap={}
        for name in ('source','baseline','edited'):
            path=Path(temporary)/(name+'.dxf');path.write_bytes(raw[name]);snap[name]=ch.snapshot(path)
        rebased=copy.deepcopy(plan);rebased['source_sha256']=snap['baseline']['sha256']
        require(rebased==read(folder/'reports/REBASED-PLAN.json'),'Diagnostic plan differs')
        for label,left,right,selected in [('source-baseline','source','baseline',None),('source-edited','source','edited',plan),('baseline-edited','baseline','edited',rebased)]:
            report=read(folder/'reports'/(label+'.json'))
            check_correspondence5.check_report(snap[left],snap[right],selected,report)
            require(equal(report,correspondence5.audit(snap[left],snap[right],selected)),'Recomputed complete diagnosis differs')
            strict=ch.compare(snap[left],snap[right],selected);closed=[];types=Counter()
            for row in report['strict_differences']:
                if row['kind']=='entity' and all(row[side] is None or row[side]['status']=='closed exact decoded correspondence' for side in ('before','after')):
                    closed.append(row['index']);difference=strict['unexpected'][row['index']]
                    types[(difference['before'] or difference['after'])['type']]+=1
            summary.append(dict(pair=label,strict_differences=report['strict_difference_count'],counts=report['counts'],
                strict_rows_with_all_present_sides_closed=closed,closed_row_types=dict(types),strict_status=report['strict_status'],whole_cad_qualified=False))
    require(equal(summary,read(folder/'reports/SUMMARY.json')),'Published paired summary differs')
    return [dict(pair=r['pair'],strict_differences=r['strict_differences'],closed_pairs=r['counts']['closed_pairs'],
                 closed_row_types=r['closed_row_types'],whole_cad_qualified=False) for r in summary]


if __name__=='__main__':print(json.dumps(check(),indent=2))
