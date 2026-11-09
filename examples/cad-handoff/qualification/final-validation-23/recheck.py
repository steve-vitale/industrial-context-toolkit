"""Replay the final frozen software and saved native evidence without native/model calls."""
import tempfile
from pathlib import Path
from campaign import HERE, ROOT, read, sha, require, binding, software
from retain import check_pin
from recheck_native_revisions import restore
from receive_api import receive as receive_api
from api_result import full_result
from receive_render import receive as receive_render
from verify_bytes import verify


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
    print('Final reserved software, 40 native API saves, 30 native renders and image observations reproduced offline. Full native preservation remains failed.')


if __name__=='__main__':main()
