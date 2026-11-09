"""Recheck externally pinned initial native concurrent returns without launching CAD."""
import json
from native_revisions import HERE, read, sha, lf, require, check


def main():
    identities=read(HERE/'NATIVE-CONCURRENT-RETAINED-1.json')
    launch=read(HERE/'NATIVE-REVISION-LAUNCH-1.json')
    require(set(identities['attempts'])=={r['label'] for r in launch['runs']},'Initial concurrent cohort omitted/extra')
    results=[]
    for label,pins in identities['attempts'].items():
        packet=HERE/'concurrent-development-1'/label
        require(lf(packet/'INVENTORY.json')==pins['inventory_sha256_lf'] and lf(packet/'RESULT.json')==pins['result_sha256_lf'] and sha(packet/'evidence.tar.xz')==pins['archive_sha256'],'Externally pinned original native packet changed: '+label)
        result=check(packet);require(result['role']=='edited' and result['committed_edits']==3,'Incomplete initial native concurrent edit')
        results.append(result)
    print(json.dumps(dict(status='pass',attempts=results,whole_cad_qualified=False)))


if __name__=='__main__':main()
