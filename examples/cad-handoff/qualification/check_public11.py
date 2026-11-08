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
        actual=controls.execute(root,Path(tmp)/'controls-replay')
        expected=json.loads((root/'controls-3/RESULTS.json').read_bytes())['cases']
        receive.require(actual==expected,'Revision/loss control outcomes differ')
        for item in actual:
            identity=item['id']
            for rel in ['revision-2.dxf','revision-2-plan.json','revision-2-candidate/candidate.dxf',
                        'unplanned-geometry.dxf','changed-foreign.dxf','changed-xdata.dxf']:
                receive.require((root/'controls-3'/identity/rel).read_bytes()==(Path(tmp)/'controls-replay'/identity/rel).read_bytes(),'Control/source revision bytes differ')
        summary['source_revision_loss_controls']=len(actual)*6
        summary['remaining']=[s for s in summary['remaining'] if s!='Planted-loss and second-revision controls on this cohort']
        return summary


if __name__=='__main__':print(json.dumps(check(),indent=2))
