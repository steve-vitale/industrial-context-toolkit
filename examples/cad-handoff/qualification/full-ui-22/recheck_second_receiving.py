"""Replay completed second receivers, unchanged model pixels and inspected-image bindings."""
import hashlib
import io
from pathlib import Path
import tempfile

from PIL import Image
from native_revisions import HERE, read, sha, lf, require
from evidence import unpack
from recheck_native_revisions import restore
from second_revisions import check, pixels


def exact_generated_files(actual,expected):
    """Compare generated image pixels exactly; retained original bytes stay hash-bound."""
    left={p.name:p for p in actual.iterdir()};right={p.name:p for p in expected.iterdir()}
    if set(left)!=set(right):return False
    for name,path in left.items():
        if path.suffix.lower()=='.png':
            with Image.open(path) as a,Image.open(right[name]) as b:
                if a.mode!=b.mode or a.size!=b.size or a.tobytes()!=b.tobytes():return False
        elif path.read_bytes()!=right[name].read_bytes():return False
    return True


def main():
    retained=read(HERE/'SECOND-RETAINED-2.json')['attempts']
    visual=read(HERE/'SECOND-VISUAL-1.json')
    expected_views={(case,label,frame) for case in ('cp1251','braces') for label in ('source','candidate')
                    for frame in ('overview','asset-1','labels-1','asset-2','labels-2')}
    require(len(visual['views'])==20 and {(r['case'],r['label'],r['frame']) for r in visual['views']}==expected_views,
            'Second visual scope omitted/duplicated')
    comparisons=identities=0
    for case in ('cp1251','braces'):
        name=case+'-second-receiving-1';packet=HERE/'second-development-1'/name;pin=retained[name]
        require(lf(packet/'INVENTORY.json')==pin['inventory_sha256_lf'] and lf(packet/'RESULT.json')==pin['result_sha256_lf'] and
                sha(packet/'evidence.tar.xz')==pin['archive_sha256'], 'Externally retained second packet differs')
        result=check(packet)
        require(result['role']=='receiving' and result['edits']==0 and not result['whole_cad_qualified'], 'Second receiving role differs')
        saved=unpack(packet)
        with tempfile.TemporaryDirectory(prefix='ict-second-pixels-') as temporary:
            root=Path(temporary);restore(saved,root)
            current=pixels(root/'attempt',root/'pixels')
            expected=HERE/'second-pixels-1'/case
            require(current==read(expected/'RESULT.json'), 'Complete second model pixel result differs')
            require(exact_generated_files(root/'pixels',expected),
                    'Second pixel/difference image files differ')
        comparisons+=len(current['comparisons']);identities+=len(current['exact_identities'])
        for row in (r for r in visual['views'] if r['case']==case):
            raw=saved[row['archive_member']]
            require(hashlib.sha256(raw).hexdigest()==row['sha256'] and row['actually_viewed'] is True, 'Inspected second image binding differs')
            with Image.open(io.BytesIO(raw)) as image:
                require(list(image.size)==row['size'] and hashlib.sha256(image.tobytes()).hexdigest()==row['pixel_sha256'], 'Inspected second pixel identity differs')
    print('Replayed2complete second receivers;',comparisons,'model comparisons;',identities,'exact identities;20inspected-image bindings. Native/paper qualification remains failed.')


if __name__=='__main__':
    main()
