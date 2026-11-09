"""Read-only repeat of existing decoded correspondence; keep strict verdicts."""
from pathlib import Path
import collections
import copy
import hashlib
import json
import sys
ROOT=Path.cwd();HERE=ROOT/'examples/cad-handoff/qualification/full-ui-22/analysis/braces-pair-1'
sys.path.insert(0,str(ROOT/'examples/cad-handoff/qualification'))
import correspondence5,check_correspondence5
ch=correspondence5.recheck.ch
basis=json.loads((HERE/'BEFORE.json').read_bytes())
for name,pin in basis['methods']['methods_sha256_lf'].items():assert hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==pin
for row in basis['inputs'].values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
snap={name:ch.snapshot(row['path']) for name,row in basis['inputs'].items() if name!='plan'}
plan=json.loads(Path(basis['inputs']['plan']['path']).read_bytes());rebased=copy.deepcopy(plan);rebased['source_sha256']=snap['baseline']['sha256']
out=HERE/'reports'
if out.exists():raise ValueError('Retain earlier diagnosis')
out.mkdir();ch.write_json(out/'REBASED-PLAN.json',rebased);rows=[]
for label,left,right,p in [('source-baseline','source','baseline',None),('source-edited','source','edited',plan),('baseline-edited','baseline','edited',rebased)]:
 report=correspondence5.audit(snap[left],snap[right],p);check_correspondence5.check_report(snap[left],snap[right],p,report);ch.write_json(out/(label+'.json'),report)
 strict=ch.compare(snap[left],snap[right],p);closed=[];types=collections.Counter()
 for row in report['strict_differences']:
  if row['kind']=='entity' and all(row[side] is None or row[side]['status']=='closed exact decoded correspondence' for side in ('before','after')):
   closed.append(row['index']);diff=strict['unexpected'][row['index']];types[(diff['before'] or diff['after'])['type']]+=1
 rows.append(dict(pair=label,strict_differences=report['strict_difference_count'],counts=report['counts'],strict_rows_with_all_present_sides_closed=closed,closed_row_types=dict(types),strict_status=report['strict_status'],whole_cad_qualified=False))
ch.write_json(out/'SUMMARY.json',rows);print(json.dumps(rows,indent=2))
