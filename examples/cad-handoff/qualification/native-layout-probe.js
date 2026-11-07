// Read-only display diagnosis: enumerate actual imported blocks/layouts. No drawing writes or UI claim.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
function readJson(path) {
 var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error("Cannot read manifest");
 var text=new QTextStream(f).readAll();f.close();return JSON.parse(text);
}
function inspect(path) {
 var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d);
 try {
  if(di.importFile(path)!==RDocumentInterface.IoErrorNoError)throw new Error("Import failed");
  var blocks=d.queryAllBlocks(),result=[];
  for(var i=0;i<blocks.length;i++) {
   var block=d.queryBlock(blocks[i]),ids=d.queryBlockEntities(blocks[i]);
   var row={id:String(blocks[i]),name:String(block.getName()),layout:String(block.getLayoutName()),entities:[]};
   for(var j=0;j<ids.length;j++) {
    var e=d.queryEntity(ids[j]),item={id:String(ids[j]),type:e.getType()};
    try {
     var box=e.getBoundingBox(),a=box.getMinimum(),b=box.getMaximum();
     item.bounds=[a.x,a.y,b.x,b.y];
     for(var k=0;k<item.bounds.length;k++)if(!isFinite(item.bounds[k]))throw new Error("Nonfinite bounds");
    }catch(error){item.bounds_error=String(error);delete item.bounds;}
    if(e.getType()===RS.EntityAttribute){item.tag=String(e.getTag());item.text=String(e.getData().getText());item.parent=String(e.getParentId());}
    row.entities.push(item);
   }
   result.push(row);
  }
  return result;
 }finally{di.destroy();}
}
try {
 var manifest=readJson(getArgument(args,"-m","-manifest"));
 for(var i=0;i<manifest.cases.length;i++) {
  var c=manifest.cases[i],result={id:c.id};
  try{result.source=inspect(c.source);result.candidate=inspect(c.candidate);}catch(error){result.error=String(error);}
  print("ICT_LAYOUT_PROBE "+JSON.stringify(result));
 }
}catch(error){print("ICT_LAYOUT_FATAL "+error);}
