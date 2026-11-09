"""Rehearse two saved drawing-receiving jobs and retain their real CLI packets; fixture runner only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def read(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8',newline='\n')


def run(out):
    if out.exists(): raise ValueError('New rehearsal folder required; retain earlier evidence')
    out.mkdir(parents=True); commands = []; checks = []
    def check(label,condition):
        checks.append(dict(check=label,passed=bool(condition)))
        write(out/'checks.json',checks)
        if not condition: raise ValueError('Rehearsal failed: '+label)
    def command(label,args,expected):
        folder = out/(label+'-execution'); folder.mkdir()
        cmd = [sys.executable,*args]; write(folder/'COMMAND.json',cmd)
        result = subprocess.run(cmd,cwd=ROOT,capture_output=True)
        (folder/'stdout.txt').write_bytes(result.stdout); (folder/'stderr.txt').write_bytes(result.stderr)
        write(folder/'EXIT.json',dict(exit=result.returncode,expected_exit=expected))
        commands.append(dict(label=label,command=cmd,exit=result.returncode,expected_exit=expected))
        write(out/'commands.json',commands); check(label+' exit',result.returncode==expected)
    command('markup',['-S','scripts/check_pid_markups.py','--manifest','examples/pid-markup-review/inputs/manifest.json','--out',str(out/'markup')],0)
    command('cad',['scripts/cad_handoff.py','review','examples/cad-handoff/source/valve.dxf','examples/cad-handoff/native/qcad/returned.dxf','--plan','examples/cad-handoff/source/edit-plan.json','--out',str(out/'cad')],1)
    markup = read(out/'markup/result.json'); cad = read(out/'cad/review.json')
    statuses = {r['id']:r['status'] for r in markup['markups']}
    check('seven request outcomes',statuses==dict(M01='supported',M02='not_supported',M03='partly_supported',M04='not_supported',M05='not_verifiable',M06='baseline_mismatch',M07='not_verifiable'))
    check('safety removal retained',next(r for r in markup['markups'] if r['id']=='M02')['priority']=='safety')
    check('unrequested fail action retained',len(markup['other_observed_changes'])==1 and markup['other_observed_changes'][0]['key']['name']=='fail_action')
    check('material coverage gap retained',len(markup['other_fact_coverage_gaps'])==1 and markup['other_fact_coverage_gaps'][0]['key']['name']=='material')
    check('CAD three edits observed',sum(r['status']=='planned edit observed' for r in cad['asset_attributes'])==3)
    check('CAD strict failure retained',cad['strict_status']=='differences' and cad['strict_difference_count']==335)
    check('no drawing acceptance',markup['release_accepted'] is False and cad['acceptance']=='not performed')
    first = {p.relative_to(out/'markup').as_posix():sha(p) for p in (out/'markup').rglob('*') if p.is_file()}
    command('portable',['-S','scripts/check_pid_markups.py','--manifest',str(out/'markup/manifest.json'),'--out',str(out/'portable')],0)
    check('portable full result reproduced',read(out/'portable/result.json')==markup)
    command('collision',['-S','scripts/check_pid_markups.py','--manifest',str(out/'markup/manifest.json'),'--out',str(out/'markup')],2)
    check('collision refused for occupied output',b'Output exists' in (out/'collision-execution/stderr.txt').read_bytes())
    check('first packet unchanged',first=={p.relative_to(out/'markup').as_posix():sha(p) for p in (out/'markup').rglob('*') if p.is_file()})
    actions = {
        'supported':('Confirm the source reading and technical intent.','Responsible engineer'),
        'partly_supported':('Return the unmet checks for correction; retain the supported parts.','Drawing author + responsible engineer'),
        'not_supported':('Return the missing/different checks for correction.','Drawing author + responsible engineer'),
        'not_verifiable':('Clarify the instruction or obtain a legible, source-bound reading.','Requesting engineer / project coordinator'),
        'baseline_mismatch':('Resolve which baseline/intent the instruction applies to.','Requesting engineer')}
    rows = []
    for item in sorted(markup['markups'],key=lambda r:(r['priority']!='safety',r['id'])):
        action,role = actions[item['status']]
        if item['priority']=='safety': action = 'Engineering safety review remains required. '+action
        rows.append(dict(item=item['id'],finding=item['status'],priority=item['priority'],request=item['text'],next_action=action,responsible_role=role,owner=None,closure='New exact return, fresh source-bound readings and responsible review',evidence='markup/REPORT.html',disposition='open'))
    rows += [dict(item='OTHER-001',finding='Unrequested FV-101 fail-action change',next_action='Assess intent and engineering/change-control implications.',responsible_role='Responsible discipline engineer',owner=None,closure='Documented technical disposition and corrected/accepted source revision',evidence='markup/REPORT.html',disposition='open'),
             dict(item='COVERAGE-001',finding='FV-101 material lacks returned evidence',next_action='Obtain the missing returned reading; retain unknown until reviewed.',responsible_role='Responsible engineer',owner=None,closure='Source-bound returned material reading',evidence='markup/result.json',disposition='open'),
             dict(item='CAD-001',finding=f"Separate CAD job: {cad['strict_difference_count']} unexpected strict differences despite three observed edits",next_action='Investigate full queue and receiving editor/layout/editability; do not waive preservation failures.',responsible_role='Drawing custodian + responsible engineer',owner=None,closure='Disposition of every difference and declared receiving checks',evidence='cad/REPORT.html',disposition='open')]
    rows.sort(key=lambda row:(row.get('priority')!='safety',row['finding']=='supported'))
    brief = dict(schema='drawing-handoff-rehearsal-1',scope='Two separate exposed fictional jobs; actual tool execution, no independent image reading or engineering review',
                 suggested_actions=['Return incomplete requested changes for correction','Escalate safety, baseline, evidence and preservation findings for review'],
                 authorized_decision='pending',release_accepted=False,items=rows)
    write(out/'brief.json',brief)
    md = ['# Drawing receiving brief — worked rehearsal','',brief['scope']+'.','',
          'Decision requested: corrections plus technical clarification. All named owners are unassigned; authorized decision remains pending.','',
          '[Markup sources and detailed evidence](markup/REPORT.html) · [Separate CAD review and strict queue](cad/REPORT.html)','',
          '| Item | Finding | Next action | Suggested role |','|---|---|---|---|']
    labels = dict(supported='Supported by supplied readings',partly_supported='Partly implemented',not_supported='Not implemented as requested',not_verifiable='Cannot verify',baseline_mismatch='Original differs from requested baseline')
    for row in rows:
        finding = labels.get(row['finding'],row['finding'])
        if row.get('request'): finding = row['request']+' — '+finding
        escaped = [str(value).replace('|','&#124;').replace('\n',' ') for value in (row['item'],finding,row['next_action'],row['responsible_role'])]
        md.append('| '+' | '.join(escaped)+' |')
    md += ['','Closure evidence and source links for every item are retained in [brief.json](brief.json).',
           'The CAD differences are an unresolved preservation failure. Neither CLI exit code is an engineering acceptance decision.',
           'This simulation measures no engineer time, reading accuracy or business benefit.']
    (out/'BRIEF.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')
    result = dict(commands=len(commands),checks=len(checks),all_checks_pass=all(r['passed'] for r in checks),markup_counts=markup['counts'],cad_strict_differences=cad['strict_difference_count'],
                  actual_input_cases=['examples/pid-markup-review/inputs/manifest.json','examples/cad-handoff/source/valve.dxf'],
                  runner_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),whole_cad_qualified=False,engineering_acceptance=False)
    write(out/'replay.json',result)
    write(out/'INVENTORY.json',dict(files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(run(args.out.resolve()),indent=2))
