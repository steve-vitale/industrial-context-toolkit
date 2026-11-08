"""Author a fictional three-way markup handoff; no model reading or real consultant data."""
import argparse
import hashlib
import json
from pathlib import Path
from html import escape

SHEET = 'DEMO/U1/PID-101'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def drawing(role, corrected=False):
    returned = role == 'returned'
    revision = ('C' if corrected else 'B') if returned else 'A'
    elements = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 980">',
                '<rect width="1600" height="980" fill="white"/>',
                '<style>text{font:22px sans-serif;fill:#193548}.small{font-size:18px}.red{fill:#b71d29;font-weight:bold}'
                'path,line,circle,rect{stroke:#193548;stroke-width:3}.redline{stroke:#b71d29;fill:none;stroke-width:4}</style>',
                '<text x="40" y="50" font-weight="bold">Fictional P&amp;ID fragment — water-transfer system</text>',
                f'<text x="40" y="88">DEMO/U1/PID-101 · revision {revision} · {role.upper()} · NOT A PLANT RECORD</text>',
                '<path d="M220 300 H960" fill="none"/><circle cx="180" cy="300" r="40" fill="white"/>',
                '<path d="M160 325 L208 300 L160 275 Z" fill="none"/><text x="135" y="370">P-101</text>',
                '<text x="130" y="400" class="small">Transfer pump</text>',
                '<path d="M430 280 L470 320 L470 280 L430 320 Z" fill="white"/>',
                '<text x="390" y="365">FV-101</text>',
                f'<text x="365" y="398" class="small">Size {"DN80" if returned else "DN50"}</text>',
                f'<text x="365" y="426" class="small">Fail {"FO" if returned and not corrected else "FC"}</text>',
                '<rect x="960" y="245" width="100" height="150" fill="white"/>',
                '<text x="960" y="430">TK-101</text>',
                '<line x1="450" y1="300" x2="450" y2="180"/><circle cx="450" cy="150" r="40" fill="white"/>',
                '<text x="414" y="157">PT-101</text><rect x="675" y="110" width="100" height="80" fill="white"/>',
                '<text x="682" y="157">PIC-101</text>',
                '<circle cx="180" cy="650" r="40" fill="white"/><text x="135" y="715">P-102</text>',
                '<text x="110" y="747">Service: standby</text>',
                f'<text x="560" y="805">Drain: {"closed system" if returned and corrected else "[unreadable]" if returned else "open tundish"}</text>',
                '<text x="40" y="928" class="small">Simplified authored geometry and readings. No symbol-standard, field-state or design-adequacy claim.</text>']
    if not (returned and corrected):
        elements += ['<path d="M680 280 L720 320 L720 280 L680 320 Z" fill="white"/>',
                     '<text x="650" y="365">HV-102</text>']
    if not returned:
        elements.append('<text x="365" y="454" class="small">Material: 316</text>')
    if returned:
        elements += ['<path d="M270 300 V540 H520" fill="none"/>',
                     '<path d="M520 520 L560 560 L560 520 L520 560 Z" fill="white"/>',
                     '<text x="500" y="600">XV-103</text>']
        elements.append('<path d="M560 540 H1010 V395" fill="none"/>' if corrected else
                        '<path d="M560 540 H810" fill="none"/><text x="800" y="580" class="small">open end</text>')
    if returned and corrected:
        elements.append('<path d="M490 150 H675" fill="none" stroke-dasharray="10 8"/>')
    if role == 'markup':
        labels = ['M01: FV-101 size DN50 → DN80', 'M02: Remove HV-102 (safety review)',
                  'M03: Add XV-103 bypass from P-101', '        discharge through to TK-101',
                  'M04: Add PT-101 → PIC-101 signal', 'M05: [illegible annotation]',
                  'M06: P-102 duty → standby', 'M07: Drain to closed system']
        elements += [f'<text x="1110" y="{180 + i*62}" class="red">{escape(label)}</text>' for i, label in enumerate(labels)]
        elements += ['<rect x="350" y="375" width="190" height="40" class="redline"/>',
                     '<path d="M660 260 L740 340 M740 260 L660 340" class="redline"/>',
                     '<path d="M270 300 V540 H1010 V395" class="redline" stroke-dasharray="10 8"/>',
                     '<path d="M490 150 H675" class="redline" stroke-dasharray="10 8"/>']
    elements.append('</svg>')
    return '\n'.join(elements) + '\n'


