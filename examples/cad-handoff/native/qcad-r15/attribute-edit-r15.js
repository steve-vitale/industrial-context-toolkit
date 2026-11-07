// Bounded public-fixture native engine experiment; not an interactive receiving test.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
function readJson(path) {
 var f=new QFile(path); if(!f.open(QIODevice.ReadOnly)) throw new Error("Cannot read JSON");
 var text=new QTextStream(f).readAll(); f.close(); return JSON.parse(text);
}
function attributes(doc) {
 var ids=doc.queryAllEntities(), groups={};
 for(var i=0;i<ids.length;i++) {
  var e=doc.queryEntity(ids[i]);
  if(e.getType()!==RS.EntityAttribute) continue;
  var parent=String(e.getParentId()); if(!groups[parent])groups[parent]={};
  var tag=e.getTag(); if(groups[parent][tag])throw new Error("Duplicate attribute");
  groups[parent][tag]={entity:e,value:e.getPlainText()};
 }
 return groups;
}
function values(groups) {
 var result=[];
 for(var parent in groups) {var row={parent:parent,attributes:{}};for(var tag in groups[parent]) row.attributes[tag]=groups[parent][tag].value;result.push(row);}
 return result;
}
function openDoc(path) {
 var doc=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(doc);
 if(di.importFile(path)!==RDocumentInterface.IoErrorNoError){di.destroy();throw new Error("Import failed");}
 return {doc:doc,di:di};
}
function main() {
 var input=getArgument(args,"-i","-input"), output=getArgument(args,"-o","-output"), plan=readJson(getArgument(args,"-p","-plan"));
 if(new QFileInfo(output).exists())throw new Error("Output exists");
 var opened=openDoc(input), groups=attributes(opened.doc), before=values(groups), op=new RModifyObjectsOperation();
 for(var i=0;i<plan.changes.length;i++) {
  var c=plan.changes[i], matches=[];
  for(var parent in groups)if(groups[parent].ICT_ID && groups[parent].ICT_ID.value===c.id)matches.push(groups[parent]);
  if(matches.length!==1)throw new Error("Identity not unique");
  var a=matches[0][c.attribute];if(!a || a.value!==c.before)throw new Error("Stale before value");
  if(!a.entity.setProperty(RAttributeEntity.PropertyText,c.after))throw new Error("Property unchanged");
  op.addObject(a.entity);
 }
 opened.di.applyOperation(op);
 if(!opened.di.exportFile(output,"R15"))throw new Error("Export failed");
 opened.di.destroy();
 var returned=openDoc(output), after=values(attributes(returned.doc));
 print("ICT_NATIVE_READBACK "+JSON.stringify({before:before,after:after}));
 returned.di.destroy();
}
try {main();}catch(e){print("ICT_NATIVE_ERROR "+e);}
