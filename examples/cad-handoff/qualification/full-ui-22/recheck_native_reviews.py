"""Reproduce actual native-return findings and explicit second proposals with existing local tools."""
import argparse
import json
from pathlib import Path
from native_revisions import HERE, ROOT, read, write, sha, lf, require
from recheck_native_revisions import restore
from review_native_revision import review
from evidence import unpack
from receive import equal


def main(out):
    require(not out.exists(),'Use a new review replay folder')
    frozen=read(HERE/'NATIVE-REVIEW-REPLAY-1.json')
    for name,pin in frozen['methods_sha256_lf'].items():require(lf(HERE/name)==pin,'Frozen review replay method changed: '+name)
    native=read(HERE/'NATIVE-CONCURRENT-RETAINED-1.json')['attempts']
    require(set(frozen['cases'])==set(native),'Native review cohort omitted/extra')
    out.mkdir(parents=True);results=[]
    for label,pin in frozen['cases'].items():
        packet=HERE/'concurrent-development-1'/label;original=HERE/'concurrent-review-1'/pin['review_case']/'RESULT.json'
        require(lf(packet/'INVENTORY.json')==native[label]['inventory_sha256_lf'] and sha(packet/'evidence.tar.xz')==native[label]['archive_sha256'] and lf(packet/'RESULT.json')==native[label]['result_sha256_lf'],'Original native packet changed')
        require(lf(original)==pin['result_sha256_lf'],'Original engineering review result changed')
        root=out/label;root.mkdir();restore(unpack(packet),root)
        actual=review(root/'attempt',root/'review')
        require(equal(actual,read(original)),'Native original-scope review/second proposal differs: '+label)
        results.append(dict(case=actual['case'],cli_commands=actual['cli_commands'],original_strict=actual['original_request_strict'],second_strict=actual['second_candidate_strict']))
        write(out/'RESULT.json',dict(status='pass',cases=results,whole_cad_qualified=False))
    print(json.dumps(dict(status='pass',cases=results,whole_cad_qualified=False)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();main(a.out)
