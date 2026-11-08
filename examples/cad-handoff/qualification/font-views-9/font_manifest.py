"""Record local font identities/coverage, not font binaries or a canvas-readability verdict."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root=Path('/work')
required=set()
for receipt in (root/'receipts').glob('*.json'):
    row=json.loads(receipt.read_text(encoding='utf-8'))
    for role in ('source','candidate'):
        for asset in row['pair'][role]['assets'].values():
            for attr in asset['attributes']:required.update(attr['text'])
cxf=Path('/opt/qcad/fonts/Standard.cxf')
raw=cxf.read_bytes()
codes={int(m.group(1),16) for m in re.finditer(r'^\[([0-9a-fA-F]{4,6})\]',raw.decode('utf-8'),re.MULTILINE)}
matched=subprocess.run(['fc-match','-f','%{file}\n%{family}\n','DejaVu Sans'],capture_output=True,text=True,check=True).stdout.splitlines()
ttf=Path(matched[0])
fonts=[]
for p in (cxf,ttf):
    b=p.read_bytes();fonts.append(dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
result=dict(role='Local installed font metadata only; Qt metrics and native canvas observations remain separate',
    fonts=fonts,fontconfig_match=matched,required_characters=sorted(required),
    standard_cxf_header_codes=sorted(codes),
    standard_cxf_missing_characters=sorted(c for c in required if not c.isspace() and ord(c) not in codes))
(root/'font-manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
