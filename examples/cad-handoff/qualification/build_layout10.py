"""Build all declared exposed layout routes and controls; no CAD execution or qualification."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

import prepare_layout10 as prepare
from verify_layout10 import verify
import recheck

HERE=Path(__file__).resolve().parent
IDS=('validation-braces','validation-cp1251','validation-foreign','validation-long','validation-unicode')
ROUTES=('original','library','library-main','prepared','candidate')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise ValueError('Output exists; retain earlier development attempt')
    args.out.mkdir(parents=True)
    all_cases=recheck.cohort();cohort=[];jobs=[]
    for case in all_cases:
        out=args.out/'cohort'/case['id'];out.parent.mkdir(exist_ok=True)
        try:
            receipt=prepare.apply(case['source'],out)
        except (prepare.ch.InputError,prepare.ch.ezdxf.DXFError) as error:
            row=dict(id=case['id'],status='refused',error=str(error))
        else:
            try:
                checked=verify(case['source'],out/'prepared.dxf',recheck.ch.digest(case['source']))
            except Exception as error:
                prepare.ch.write_json(args.out/'software-failure.json',dict(case_id=case['id'],error=str(error)))
                raise
            row=dict(id=case['id'],status=receipt['status'],layouts=len(receipt['layouts']),byte_check=checked)
        cohort.append(row)
        prepare.ch.write_json(args.out/'cohort-results.json',cohort)
    for case_id in IDS:
        case=next(c for c in all_cases if c['id']==case_id)
        out=args.out/case_id;out.mkdir()
        source=case['source'];plan=recheck.read(case['plan'])
        shutil.copyfile(source,out/'original.dxf')
        for route in ('library','library-main'):
            doc=prepare.ch.load(source)
            if route=='library-main':
                for layout in doc.layouts:
                    if layout.name=='Model':continue
                    viewports=list(layout.query('VIEWPORT'))
                    if viewports and not any(e.dxf.id==1 for e in viewports):
                        prior=layout.dxf_layout.dxf.get('viewport_handle','0')
                        layout.add_new_main_viewport();layout.set_current_viewport_handle(prior)
            doc.saveas(out/(route+'.dxf'))
        prepared=args.out/'cohort'/case_id/'prepared.dxf'
        shutil.copyfile(prepared,out/'prepared.dxf')
        rebound=copy.deepcopy(plan);rebound['source_sha256']=recheck.ch.digest(prepared)
        prepare.ch.write_json(out/'candidate-plan.json',rebound)
        recheck.patcher.apply(prepared,rebound,out/'value-packet')
        shutil.copyfile(out/'value-packet/candidate.dxf',out/'candidate.dxf')
        checked=recheck.verify(prepared,out/'candidate.dxf',rebound)
        prepare.ch.write_json(out/'candidate-byte-check.json',checked)
        # Identical window derived from source display viewport(s), never native outcome.
        d=prepare.ch.load(source);boxes=[]
        for layout in d.layouts:
            if layout.name=='Model':continue
            viewports=[v for v in layout.query('VIEWPORT') if v.dxf.id!=1]
            if not viewports:continue
            for v in viewports:
                x,y=v.dxf.center[:2];w,h=v.dxf.width,v.dxf.height
                boxes.append((x-w/2,y-h/2,x+w/2,y+h/2))
            x1,y1=min(b[0] for b in boxes),min(b[1] for b in boxes)
            x2,y2=max(b[2] for b in boxes),max(b[3] for b in boxes)
            pad=max(2,.2*max(x2-x1,y2-y1))
            window=[x1-pad,y1-pad,x2-x1+2*pad,y2-y1+2*pad]
            for route in ROUTES:
                path=out/(route+'.dxf')
                before,after=prepare.ch.snapshot(source),prepare.ch.snapshot(path)
                comparison=prepare.ch.compare(before,after)
                prepare.ch.write_json(out/(route+'-from-original-strict.json'),comparison)
                jobs.append(dict(id=case_id+'-'+route,case_id=case_id,route=route,
                    path=case_id+'/'+route+'.dxf',sha256=prepare.ch.digest(path),
                    layout=layout.name,window=window,
                    strict_from_original=len(comparison['unexpected'])))
    manifest=dict(role='Five already exposed failures, all five matched routes; no fresh validation',
                  cohort=cohort,jobs=jobs,methods_lf={name:recheck.text_hash(HERE/name) for name in
                    ('prepare_layout10.py','verify_layout10.py','build_layout10.py')},
                  ezdxf=prepare.ch.ezdxf.__version__)
    prepare.ch.write_json(args.out/'MANIFEST.json',manifest)
    print(json.dumps(dict(cohort=[dict(id=r['id'],status=r['status'],layouts=r.get('layouts'),error=r.get('error')) for r in cohort],jobs=len(jobs))))


if __name__=='__main__':main()
