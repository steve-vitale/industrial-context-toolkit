"""Offline receiving of retained public transfer observations; no drawing qualification inferred."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'public-validation-11'))
import receive
import controls
import check_linux7


def check():
    base=HERE/'public-validation-11'
    with tempfile.TemporaryDirectory(prefix='cad-public11-archive-') as tmp:
        root=check_linux7.unpack(base,Path(tmp)/'retained')
        summary=receive.check(root)
        from PIL import Image, ImageChops
        retained=json.loads((base/'PIXELS.json').read_bytes())['pairs']
        actual_pixels=[]
        for phase in ['renders','renders-corrected']:
            for case in json.loads((base/'ADMISSION.json').read_bytes())['cases']:
                for view in ['model','asset-1']:
                    images=[]
                    for role in ['source','candidate']:
                        with Image.open(root/'native-1'/phase/(case['id']+'-'+view+'-'+role+'.png')) as im:images.append(im.convert('RGB'))
                    delta=ImageChops.difference(*images);r,g,b=delta.split()
                    nonzero=ImageChops.lighter(ImageChops.lighter(r,g),b)
                    count=nonzero.width*nonzero.height-nonzero.histogram()[0];box=delta.getbbox()
                    actual_pixels.append(dict(phase=phase,id=case['id'],view=view,different_rgb_pixels=count,bbox=list(box) if box else None))
        receive.require(actual_pixels==retained,'Matched RGB diagnostic changed')
        visual=json.loads((base/'VISUAL-REVIEW.json').read_bytes())
        expected_paths=['native-1/'+phase+'/'+case['id']+'-'+view+'-'+role+'.png'
                        for phase in ['renders','renders-corrected']
                        for case in json.loads((base/'ADMISSION.json').read_bytes())['cases']
                        for view in ['model','asset-1'] for role in ['source','candidate']]
        receive.require([v['path'] for v in visual['native_images']]==expected_paths,'Visual review coverage differs')
        receive.require(all(receive.ch.digest(root/v['path'])==v['sha256'] for v in visual['native_images']),'Reviewed image identity differs')
        actual=controls.execute(root,Path(tmp)/'controls-replay')
        expected=json.loads((root/'controls-3/RESULTS.json').read_bytes())['cases']
        receive.require(actual==expected,'Revision/loss control outcomes differ')
        for item in actual:
            identity=item['id']
            for rel in ['revision-2.dxf','revision-2-plan.json','revision-2-candidate/candidate.dxf',
                        'unplanned-geometry.dxf','changed-foreign.dxf','changed-xdata.dxf']:
                receive.require((root/'controls-3'/identity/rel).read_bytes()==(Path(tmp)/'controls-replay'/identity/rel).read_bytes(),'Control/source revision bytes differ')
        summary['source_revision_loss_controls']=len(actual)*6
        summary['matched_rgb_diagnostics']=len(actual_pixels)
        summary['remaining']=[s for s in summary['remaining'] if s!='Planted-loss and second-revision controls on this cohort']
        return summary


if __name__=='__main__':print(json.dumps(check(),indent=2))
