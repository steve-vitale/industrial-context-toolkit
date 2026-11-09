"""Author six declared boundary fixtures; never imports or runs the candidate."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import generate_fixtures as base
import ezdxf

CASES=[
    ('final-r12','reserved-authored','R12','cp1252','crlf',1,41,'Legacy-C','Legacy-D'),
    ('final-mirror','reserved-authored','R2000','cp1252','mixed',2,158,'Étage-7','Étage-8'),
    ('final-cyrillic','reserved-authored','R2004','cp1251','lf',3,287,'Насос-А','Насос-Б'),
    ('final-unicode','reserved-authored','R2007','utf8','mixed',2,94,'Pump Ω-7','機器 Ж-8'),
    ('final-literal','reserved-authored','R2013','utf8','crlf',1,17,'Assembly {E} '+'X'*89,'Assembly {F} '+'Y'*101),
    ('final-foreign','reserved-authored','R2018','utf8','lf',3,239,'Unit-17','Unit-18'),
]


def generate(out):
    base.CASES=CASES
    base.generate(out)
    manifest=json.loads((out/'MANIFEST.json').read_bytes())
    for index,row in enumerate(manifest['cases']):
        path=out/row['source'];doc=ezdxf.readfile(path)
        for ref in doc.modelspace().query('INSERT'):
            if index in (1,4):ref.dxf.xscale=-abs(ref.dxf.xscale)
            if index%2:ref.attribs.reverse()
        if row['version']!='R12':
            layout=doc.layouts.new('Final sheet')
            layout.page_setup(size=(297,210),margins=(10,10,10,10),units='mm')
            layout.add_viewport(center=(140,95),size=(250,160),view_center_point=(50,20),view_height=90)
        doc.saveas(path)
        raw=path.read_bytes().replace(b'\r\n',b'\n')
        raw=raw.replace(b'  0\nEOF',b'999\nFinal procedural source: retain this unfamiliar raw comment\n  0\nEOF')
        if row['newline']=='crlf':raw=raw.replace(b'\n',b'\r\n')
        elif row['newline']=='mixed':raw=b''.join(line+(b'\n' if n%5 else b'\r\n') for n,line in enumerate(raw.split(b'\n')[:-1]))
        path.write_bytes(raw);row['source_sha256']=base.sha(raw)
        planpath=out/row['plan'];plan=json.loads(planpath.read_bytes());plan['source_sha256']=row['source_sha256']
        planpath.write_text(json.dumps(plan,indent=2,ensure_ascii=True)+'\n',encoding='utf-8',newline='\n')
        row['plan_sha256']=base.sha(planpath.read_bytes())
    manifest['exposure']='Six newly declared same-author procedural configurations, generated before any candidate test; not independent plant truth'
    manifest['generator_sha256_lf']=base.sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    generate(p.parse_args().out)
