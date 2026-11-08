import hashlib,json,subprocess,sys
from pathlib import Path
b=Path(r"C:\Users\Steve\.cp-scratch\cad-full-ui-22")
j=b/"paper-render-1";h=b/"paper-render-1-host";h.mkdir()
def write(name,v):(h/name).write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8",newline="\n")
(h/"SCRIPT.py").write_bytes(Path(__file__).read_bytes())
cmd=["docker","create","--name","ict-cad-full22-paper-render-1","--network","none","--user","1001:1001","--memory","2g","--cpus","1","--pids-limit","256","--cap-drop","ALL","--security-opt","no-new-privileges","--mount","type=bind,source="+j.as_posix()+",target=/work","--entrypoint","python3","sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8","/work/render_paper.py"]
write("COMMAND.json",cmd)
r=subprocess.run(cmd,capture_output=True,text=True);write("CREATE.json",dict(exit=r.returncode,stdout=r.stdout,stderr=r.stderr));r.check_returncode()
name="ict-cad-full22-paper-render-1"
write("BEFORE.json",json.loads(subprocess.check_output(["docker","inspect",name])))
print("Paper container created",r.stdout.strip(),flush=True)
with (h/"stdout.txt").open("wb") as out,(h/"stderr.txt").open("wb") as err:r=subprocess.run(["docker","start","-a",name],stdout=out,stderr=err)
write("EXIT.json",dict(exit=r.returncode));write("AFTER.json",json.loads(subprocess.check_output(["docker","inspect",name])))
print("Original paper host exit",r.returncode,flush=True);sys.exit(r.returncode)
