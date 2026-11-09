"""Read bounded lossless full API comparisons beside their agent-readable summary."""
import hashlib
import json
import lzma
from campaign import HERE, read, sha, require
from evidence import MAX_FILE, MAX_RAW


def summary(result):
    return dict(scope=result['scope'],cases=[dict(id=r['id'],all_native_fields_match=r['all_native_fields_match'],field_checks=len(r['field_checks']),
        native_saves=[{k:v for k,v in s.items() if k!='comparison'} for s in r['native_saves']]) for r in result['cases']],
        fields_match=result['fields_match'],native_save_files=result['native_save_files'],whole_cad_qualified=result['whole_cad_qualified'],
        boundaries=result['boundaries'],full_comparisons='API-RESULT.json.xz (lossless complete JSON; use api_result.full_result)')


def full_result():
    pin=read(HERE/'API-RETAINED.json');path=HERE/'API-RESULT.json.xz'
    require(path.stat().st_size<=MAX_FILE and sha(path)==pin['compressed_result_sha256'],'Compressed API result differs/exceeds bound')
    decoder=lzma.LZMADecompressor(memlimit=256*1024**2);raw=decoder.decompress(path.read_bytes(),max_length=MAX_RAW+1)
    require(decoder.eof and not decoder.unused_data and len(raw)<=MAX_RAW and len(raw)==pin['result_bytes'] and hashlib.sha256(raw).hexdigest()==pin['result_sha256'],'Full API comparison bytes differ/exceed bounds')
    result=json.loads(raw)
    require(sha(HERE/'API-RESULT.json')==pin['summary_sha256'] and summary(result)==read(HERE/'API-RESULT.json'),'Readable API summary differs from complete evidence')
    return result
