"""Rehearse a corrected fictional consultant return with fresh readings and a stale-reading refusal."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def write(path,value): path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8',newline='\n')
def inventory(root): return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}


def run(initial,out):
    if out.exists(): raise ValueError('New revision rehearsal destination required')
    before = inventory(initial)
    initial_report = read(initial/'markup/result.json'); cad = read(initial/'cad/review.json')
    if not read(initial/'replay.json')['all_checks_pass'] or cad['strict_difference_count'] != 335:
        raise ValueError('Use the completed fixed drawing-handoff rehearsal as initial evidence')
    out.mkdir(parents=True); commands=[]; checks=[]
    source = ROOT/'examples/pid-markup-review/corrected'; key = ROOT/'examples/pid-markup-review/ACCEPTANCE.json'
    write(out/'BASIS.json',dict(initial_files=before,corrected_manifest_sha256=sha(source/'manifest.json'),prior_key_sha256=sha(key),
          plan_sha256=sha(HERE/'REVISION-PLAN.md'),runner_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest()))
    def check(label,condition):
        checks.append(dict(check=label,passed=bool(condition)));write(out/'checks.json',checks)
        if not condition: raise ValueError('Revision rehearsal failed: '+label)
    def command(label,manifest,destination,expected):
        logs=out/(label+'-execution');logs.mkdir();cmd=[sys.executable,'-S','scripts/check_pid_markups.py','--manifest',str(manifest),'--out',str(destination)]
        write(logs/'COMMAND.json',cmd);r=subprocess.run(cmd,cwd=ROOT,capture_output=True)
        (logs/'stdout.txt').write_bytes(r.stdout);(logs/'stderr.txt').write_bytes(r.stderr);write(logs/'EXIT.json',dict(exit=r.returncode,expected_exit=expected))
        commands.append(dict(label=label,command=cmd,exit=r.returncode,expected_exit=expected));write(out/'commands.json',commands);check(label+' exit',r.returncode==expected)
    command('corrected',source/'manifest.json',out/'corrected',0)
    current=read(out/'corrected/result.json'); expected=read(key)['corrected_return_statuses']
    check('all seven current outcomes use prior corrected key',{r['id']:r['status'] for r in current['markups']}==expected)
    check('five supported and two unresolved',current['counts']==dict(supported=5,not_verifiable=1,baseline_mismatch=1))
    safety=next(r for r in current['markups'] if r['id']=='M02')
    check('supported safety item still requires review',safety['priority']=='safety' and safety['status']=='supported' and safety['review_required'] is True)
    old_return=next(d for d in initial_report['documents'] if d['role']=='returned');new_return=next(d for d in current['documents'] if d['role']=='returned')
    check('new exact return and reading binding',old_return['sha256']!=new_return['sha256'] and initial_report['input_sha256']['readings']!=current['input_sha256']['readings'])
    command('portable',out/'corrected/manifest.json',out/'portable',0)
    check('portable full current result reproduced',read(out/'portable/result.json')==current)
    control=out/'stale-input';shutil.copytree(initial/'markup',control);manifest=read(control/'manifest.json')
    doc=next(d for d in manifest['documents'] if d['role']=='returned');old_hash=doc['sha256']
    corrected_doc=next(d for d in read(source/'manifest.json')['documents'] if d['role']=='returned')
    (control/doc['path']).write_bytes((source/corrected_doc['path']).read_bytes());doc['sha256']=corrected_doc['sha256'];doc['pages']=copy.deepcopy(corrected_doc['pages']);write(control/'manifest.json',manifest)
    write(out/'STALE-CONTROL.json',dict(changed='Returned source bytes, manifest hash and revision; original readings retained',old_return_sha256=old_hash,new_return_sha256=doc['sha256'],readings_sha256=sha(control/'readings.json')))
    command('stale',control/'manifest.json',out/'stale-output',2)
    check('stale source-bound readings refused',b'Stale observation/markup document hash' in (out/'stale-execution/stderr.txt').read_bytes() and not (out/'stale-output').exists())
    check('original packet unchanged',inventory(initial)==before)
    check('no automatic acceptance',current['release_accepted'] is False and cad['acceptance']=='not performed')
    old={r['id']:r for r in initial_report['markups']};rows=[]
    for item in sorted(current['markups'],key=lambda r:(r['priority']!='safety',r['status']=='supported',r['id'])):
        status=item['status'];action=('Engineering review of the current evidence remains required.' if status=='supported' else
                                    'Clarify the illegible instruction.' if status=='not_verifiable' else 'Resolve the requested baseline/intent.')
        if item['priority']=='safety':action='Safety review remains required even though current readings support the request.'
        rows.append(dict(id=item['id'],request=item['text'],previous=old[item['id']]['status'],current=status,priority=item['priority'],
                         next_action=action,engineering_closure='pending',owner=None,current_evidence='corrected/REPORT.html',
                         source_checks=item['checks'],request_evidence=item['evidence']))
    baseline_questions=[dict(request=row['id'],key=check['key'],requested_before=check['before'],
                        observed_original=check['original'],observed_return=check['returned'])
                        for row in rows for check in row['source_checks'] if check['status']=='baseline_mismatch']
    coverage_actions=[dict(key=gap['key'],original=gap['original'],returned=gap['returned'],owner=None,
                      next_action='Obtain a source-bound current reading; do not infer preservation or removal from an absent observation.')
                      for gap in current['other_fact_coverage_gaps']]
    check('baseline question retains requested and observed values',len(baseline_questions)==1 and baseline_questions[0]['request']=='M06' and
          baseline_questions[0]['requested_before']=='duty' and baseline_questions[0]['observed_original']['value']=='standby' and
          baseline_questions[0]['observed_return']['value']=='standby')
    check('coverage action retains the actual unknown material',len(coverage_actions)==1 and
          coverage_actions[0]['key']['subject']=='FV-101' and coverage_actions[0]['key']['name']=='material' and
          coverage_actions[0]['original']['value']=='316' and coverage_actions[0]['returned']['state']=='unknown' and
          not coverage_actions[0]['returned']['observations'])
    report=dict(schema='drawing-handoff-revision-rehearsal-1',release_accepted=False,authorized_decision='pending',items=rows,
                initial_return_sha256=old_return['sha256'],current_return_sha256=new_return['sha256'],
                current_other_observed_changes=current['other_observed_changes'],current_coverage_gaps=current['other_fact_coverage_gaps'],
                baseline_questions=baseline_questions,coverage_actions=coverage_actions,
                separate_cad_strict_differences=cad['strict_difference_count'],cad_finding_resolved=False,
                scope='Existing exposed fictional returns with authored readings; actual comparison, not independent image reading or engineering closure')
    write(out/'revision.json',report)
    shutil.copytree(initial/'markup',out/'previous');shutil.copytree(initial/'cad',out/'separate-cad')
    labels=dict(supported='Supported by current readings',not_supported='Not implemented as requested',partly_supported='Partly implemented',not_verifiable='Cannot verify',baseline_mismatch='Baseline mismatch')
    md=['# Receiving the next consultant return','',report['scope']+'.','',
        '**Decision requested:** review the corrected evidence; clarify M05 and M06. Authorized receiving/release remains pending.','',
        '[Previous markup evidence](previous/REPORT.html) · [Corrected return evidence](corrected/REPORT.html) · [Separate CAD finding](separate-cad/REPORT.html)','',
        '| Item / request | Previous finding | Current finding | Next action |','|---|---|---|---|']
    for row in rows:
        values=[row['id']+': '+row['request'],labels[row['previous']],labels[row['current']],row['next_action']]
        md.append('| '+' | '.join(value.replace('|','&#124;').replace('\n',' ') for value in values)+' |')
    def reading(value):
        return json.dumps(value.get('value'),ensure_ascii=True) if value['state']=='known' else value['state']+' ('+value.get('reason','unresolved reading')+')'
    md += ['', '**Clarify the baseline**', '']
    for question in baseline_questions:
        md.append(f"- {question['request']}: the instruction starts from {json.dumps(question['requested_before'])}; the original reads {reading(question['observed_original'])} and the return reads {reading(question['observed_return'])}. Confirm the intended change and correct baseline; a matching return alone does not resolve the instruction.")
    md += ['', '**Obtain the missing evidence**', '']
    for gap in coverage_actions:
        key=gap['key']
        md.append(f"- {key['sheet']} / {key['subject']} / {key['name']}: original {reading(gap['original'])}; return {reading(gap['returned'])}. {gap['next_action']}")
    md += ['',f"Other current observed changes: {len(current['other_observed_changes'])}. Current coverage gaps: {len(current['other_fact_coverage_gaps'])}. revision.json retains each request's full current source checks, original/return observations and locations; follow the corrected packet for the source files.",
           'The separate CAD preservation finding remains unresolved at 335 strict differences. This P&ID correction does not close it.',
           'All engineering closure decisions remain pending and owners unassigned. The old packet and old findings are retained.',
           'The deliberate new-source/old-reading control refused; updating the manifest alone cannot carry findings onto a new return.']
    (out/'REVISION-BRIEF.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')
    result=dict(commands=len(commands),checks=len(checks),all_checks_pass=all(r['passed'] for r in checks),current_counts=current['counts'],
                open_requests=['M05','M06'],safety_review_required=True,cad_finding_resolved=False,engineering_acceptance=False)
    write(out/'replay.json',result);write(out/'INVENTORY.json',dict(files=inventory(out)));return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--initial',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(run(args.initial.resolve(),args.out.resolve()),indent=2))
