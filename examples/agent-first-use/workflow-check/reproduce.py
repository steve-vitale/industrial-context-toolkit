"""Replay seven documented fixture workflows and five regression suites; not an independent agent or plant trial."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]

def read(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def reproduce(out):
    if out.exists():raise ValueError('Use a new output directory; previous evidence is retained')
    out.mkdir(parents=True)
    jobs=[
        ('maintenance',['-S','examples/maintenance-intake/reproduce.py','--out',str(out/'maintenance')]),
        ('markups',['-S','scripts/check_pid_markups.py','--manifest','examples/pid-markup-review/inputs/manifest.json','--out',str(out/'markups')]),
        ('ports',['-S','examples/pid-port-review/replay.py','--out',str(out/'ports')]),
        ('paths',['-S','examples/pid-path-review/reproduce.py','--out',str(out/'paths')]),
        ('drawing',['-S','scripts/import_site_drawing.py','--manifest','examples/own-drawing/manifest.json','--out',str(out/'drawing')]),
        ('drawing-report',['-S','scripts/deliverable_report.py',str(out/'drawing')]),
        ('knowledge',['-B','-S','examples/engineering-onboarding/contribution-loop/reproduce.py','--out',str(out/'knowledge')]),
        ('batches',['-B','-S','scripts/batch_analysis.py','--csv','examples/batch-analysis/observations.csv','--plan','examples/batch-analysis/plan.json','--graph','examples/batch-analysis/graph.json','--out',str(out/'batches')]),
        *[(name,['-S','scripts/'+name+'.py'])for name in ['test_maintenance_intake','test_pid_markups','test_pid_connections','test_pid_path_review','test_knowledge_capture']]
    ]
    commit=None
    if shutil.which('git'):
        r=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True)
        if r.returncode==0:commit=r.stdout.strip()
    write(out/'PLAN.json',dict(scope=__doc__,commit=commit,python=sys.version,runner_sha256=sha(Path(__file__)),guide_sha256=sha(ROOT/'docs/REPRODUCE_A_WORKFLOW.md'),jobs=jobs))
    results=[]
    for label,args in jobs:
        run=subprocess.run([sys.executable,*args],cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace')
        (out/(label+'.stdout.txt')).write_text(run.stdout,encoding='utf-8',newline='\n')
        (out/(label+'.stderr.txt')).write_text(run.stderr,encoding='utf-8',newline='\n')
        row=dict(label=label,command=[sys.executable,*args],exit=run.returncode,stdout_sha256=sha(out/(label+'.stdout.txt')),stderr_sha256=sha(out/(label+'.stderr.txt')))
        results.append(row);write(out/'COMMANDS.json',results);print(label,run.returncode,flush=True)
    checks={}
    if all(r['exit']==0 for r in results[:8]):
        markup=read(out/'markups/result.json');key=read(ROOT/'examples/pid-markup-review/ACCEPTANCE.json')
        checks['markup_statuses_match_preexisting_key']={r['id']:r['status']for r in markup['markups']}==key['markup_statuses']
        checks['markup_counts_match_preexisting_key']=markup['counts']==key['counts']
        checks['other_changes_and_coverage_gap_retained']=len(markup['other_observed_changes'])==key['other_observed_changes']and len(markup['other_fact_coverage_gaps'])==key['other_fact_coverage_gaps']
        checks['markup_not_automatic_or_accepted']=markup['automatic_drawing_reading']is False and markup['release_accepted']is False
        maintenance=read(out/'maintenance/replay.json');checks['maintenance_revision_checks']=all(maintenance['checks'].values())
        knowledge=read(out/'knowledge/result.json');checks['knowledge_revision_checks']=knowledge['all_pass']is True and all(knowledge['checks'].values())
        checks['batch_entire_result_matches_committed_expected']=read(out/'batches/batch_analysis.json')==read(ROOT/'examples/batch-analysis/expected/batch_analysis.json')
        checks['drawing_report_present']=(out/'drawing/REPORT.html').is_file()
    passed=all(r['exit']==0 for r in results)and bool(checks)and all(checks.values())
    result=dict(scope=__doc__,commands=results,checks=checks,all_pass=passed)
    write(out/'RESULT.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    try:result=reproduce(args.out.resolve())
    except ValueError as error:parser.exit(1,str(error)+'\n')
    raise SystemExit(0 if result['all_pass']else 1)
