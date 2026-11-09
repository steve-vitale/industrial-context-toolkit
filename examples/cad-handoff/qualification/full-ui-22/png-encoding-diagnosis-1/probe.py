from pathlib import Path
import json,hashlib,PIL
from PIL import Image,ImageChops
b=Path('/work');rows=[]
for n,row in enumerate(json.loads((b/'PAIRS.json').read_bytes())):
 with Image.open(b/row['left']) as a,Image.open(b/row['right']) as z,Image.open(b/row['expected']) as expected:
  d=ImageChops.difference(a,z);out=b/('linux-'+str(n)+'.png');d.save(out)
  rows.append(dict(expected=row['expected'],encoded_bytes_equal=out.read_bytes()==(b/row['expected']).read_bytes(),decoded_pixels_equal=d.mode==expected.mode and d.size==expected.size and d.tobytes()==expected.tobytes(),expected_sha256=hashlib.sha256((b/row['expected']).read_bytes()).hexdigest(),linux_sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
result=dict(Pillow=PIL.__version__,pairs=rows);(b/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print('pairs',len(rows),'byte differences',sum(not r['encoded_bytes_equal'] for r in rows),'pixel differences',sum(not r['decoded_pixels_equal'] for r in rows))
assert all(r['decoded_pixels_equal'] for r in rows)
