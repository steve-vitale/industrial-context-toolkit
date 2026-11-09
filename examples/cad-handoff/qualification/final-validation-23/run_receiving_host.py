"""Launch one predetermined fresh receiver using pinned completed native returns."""
import argparse
import subprocess
import sys
from pathlib import Path
from campaign import HERE, ROOT, read, write, sha, lf, require, binding


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scratch',type=Path);p.add_argument('case',choices=('public-air-water','final-foreign'));p.add_argument('configuration',type=Path)
    a=p.parse_args();binding();launch=read(HERE/'RECEIVING-LAUNCH.json')
    require(lf(__file__)==launch['driver_sha256_lf'] and sha(HERE/'UI-RETURNS.json')==launch['returns_sha256'] and sha(HERE/'UI-RETAINED.json')==launch['retained_sha256'],'Fresh receiving launch identity differs')
    require(sha(a.configuration)==read(HERE/'FREEZE.json')['configuration_sha256'],'Fresh receiving profile differs')
    returns=a.scratch/'final-native-matched-1'
    for identity,pin in read(HERE/'UI-RETURNS.json')['cases'].items():
        for role in ('baseline','edited'):
            path=returns/(identity+'-'+role)/'job/returned.dxf'
            require(sha(path)==pin[role+'_sha256'],'Fresh receiving native return differs')
    case=a.scratch/'final-native-preparation-1/ui'/a.case;prep=read(HERE/'UI-PREPARATION.json')['cases'][a.case]
    for name,pin in prep['files'].items():require(sha(case/name)==pin,'Fresh receiving prepared source differs')
    name='final23-'+a.case+'-receiving-1';host=a.scratch/(name+'-host');require(not host.exists(),'Original fresh receiving host already exists');host.mkdir()
    cmd=[sys.executable,str(HERE.parent/'full-ui-22/run_wait.py'),str(case),'receiving',str(a.configuration),str(a.scratch/name),'--name','ict-cad-'+name,'--returns',str(returns)]
    write(host/'COMMAND.json',cmd);(host/'SCRIPT.py').write_bytes(Path(__file__).read_bytes())
    with (host/'stdout.txt').open('wb') as out,(host/'stderr.txt').open('wb') as err:
        result=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=err)
    write(host/'EXIT.json',dict(exit=result.returncode))
    print('Original fresh final UI exit',a.case,result.returncode,flush=True)
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
