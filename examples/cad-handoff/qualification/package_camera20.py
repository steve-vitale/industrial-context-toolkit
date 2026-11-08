"""Package original terminal camera runs without settings contents or proprietary binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import package_ui19 as archive
from ui19_archive import read,require,sha

def package(work,case,out):
    job=work/'camera-1'/case
    container='ict-cad-ui19-camera-air1'if case=='libre-air-water'else'ict-cad-ui20-camera-'+case
    env=archive.environment(job,container)
    process=read(job/'native/PROCESS.json')
    require(env['state']['ExitCode']==0 and process.get('controller_exit')==0 and process.get('exit')==0 and(job/'ui/RESULT.json').is_file()and not(job/'ui/FAILURE.json').exists(),'Camera job incomplete/failed; retain same original handle')
    files={};archive.collect(files,job,'raw/job')
    assembly=dict(scope='Original read-only exposed camera job, no relaunch; original full-save failures unchanged',case=case,container=container,
                  assembly_sha256=sha(Path(__file__)),archive_writer_sha256=sha(HERE/'package_ui19.py'))
    files['raw/ASSEMBLY.json']=archive.encoded(assembly)
    if case=='libre-air-water':
        files['raw/batch/LAUNCH.json']=(work/'camera-1/LAUNCH-air1.json').read_bytes()
        files['raw/batch/TERMINAL-INSPECT.json']=(work/'camera-1/TERMINAL-INSPECT-air1.json').read_bytes()
    else:
        batch=work/'camera-1/remaining-batch'
        for name in ('FREEZE.json',case+'-stage.json',case+'-launch.json',case+'-inspection.json'):
            files['raw/batch/'+name]=(batch/name).read_bytes()
    archive.pack(files,out,dict(route='exposed-camera-repeat',case=case))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('case');p.add_argument('out',type=Path);a=p.parse_args()
    package(a.work,a.case,a.out)
