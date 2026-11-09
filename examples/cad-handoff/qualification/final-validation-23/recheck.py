"""Replay the final frozen software and saved native evidence without native/model calls."""
import tempfile
import hashlib
import io
from pathlib import Path
from PIL import Image
from campaign import HERE, ROOT, read, sha, require, binding, software
from retain import check_pin
from recheck_native_revisions import restore
from receive_api import receive as receive_api
from api_result import full_result
from receive_ui import check as check_ui, restore_packet
from native_ui import pixels
from recheck_second_receiving import exact_generated_files
from receive_render import receive as receive_render
from verify_bytes import verify


def checked_view_member(row,captures):
    capture=captures[(row['label'],row['frame'])]
    member='attempt/job/ui/'+Path(capture['images'][-1]['path']).with_suffix('.canvas.png').name
    require(row['archive_member']==member,'Inspected image does not match its declared label/frame')
    return member


def check_ui_views():
    retained=read(HERE/'UI-RETAINED.json')['attempts']
    completed={name.removesuffix('-receiving') for name in retained if name.endswith('-receiving')}
    pins=read(HERE/'UI-PIXELS.json')['cases'];visual=read(HERE/'UI-VISUAL.json')['cases']
    require(set(pins)==set(visual)==completed,'Completed fresh receiver pixel/visual coverage differs')
    comparisons=identities=inspected=0
    for case in sorted(completed):
        expected=HERE/'ui-pixels'/case;pin=pins[case]
        require({p.name:sha(p) for p in expected.iterdir() if p.is_file()}==pin['files'],'Retained original pixel artifact bytes differ')
        with tempfile.TemporaryDirectory(prefix='ict-final-ui-pixels-') as temporary:
            root=Path(temporary);receipt,saved=restore_packet(case+'-receiving',root)
            current=pixels(root/'attempt',root/'pixels')
            require(current==read(expected/'RESULT.json') and exact_generated_files(root/'pixels',expected),'Complete frozen pixel result/difference image pixels differ')
            comparisons+=len(current['comparisons']);identities+=len(current['exact_identities'])
            frames=set(read(root/'attempt/job/job.json')['frames'])
            captures={(r['label'],r['frame']):r for r in read(root/'attempt/job/ui/actions.json') if r['kind']=='capture'}
            rows=visual[case]['views']
            require(len(rows)==2*len(frames) and {(r['label'],r['frame']) for r in rows}=={(label,frame) for label in ('source','candidate') for frame in frames},'Actual inspected view omitted/duplicated')
            for row in rows:
                checked_view_member(row,captures)
                raw=saved[row['archive_member']]
                require(row['actually_viewed'] is True and hashlib.sha256(raw).hexdigest()==row['sha256'],'Actual inspected image byte binding differs')
                with Image.open(io.BytesIO(raw)) as im:
                    require(im.mode==row['mode'] and list(im.size)==row['size'] and hashlib.sha256(im.tobytes()).hexdigest()==row['pixel_sha256'],'Actual inspected pixel identity differs')
                inspected+=1
    return dict(cases=len(completed),comparisons=comparisons,exact_identities=identities,inspected_source_candidate_views=inspected)


def main():
    binding()
    with tempfile.TemporaryDirectory(prefix='ict-final-validation-') as temporary:
        root=Path(temporary);pin=read(HERE/'SOFTWARE-RETAINED.json')
        saved=check_pin(HERE/'software-evidence',pin);restore(saved,root/'software')
        original=root/'software'
        expected=read(HERE/'SOFTWARE-RESULT.json')
        require(sha(HERE/'SOFTWARE-RESULT.json')==pin['result_sha256'] and read(original/'RESULT.json')==expected,'Retained software result differs')
        inputs={r['id']:r for r in read(HERE/'INPUTS.json')['cases']}
        for row in expected['cases']:
            require(read(original/row['case']/'EVALUATION.json')==row,'Retained per-case evaluation differs')
            admitted=inputs[row['case']]
            verify(ROOT/admitted['source'],original/row['case']/'candidate/candidate.dxf',read(ROOT/admitted['plan']))
        software(root/'reproduced')
        require(read(root/'reproduced/RESULT.json')==expected,'Complete frozen software reproduction differs')
        api_pin=read(HERE/'API-RETAINED.json');restore(check_pin(HERE/'api-evidence',api_pin),root/'api')
        require(receive_api(root/'api/api',root/'api/host')==full_result(),'Complete actual native API receipt differs')
        render_pin=read(HERE/'RENDER-RETAINED.json');restore(check_pin(HERE/'render-evidence',render_pin),root/'render')
        require(sha(HERE/'RENDER-RESULT.json')==render_pin['result_sha256'] and receive_render(root/'render/render',root/'render/execution')==read(HERE/'RENDER-RESULT.json'),'Complete actual native render receipt differs')
        visual=read(HERE/'RENDER-VISUAL.json');observed={r['id']:r for r in read(HERE/'RENDER-RESULT.json')['images']}
        require(len(visual['images'])==30 and {r['id'] for r in visual['images']}==set(observed),'Inspected image coverage differs')
        for row in visual['images']:
            require(row['actually_viewed'] is True and all(row[k]==observed[row['id']][k] for k in ('sha256','pixel_sha256','size','mode')),'Actual image observation binding differs')
    ui=read(HERE/'UI-RETAINED.json')['attempts']
    for name in ui:check_ui(name)
    print('Final reserved software, 40 native API saves, 30 native renders, image observations and',len(ui),'complete UI packets reproduced offline. Full native preservation remains failed.')
    print('Fresh receiving model evidence:',check_ui_views())


if __name__=='__main__':main()
