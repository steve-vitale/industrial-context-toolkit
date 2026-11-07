// Read-only display diagnostic. No drawing export, edits or interactive-UI acceptance.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
function readJson(path) {
 var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error("Cannot read manifest");
 var text=new QTextStream(f).readAll();f.close();return JSON.parse(text);
}
function bounds(entity) {
 var box=entity.getBoundingBox(),a=box.getMinimum(),b=box.getMaximum();
 var ret=[a.x,a.y,b.x,b.y];
 for(var i=0;i<ret.length;i++)if(!isFinite(ret[i]))throw new Error("Nonfinite native entity bounds");
 return ret;
}
function inspect(path) {
 var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d);
 if(di.importFile(path)!==RDocumentInterface.IoErrorNoError){di.destroy();throw new Error("Import failed");}
 var ids=d.queryAllEntities(),result=[];
 for(var i=0;i<ids.length;i++) {
  var e=d.queryEntity(ids[i]),row={id:String(ids[i]),type:e.getType(),block:String(e.getBlockName())};
  if(e.getType()===RS.EntityAttribute) {
   row.parent=String(e.getParentId());row.tag=String(e.getTag());row.text=String(e.getData().getText());
  }
  try{row.bounds=bounds(e);}catch(error){row.bounds_error=String(error);}
  result.push(row);
 }
 di.destroy();return result;
}
try {
 var manifest=readJson(getArgument(args,"-m","-manifest"));
 for(var i=0;i<manifest.cases.length;i++) {
  var c=manifest.cases[i],result={id:c.id};
  try{result.source=inspect(c.source);result.candidate=inspect(c.candidate);}catch(error){result.error=String(error);}
  print("ICT_VIEW_BOUNDS "+JSON.stringify(result));
 }
}catch(error){print("ICT_VIEW_FATAL "+error);}
