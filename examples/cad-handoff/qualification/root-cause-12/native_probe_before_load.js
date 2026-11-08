// Matched no-operation / text-operation / second-save diagnosis. Not native UI acceptance.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
function readJson(path) {
 var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error("Cannot read JSON: "+path);
 var t=new QTextStream(f).readAll();f.close();return JSON.parse(t);
}
function objectHandles(d) {
 var ids=d.queryAllObjects(),r=[];
 for(var i=0;i<ids.length;i++){var e=d.queryObject(ids[i]);r.push({id:String(ids[i]),handle:Number(e.getHandle()).toString(16).toUpperCase(),type:Number(e.getType())});}
 return r;
}
function opened(path) {
 var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel(),true),di=new RDocumentInterface(d);
 var initial=objectHandles(d);
 if(di.importFile(path)!==RDocumentInterface.IoErrorNoError){di.destroy();throw new Error("Import failed: "+path);}
 print("ICT_ROOT12_DOCUMENT "+JSON.stringify({path:path,initial:initial,imported:objectHandles(d)}));
 return {doc:d,di:di};
}
function vector(p){return [p.x,p.y,p.z];}
function attributes(d) {
 var ids=d.queryAllEntities(),out=[];
 for(var i=0;i<ids.length;i++) {
  var e=d.queryEntity(ids[i]);if(e.getType()!==RS.EntityAttribute)continue;
  var data=e.getData();
  out.push({parent:String(e.getParentId()),handle:Number(e.getHandle()).toString(16).toUpperCase(),
   layer_id:String(e.getLayerId()),tag:String(e.getTag()),text:String(data.getText()),position:vector(data.getPosition()),
   alignment:vector(data.getAlignmentPoint()),halign:Number(data.getHAlign()),valign:Number(data.getVAlign()),
   font:String(data.getFontName()),font_file:String(data.getFontFile())});
 }
 return out;
}
function edit(o,plan) {
 var ids=o.doc.queryAllEntities(),groups={};
 for(var i=0;i<ids.length;i++) {
  var e=o.doc.queryEntity(ids[i]);if(e.getType()!==RS.EntityAttribute)continue;
  var p=String(e.getParentId()),tag=String(e.getTag());if(!groups[p])groups[p]={};
  if(groups[p][tag])throw new Error("Duplicate native tag");groups[p][tag]=e;
 }
 var op=new RModifyObjectsOperation();
 for(var j=0;j<plan.changes.length;j++) {
  var c=plan.changes[j],found=[];
  for(var p in groups)if(groups[p].ICT_ID && String(groups[p].ICT_ID.getData().getText())===c.id)found.push(groups[p]);
  if(found.length!==1)throw new Error("Native identity not unique");
  var a=found[0][c.attribute];if(!a || String(a.getData().getText())!==c.before)throw new Error("Stale before-value");
  if(!a.setProperty(RAttributeEntity.PropertyText,c.after))throw new Error("Property unchanged");op.addObject(a,false);
 }
 o.di.applyOperation(op);
}
function execute(job,readOnly) {
 var o=opened(readOnly?job.output:job.input),result={id:job.id,imported:attributes(o.doc)};
 try {
  if(!readOnly) {
   if(job.operation==="edit")edit(o,readJson(job.plan));
   else if(job.operation!=="none")throw new Error("Unsupported operation");
   result.before_export=attributes(o.doc);
   if(new QFileInfo(job.output).exists())throw new Error("Preserve existing native return");
   if(!o.di.exportFile(job.output,job.format))throw new Error("Native export failed");
   result.after_export=attributes(o.doc);
  }
 } finally {o.di.destroy();}
 if(!readOnly) {var r=opened(job.output);result.reopened=attributes(r.doc);r.di.destroy();}
 return result;
}
try {
 var path=String(RSettings.getFileName());
 print("ICT_ROOT12_PROFILE "+JSON.stringify({configuration_file:path,qt_version:String(RSettings.getQtVersionString())}));
 if(path!=="/home/cad/.config/QCAD/QCAD3.conf")throw new Error("Wrong selected configuration");
 var m=readJson(getArgument(args,"-m","-manifest"));
 for(var i=0;i<m.jobs.length;i++) {
  var r;try{r=execute(m.jobs[i],m.read_only===true);}catch(e){r={id:m.jobs[i].id,error:String(e)};}
  print("ICT_ROOT12 "+JSON.stringify(r));if(r.error)throw new Error("Stop after failed job");
 }
}catch(e){print("ICT_ROOT12_FATAL "+String(e));}
