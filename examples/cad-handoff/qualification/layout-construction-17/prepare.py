"""Stage the declared six exposed source files and complete native observation method before freezing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=ROOT/'examples/cad-handoff/qualification/header-boundaries-16'
MODES=['observe','preset-a','preset-b','tab-only']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prior',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args();old=args.prior;out=args.out
    if out.exists():raise ValueError('Use a new preparation folder')
    prior=json.loads((old/'FREEZE.json').read_bytes())
    out.mkdir();(out/'cases').mkdir();jobs=[]
    for name,pin in sorted(prior['inputs'].items()):
        if not(name.startswith('cases/')and name.endswith('/source.dxf')):continue
        if sha(old/name)!=pin:raise ValueError('Different exposed source: '+name)
        dest=out/name;dest.parent.mkdir(parents=True);shutil.copyfile(old/name,dest)
        for importer in ('OpenDesign','dxflib'):
            jobs.append(dict(id=dest.parent.name+'/'+importer,input='/work/'+name,importer=importer))
    for importer in ('OpenDesign','dxflib'):jobs.append(dict(id='empty/'+importer,input=None,importer=importer))
    write(out/'jobs.json',dict(jobs=jobs))
    shutil.copyfile(OLD/'KEYS.json',out/'KEYS.json')
    for name in ('layout_ctor.cpp','run_native.py','PLAN.md'):shutil.copyfile(HERE/name,out/name)
    (out/'.configuration').mkdir();shutil.copyfile(old/'.configuration/QCAD3.conf',out/'.configuration/QCAD3.conf')
    prefix=(OLD/'native_headers.js').read_text(encoding='utf-8').split('var importFilters,exportFilters;')[0]
    suffix=r'''
try {
 var filters=RFileImporterRegistry.getFilterStrings();
 print('ICT_LAYOUT17_PROFILE '+JSON.stringify({configuration_file:String(RSettings.getFileName()),
   qt:String(RSettings.getQtVersionString()),observer:'native-getters'}));
 var detached=new RLayout(),props=[];
 for(var j=0;j<keys.layout_getters.length;j++){var getter=keys.layout_getters[j];props.push({getter:getter,value:value(detached[getter](),0)});}
 props.push({getter:'getTabOrder',value:value(detached.getTabOrder(),0)});
 print('ICT_LAYOUT17_DETACHED '+JSON.stringify({properties:props}));
 var jobs=readJson('/work/jobs.json').jobs;
 for(var i=0;i<jobs.length;i++){
  var job=jobs[i],di;
  try {
   var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel());di=new RDocumentInterface(d);
   var initial=inventory(d),filter=chooseFilter(filters,job.importer,null),code=null;
   if(job.input!==null)code=di.importFile(job.input,filter);
   print('ICT_LAYOUT17_JOB '+JSON.stringify({id:job.id,filter:filter,import_code:code,initial:initial,imported:inventory(d)}));
  } catch(err){print('ICT_LAYOUT17_JOB '+JSON.stringify({id:job.id,error:String(err)}));}
  finally{if(di)di.destroy();}
 }
}catch(err){print('ICT_LAYOUT17_FATAL '+String(err));}
'''
    (out/'native_layouts.js').write_text(prefix+suffix,encoding='utf-8',newline='\n')
    write(out/'PREPARED.json',dict(prior_inputs=prior['inputs'],configuration_sha256=prior['configuration_sha256'],
        runtime_image=prior['image'],compiler_image='sha256:10eed1af091798666a93fbe6e2cf438bdd3a950cb87d12487eea83ab0859e85e',
        library_sha256='cf911e2ae0fc8d4ab65ec9fccdc82f6ca2aaaa0c62973041df115b17b2f7d5ac',modes=MODES,
        cases=6,jobs_per_mode=14,detached_per_mode=1,whole_cad_qualified=False))
    print('Prepared',out)

if __name__=='__main__':main()
