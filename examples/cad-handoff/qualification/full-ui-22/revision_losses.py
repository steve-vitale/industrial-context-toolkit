"""Rehearse exposed multi-asset revisions and exact planted losses without native CAD."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE.parent))
import cad_handoff as ch
from verify_bytes import verify


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8', newline='\n')


def require(value, message):
    if not value:
        raise ValueError(message)


def inventory(path):
    return {p.relative_to(path).as_posix(): ch.digest(p) for p in sorted(path.rglob('*')) if p.is_file()}


def command(out, label, args, expected=0, diagnostic=None):
    folder = out / 'commands' / label
    folder.mkdir(parents=True)
    actual = [sys.executable] + [str(a) for a in args]
    portable = [s.replace(str(out), '$OUT').replace(str(ROOT), '$ROOT') for s in actual[1:]]
    write(folder / 'command.json', dict(argv=['python'] + portable, expected_exit=expected))
    result = subprocess.run(actual, cwd=ROOT, capture_output=True, timeout=120)
    (folder / 'stdout.txt').write_bytes(result.stdout)
    (folder / 'stderr.txt').write_bytes(result.stderr)
    write(folder / 'exit.json', dict(returncode=result.returncode))
    require(result.returncode == expected, f'{label}: exit {result.returncode}, expected {expected}')
    if diagnostic:
        require(diagnostic.encode() in result.stderr, label + ': expected refusal missing')


def records(raw):
    """Independent raw-line mutation helper; never consumes candidate patch spans."""
    lines = raw.splitlines(keepends=True)
    require(len(lines) % 2 == 0, 'Mutation input needs complete pairs')
    result, current = [], []
    for i in range(0, len(lines), 2):
        code = int(lines[i].strip())
        if code == 0 and current:
            result.append(current)
            current = []
        current.append((i + 1, code, lines[i + 1].rstrip(b'\r\n')))
    result.append(current)
    return lines, result


def mutate(raw, kind, handle, code, replacement=None, extra=False):
    lines, groups = records(raw)
    selected = [g for g in groups if g[0][2] == kind.encode() and (5, handle.encode()) in [(c,v) for _,c,v in g]]
    require(len(selected) == 1, 'Mutation record must be unique: ' + handle)
    values = [(i,v) for i,c,v in selected[0] if c == code]
    require(len(values) == 1, 'Mutation value must be unique')
    i, before = values[0]
    after = replacement if replacement is not None else str(float(before) + 1.25).encode()
    ending = lines[i][len(before):]
    if extra:
        lines[i] += b'  3' + ending + after + ending
    else:
        require(before != after, 'Mutation must change the value')
        lines[i] = after + ending
    return b''.join(lines), dict(type=kind, handle=handle, group=code, before_hex=before.hex(),
                                 after_hex=after.hex(), operation='insert group 3' if extra else 'replace value')


def case(out, row):
    source = ROOT / row['source']
    plan = read(ROOT / row['plan'])
    original = source.read_bytes()
    before = ch.snapshot(source)
    assets = before['assets']
    require(len(assets) == 2, 'Expected both declared assets')
    a, b = assets
    patch = ROOT / 'scripts/cad_value_patch.py'
    cli = ROOT / 'scripts/cad_handoff.py'
    project = ROOT / 'examples/cad-handoff/project_to_map.py'
    map_cli = ROOT / 'scripts/one_map.py'
    write(out / 'original-plan.json', plan)
    command(out, 'proposal', [patch, source, out / 'original-plan.json', '--out', out / 'proposal'])
    candidate = out / 'proposal/candidate.dxf'
    baseline = ch.compare(before, ch.snapshot(candidate), plan)
    require(not baseline['unexpected'], 'Positive strict baseline failed')
    write(out / 'baseline-bytes.json', verify(source, candidate, plan))

    concurrent = copy.deepcopy(plan)
    concurrent['changes'][0]['after'] = 'OTHER-CHOICE'
    concurrent['changes'].append(dict(id=b['id'], attribute='SERIAL', before=b['attributes']['SERIAL'],
        after='FIELD-OBSERVED', reason='Fictional concurrent branch; not an observed installed serial'))
    write(out / 'concurrent-plan.json', concurrent)
    command(out, 'concurrent', [patch, source, out / 'concurrent-plan.json', '--out', out / 'concurrent'])
    returned = out / 'concurrent/candidate.dxf'
    stale_before = dict(plan, source_sha256=ch.digest(returned))
    write(out / 'stale-before-plan.json', stale_before)
    refusals = [('stale-hash', returned, out / 'original-plan.json', 'exact current source SHA-256'),
                ('stale-before', returned, out / 'stale-before-plan.json', 'Before-value mismatch')]
    for label, drawing, request, message in refusals:
        target = out / label
        command(out, label, [patch, drawing, request, '--out', target], 2, message)
        require(not target.exists(), label + ' published output')

    command(out, 'review-concurrent', [cli, 'review', source, returned, '--plan', out / 'original-plan.json', '--out', out / 'review-concurrent'], 1)
    report = read(out / 'review-concurrent/review.json')
    findings = {(v['id'],v['attribute']):v for v in report['asset_attributes']}
    require(report['strict_difference_count'] == 2, 'Expected separate disagreement and collateral change')
    require(findings[(a['id'],'MODEL')]['status'] == 'planned edit missing or different', 'MODEL conflict lost')
    require(findings[(b['id'],'SERIAL')]['after'] == 'FIELD-OBSERVED', 'Concurrent serial lost')

    second = dict(plan, source_sha256=ch.digest(returned), changes=[dict(id=a['id'],attribute='MODEL',
        before='OTHER-CHOICE',after=plan['changes'][0]['after'],reason='Explicit fictional selection; keep concurrent SERIAL; authorized review pending')])
    write(out / 'second-plan.json', second)
    command(out, 'second-proposal', [patch, returned, out / 'second-plan.json', '--out', out / 'second'])
    selected = out / 'second/candidate.dxf'
    write(out / 'second-bytes.json', verify(returned, selected, second))
    relative_original = ch.compare(before, ch.snapshot(selected), plan)
    require(len(relative_original['unexpected']) == 1, 'Original collateral change disappeared')
    write(out / 'original-v-selected.json', relative_original)
    final_assets = {v['id']:v for v in ch.snapshot(selected)['assets']}
    for asset in assets:
        expected = dict(asset['attributes'], MODEL=plan['changes'][0]['after'])
        if asset['id'] == b['id']:
            expected['SERIAL'] = 'FIELD-OBSERVED'
        require(final_assets[asset['id']]['attributes'] == expected, 'Selected fields/foreign values changed')

    mapping = dict(site='S',plant='P',unit='U',assets=[dict(id=v['id'],tag=v['attributes']['TAG'],section='instruments') for v in assets])
    write(out / 'mapping.json', mapping)
    for label, packet in [('original', out / 'proposal'), ('selected', out / 'second/candidate-context')]:
        projection = out / ('map-' + label)
        command(out, 'project-' + label, [project,packet,out/'mapping.json','--out',projection])
        command(out, 'build-' + label, [map_cli,'build',projection/'site.json','--out',projection/'map'])
        expected_raw = original if label == 'original' else selected.read_bytes()
        require((projection/'cad-source.dxf').read_bytes() == expected_raw, 'Projection lost exact source')
    command(out, 'map-changes', [map_cli,'changes',out/'map-original/map/graph.json',out/'map-selected/map/graph.json','--out',out/'map-changes'])
    sheet = read(out/'map-selected/sheet.json')
    require(len(sheet['instruments']) == 2 and not sheet['lines'] and not sheet['signal_lines'], 'Projection invented topology or lost assets')
    by_tag = {v['tag']:v['attributes'] for v in sheet['instruments']}
    for asset in final_assets.values():
        for key,value in asset['attributes'].items():
            require(by_tag[asset['attributes']['TAG']]['cad_' + key.lower()] == value, 'Context field changed')

    doc = ch.load(candidate)
    line = next(e for e in doc.modelspace() if e.dxftype() == 'LINE')
    block = next(e for e in doc.blocks['ASSET'] if e.dxftype() in ('LINE','CIRCLE'))
    style = doc.styles.get('Standard')
    xdata = next(e for e in doc.entitydb.values() if e.is_alive and e.has_xdata('FOREIGN_VENDOR'))
    controls = [('geometry','LINE',line.dxf.handle,10,None),
                ('layer','LINE',line.dxf.handle,8,b'0'),
                ('style','STYLE',style.dxf.handle,40,None),
                ('foreign','ATTRIB',a['attribute_handles']['VENDOR_PRIVATE'],1,b'LOST'),
                ('xdata',xdata.dxftype(),xdata.dxf.handle,1000,b'LOST-XDATA'),
                ('block',block.dxftype(),block.dxf.handle,10,None)]
    losses = []
    for label,kind,handle,code,value in controls:
        raw, mutation = mutate(candidate.read_bytes(),kind,handle,code,value)
        path = out/'losses'/(label+'.dxf');path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
        comparison = ch.compare(before,ch.snapshot(path),plan)
        require(comparison['unexpected'], 'Strict comparator missed ' + label)
        try:
            verify(source,path,plan)
        except ValueError as error:
            refusal = str(error)
        else:
            raise ValueError('Byte checker missed ' + label)
        write(out/'losses'/(label+'.json'),dict(mutation=mutation,comparison=comparison,byte_refusal=refusal))
        losses.append(dict(control=label,strict_count=len(comparison['unexpected']),byte_refused=True,mutation=mutation))

    invalid = []
    for label, edit in [('identity',dict(plan['changes'][0],attribute='ICT_ID',before=a['id'],after='OTHER-ID')),
                        ('newline',dict(plan['changes'][0],after='two\nlines'))]:
        bad = dict(plan,changes=[edit]);write(out/(label+'-plan.json'),bad)
        invalid.append((label,source,out/(label+'-plan.json'), 'noneditable attribute' if label == 'identity' else 'plain single-line'))
    duplicate = dict(plan,changes=plan['changes']+[plan['changes'][0]])
    write(out/'duplicate-plan.json',duplicate);invalid.append(('duplicate',source,out/'duplicate-plan.json','Duplicate edit'))
    malformed, mutation = mutate(original,'ATTRIB',a['attribute_handles']['MODEL'],1,b'ambiguous',extra=True)
    (out/'ambiguous.dxf').write_bytes(malformed)
    write(out/'ambiguous-plan.json',dict(plan,source_sha256=ch.digest(out/'ambiguous.dxf')))
    write(out/'ambiguous-mutation.json',mutation)
    invalid.append(('ambiguous',out/'ambiguous.dxf',out/'ambiguous-plan.json','Multiline/ambiguous'))
    for label,drawing,request,message in invalid:
        command(out,label,[patch,drawing,request,'--out',out/('refused-'+label)],2,message)
        require(not (out/('refused-'+label)).exists(),label+' emitted packet')
    saved = inventory(out/'proposal')
    command(out,'collision',[patch,source,out/'original-plan.json','--out',out/'proposal'],2,'Output folder already exists')
    require(saved == inventory(out/'proposal') and source.read_bytes() == original, 'Collision/source bytes changed')
    result = dict(case=row['case'],source_sha256=ch.digest(source),baseline_strict=0,
        concurrent_strict=report['strict_difference_count'],findings=[findings[(a['id'],'MODEL')],findings[(b['id'],'SERIAL')]],
        stale_refusals=2,admission_refusals=5,selected_strict=0,selected_original_strict=1,
        selected_sha256=ch.digest(selected),retained_serial='FIELD-OBSERVED',assets=2,context_commands=5,
        planted_losses=losses,cli_commands=len(list((out/'commands').iterdir())),
        scope='Exposed authored software branches, not native manual edits, field observations or acceptance')
    write(out/'RESULT.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--expect',help='Compare the stable result against a retained RESULT.json')
    args=parser.parse_args();out=Path(args.out).resolve()
    require(not out.exists(), 'Use a new output folder')
    freeze=read(HERE/'REVISION-LOSS-METHODS-1.json')
    for name,pin in freeze['methods_sha256_lf'].items():
        require(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() == pin,'Frozen method changed: '+name)
    catalog=read(HERE/'DEVELOPMENT-INPUTS.json')
    for row in catalog['cases']:
        require(ch.digest(ROOT/row['source']) == row['source_sha256'] and ch.digest(ROOT/row['plan']) == row['plan_sha256'],'Declared source/plan changed')
    out.mkdir(parents=True)
    try:
        results=[]
        for row in catalog['cases']:
            folder=out/row['case'];folder.mkdir();results.append(case(folder,row))
        result=dict(status='pass',cases=results,method_sha256_lf=hashlib.sha256((HERE/'REVISION-LOSS-METHODS-1.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest())
        write(out/'RESULT.json',result)
        if args.expect:
            require(result == read(args.expect),'Stable replay differs from retained result')
        write(out/'INVENTORY.json',inventory(out))
        print(json.dumps(dict(status='pass',cases=len(results),cli_commands=sum(r['cli_commands'] for r in results),
                              planted_losses=sum(len(r['planted_losses']) for r in results))))
    except Exception:
        (out/'FAILURE.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n')
        raise


if __name__ == '__main__':
    main()
