// Authored qualification harness. QCAD native API only; no UI acceptance is inferred.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
function readJson(path) {
 var f=new QFile(path); if(!f.open(QIODevice.ReadOnly))throw new Error("Cannot read JSON");
 var text=new QTextStream(f).readAll();f.close();return JSON.parse(text);
}
function opened(path) {
 var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d);
 if(di.importFile(path)!==RDocumentInterface.IoErrorNoError){di.destroy();throw new Error("Import failed: "+path);}
 return {doc:d,di:di};
}
function rows(d) {
 var ids=d.queryAllEntities(),groups={};
 for(var i=0;i<ids.length;i++) {
  var e=d.queryEntity(ids[i]);if(e.getType()!==RS.EntityAttribute)continue;
  var parent=String(e.getParentId());if(!groups[parent])groups[parent]={};
  var tag=e.getTag();if(groups[parent][tag])throw new Error("Duplicate native attribute");
  // Stored DXF text and its formatted display are different evidence. Do not compare plain text to a raw plan.
  groups[parent][tag]={entity:e,value:String(e.getData().getText()),plain:String(e.getPlainText())};
 }
 return groups;
}
function values(groups) {
 var out=[];for(var p in groups) {
  var row={parent:p,attributes:{},plain_text:{}};
  for(var t in groups[p]){row.attributes[t]=groups[p][t].value;row.plain_text[t]=groups[p][t].plain;}
  out.push(row);
 }return out;
}
function readClosed(path) {
 var o=opened(path),result=values(rows(o.doc));o.di.destroy();return result;
}
function exportEdited(path,plan,output,version) {
 if(new QFileInfo(output).exists())throw new Error("Refuse existing return: "+output);
 var o=opened(path),groups=rows(o.doc),op=new RModifyObjectsOperation();
 for(var i=0;i<plan.changes.length;i++) {
  var c=plan.changes[i],matches=[];
  for(var p in groups)if(groups[p].ICT_ID && groups[p].ICT_ID.value===c.id)matches.push(groups[p]);
  if(matches.length!==1)throw new Error("Identity is not unique");
  var a=matches[0][c.attribute];if(!a || a.value!==c.before)throw new Error("Before value mismatch");
  if(!a.entity.setProperty(RAttributeEntity.PropertyText,c.after))throw new Error("Property did not change");
  op.addObject(a.entity);
 }
 o.di.applyOperation(op);
 if(!o.di.exportFile(output,version))throw new Error("Native export failed");
 o.di.destroy();return readClosed(output);
}
function main() {
 var manifest=readJson(getArgument(args,"-m","-manifest"));
 for(var i=0;i<manifest.cases.length;i++) {
  var c=manifest.cases[i],result={id:c.id};
  try {
   var plan=readJson(c.plan);
   result.source=readClosed(c.source);
   result.candidate=readClosed(c.candidate);
   if(!manifest.read_only) {
    try{result.native_default=exportEdited(c.source,plan,c.native_default,"");}
    catch(e){result.native_default_error=String(e);}
    try{result.native_r15=exportEdited(c.source,plan,c.native_r15,"R15");}
    catch(e){result.native_r15_error=String(e);}
   }
  }catch(e){result.error=String(e);}
  print("ICT_QUAL_NATIVE "+JSON.stringify(result));
 }
}
try{main();}catch(e){print("ICT_QUAL_FATAL "+e);}