def build(root, corrected=False):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    documents = []
    for role in ('original', 'markup', 'returned'):
        name = role + '.svg'
        raw = drawing(role, corrected).encode('utf-8'); (root/name).write_bytes(raw)
        documents.append(dict(id=role, role=role, path=name, sha256=hashlib.sha256(raw).hexdigest(),
                              pages=[dict(page=1, sheet=SHEET, revision=('C' if corrected else 'B') if role=='returned' else 'A', identity='confirmed')]))
    pins = {d['id']: d['sha256'] for d in documents}
    def key(kind, subject, **fields):return dict(sheet=SHEET, kind=kind, subject=subject, **fields)
    def loc(role, description, box=None):
        return [dict(document=role, sha256=pins[role], page=1, box_0_1000=box or [20,100,690,850], description=description)]
    size=key('attribute','FV-101',name='size'); hv=key('symbol','HV-102'); xv=key('symbol','XV-103')
    inlet=key('connection','P-101',relation='process',to='XV-103')
    outlet=key('connection','XV-103',relation='process',to='TK-101')
    signal=key('connection','PT-101',relation='signal',to='PIC-101')
    service=key('attribute','P-102',name='service'); note=key('note','drain-note')
    definitions=[('M01','Change FV-101 size from DN50 to DN80','normal',[(size,'DN50','DN80')]),
                 ('M02','Remove HV-102','safety',[(hv,True,False)]),
                 ('M03','Add XV-103 bypass from P-101 discharge through to TK-101','normal',[(xv,False,True),(inlet,False,True),(outlet,False,True)]),
                 ('M04','Add the PT-101 to PIC-101 signal connection','normal',[(signal,False,True)]),
                 ('M05','Illegible annotation; request clarification','normal',[]),
                 ('M06','Change P-102 service from duty to standby','normal',[(service,'duty','standby')]),
                 ('M07','Change drain note from open tundish to closed system','normal',[(note,'open tundish','closed system')])]
    markups=[]
    for mid,label,priority,checks in definitions:
        row=dict(id=mid,sheet=SHEET,text=label,priority=priority,interpretation='prepared' if checks else 'unreadable',
                 evidence=loc('markup',label,[690,110,990,770]),checks=[dict(key=k,before=b,after=a) for k,b,a in checks])
        if not checks:row['reason']='Fictional illegible annotation deliberately left uninterpreted'
        markups.append(row)
    write(root/'requests.json',dict(schema='pid-markup-requests-1',inventory_basis='Seven authored numbered annotations; inventory is not independently reviewed or automatically discovered.',markups=markups))
    observations=[]
    facts=[(size,'DN50','DN80'),(hv,True,False if corrected else True),(xv,False,True),
           (inlet,False,True),(outlet,False,corrected),(signal,False,corrected),
           (service,'standby','standby'),(note,'open tundish','closed system' if corrected else None),
           (key('attribute','FV-101',name='fail_action'),'FC','FC' if corrected else 'FO'),
           (key('symbol','PT-101'),True,True),(key('symbol','PIC-101'),True,True)]
    for k,b,a in facts:
        for role,value in [('original',b),('returned',a)]:
            row=dict(role=role,key=k,state='known' if value is not None else 'unknown',
                     evidence=loc(role, ('Explicit reviewed absence: ' if value is False else 'Authored reading: ') + json.dumps(k,sort_keys=True)))
            if value is None:row['reason']='Returned note deliberately represented as unreadable; no value guessed'
            else:
                row['value']=value
                if value is False:row['reason']='Fixture author examined the entire relevant source region; this exact symbol/typed directed connection is absent'
            observations.append(row)
    observations.append(dict(role='original',key=key('attribute','FV-101',name='material'),state='known',value='316',evidence=loc('original','Material: 316')))
    write(root/'readings.json',dict(schema='pid-drawing-readings-1',method='Authored fictional readings from the fixture design, not model extraction, engineering approval or an independent visual interpretation test.',observations=observations))
    references={}
    for field in ('requests','readings'):
        path=root/(field+'.json'); references[field]=dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest=dict(schema='pid-markup-review-1',documents=documents,**references)
    write(root/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--corrected',action='store_true');args=parser.parse_args()
    if args.out.exists():raise ValueError('Keep existing fixture; choose a new directory')
    build(args.out,args.corrected)
