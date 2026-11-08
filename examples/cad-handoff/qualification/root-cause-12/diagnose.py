"""Explain exact residuals and index full-save failures; no equivalence metric or waiver."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import analyze as a

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import correspondence5
import check_correspondence5

def grouped(record):
    out={}
    for code,value in (record or {}).get('tags',[]):out.setdefault(str(code),[]).append(value)
    return out

def residuals(root):
    cases=[]
    for identity in a.IDS:
        folder=root/'cases'/identity;source=a.ch.snapshot(folder/'source.dxf');plan=a.read(folder/'plan.json')
        for fmt in ('default','r15'):
            noop=a.ch.snapshot(folder/'returns'/('noop-'+fmt+'.dxf'))
            edited=a.ch.snapshot(folder/'returns'/('edited-'+fmt+'.dxf'))
            rebound=dict(plan,source_sha256=noop['sha256']);report=a.ch.compare(noop,edited,rebound)
            details=[]
            for index,row in enumerate(report['unexpected']):
                detail=dict(index=index,kind=row['kind'],strict_row_sha256=correspondence5.fingerprint(row))
                if row['kind']=='entity' and row['before'] and row['after']:
                    detail.update(handle=row['handle'],type=row['before']['type'],
                        groups=a.ch.field_changes(grouped(row['before']),grouped(row['after'])))
                    if row['before']['type']=='XRECORD' and [1,'DWGPROPS COOKIE'] in row['before']['tags']:
                        checks={}
                        for side,snap in (('before',noop),('after',edited)):
                            vals=grouped(row[side]);checks[side]={
                                'group_41_equals_header_TDUCREATE':vals.get('41')==[snap['save_metadata'].get('$TDUCREATE')],
                                'group_42_equals_header_TDUPDATE':vals.get('42')==[snap['save_metadata'].get('$TDUPDATE')]}
                        detail['embedded_time_checks']=checks
                details.append(detail)
            cases.append(dict(id=identity,format=fmt,strict_differences=len(report['unexpected']),details=details))
    return cases

def full_save(root):
    rows=[]
    for identity in a.IDS:
        folder=root/'cases'/identity
        for fmt in ('default','r15'):
            source=a.ch.snapshot(folder/'source.dxf');noop=a.ch.snapshot(folder/'returns'/('noop-'+fmt+'.dxf'))
            again=a.ch.snapshot(folder/'returns'/('repeat-'+fmt+'.dxf'))
            for phase,left,right in (('first_save',source,noop),('second_save',noop,again)):
                report=correspondence5.audit(left,right)
                check_correspondence5.check_report(left,right,None,report)
                strict=a.ch.compare(left,right)
                indexed=[]
                for index,r in enumerate(strict['unexpected']):
                    row=dict(index=index,kind=r['kind'],sha256=correspondence5.fingerprint(r))
                    if r['kind']=='entity':
                        before,after=r['before'],r['after']
                        row.update(handle=r['handle'],before_type=(before or {}).get('type'),after_type=(after or {}).get('type'),
                            group_codes_changed=sorted(a.ch.field_changes(grouped(before),grouped(after)),key=int))
                    indexed.append(row)
                def counts(s):return dict(sorted(Counter(r['type']for r in s['entities'].values()).items()))
                ld,lt,lb,ll=a.ch.review_records(a.ch.load(folder/('source.dxf' if phase=='first_save' else 'returns/noop-'+fmt+'.dxf')))
                rd,rt,rb,rl=a.ch.review_records(a.ch.load(folder/('returns/noop-'+fmt+'.dxf' if phase=='first_save' else 'returns/repeat-'+fmt+'.dxf')))
                rows.append(dict(id=identity,format=fmt,phase=phase,before_sha256=left['sha256'],after_sha256=right['sha256'],
                    strict_status=strict['status'],strict_differences=indexed,counts=report['counts'],
                    exact_closed_pairs=report['correspondence']['pairs'],
                    before_unpaired_reasons=dict(Counter(r['reason']for r in report['correspondence']['before'].values()if r['status']=='unpaired')),
                    after_unpaired_reasons=dict(Counter(r['reason']for r in report['correspondence']['after'].values()if r['status']=='unpaired')),
                    before_types=counts(left),after_types=counts(right),header_changes=a.ch.field_changes(left['header'],right['header']),
                    named_table_changes=a.ch.field_changes(lt,rt),block_changes=a.ch.field_changes(lb,rb),layout_changes=a.ch.field_changes(ll,rl)))
    return rows

def diagnose(first,second):
    return dict(original_operation_residuals=residuals(first),preserved_operation_residuals=residuals(second),
        first_attempt_full_save=full_save(first),
        boundary='Exact strict row coverage and conservative closed decoded subsets. Unpaired is unresolved, not inferred lost or harmless. Full saves remain failures.')

if __name__=='__main__':
    result=diagnose(Path(sys.argv[1]),Path(sys.argv[2]));a.write(Path(sys.argv[3]),result)
    print('Diagnosed 24 matched residual comparisons and 24 full saves; every strict row retained')
