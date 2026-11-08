"""Declared continuation on the SAME failed edited process; not a fresh/full procedure pass."""
import traceback
from workflow import Workflow,write,require

w=Workflow('ui-focus-recovery',1000)
try:
    require(w.job['role']=='edited','Recovery is only for the retained failed edit')
    obs=w.observe();require(obs['filename']=='/work/source.dxf'and obs['modified']is False,'Recovery requires unchanged active source')
    w.focus_canvas();w.keys('Escape','Escape','t','n');require(not w.observe()['selected'],'Deselect failed')
    expected=dict(w.job['attributes']);fields=w.select_and_verify('/work/source.dxf',expected,True)
    w.control('type',fields['MANUFACTURER'],'QUAL-AFTER');expected['MANUFACTURER']='QUAL-AFTER'
    w.snapshot('edited');w.fields(expected)
    obs=w.observe();require(obs['modified']is True,'Native edit was not committed')
    require({a['tag']:a['text']for a in obs['attributes']}==expected,'Native stored edited values differ')
    w.save_as('/work/returned.dxf');w.close_doc();w.open_file('/work/returned.dxf')
    w.select_and_verify('/work/returned.dxf',expected);w.capture('/work/returned.dxf','returned');w.close_doc();w.finish()
    write(w.out/'RESULT.json',dict(status='recovery-complete',scope='Same process after retained controller failure; not a clean full-procedure pass',whole_cad_qualified=False))
except Exception:
    write(w.out/'FAILURE.json',dict(traceback=traceback.format_exc(),scope='Recovery failed; retain same native process'))
    try:w.snapshot('failure')
    except Exception:pass
    raise
