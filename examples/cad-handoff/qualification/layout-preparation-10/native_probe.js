// Read-only native import of the entire predeclared route cohort; no document save or UI claim.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
function p10Read(path) {
    var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error("Cannot read manifest");
    var t=new QTextStream(f);setUtf8Codec(t);var text=t.readAll();f.close();return JSON.parse(text);
}
function p10Write(path,data) {
    var f=new QFile(path);if(!f.open(QIODevice.WriteOnly))throw new Error("Cannot write native receipt");
    var t=new QTextStream(f);setUtf8Codec(t);t.writeString(JSON.stringify(data));f.close();
}
function p10Inspect(path) {
    var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d);
    try {
        if(di.importFile(path)!==RDocumentInterface.IoErrorNoError)throw new Error("Native import failed");
        var blocks=d.queryAllBlocks(),result=[],attributes=[];
        for(var i=0;i<blocks.length;i++) {
            var block=d.queryBlock(blocks[i]),ids=d.queryBlockEntities(blocks[i]);
            var row={name:String(block.getName()),layout:String(block.getLayoutName()),entities:[]};
            for(var j=0;j<ids.length;j++) {
                var e=d.queryEntity(ids[j]),entity={id:String(ids[j]),type:e.getType()};
                if(e.getType()===RS.EntityAttribute && e.getBlockId()===d.getModelSpaceBlockId()) {
                    attributes.push({tag:String(e.getTag()),text:String(e.getData().getText()),parent:String(e.getParentId())});
                }
                try {
                    var b=e.getBoundingBox(),a=b.getMinimum(),z=b.getMaximum();
                    entity.bounds=[a.x,a.y,z.x,z.y];
                    for(var k=0;k<4;k++)if(!isFinite(entity.bounds[k]))throw new Error("Nonfinite bounds");
                }catch(error){entity.bounds_error=String(error);delete entity.bounds;}
                row.entities.push(entity);
            }
            result.push(row);
        }
        return {layouts:result,attributes:attributes};
    }finally{di.destroy();}
}
try {
    var manifest=p10Read(getArgument(args,"-m","-manifest")),rows=[];
    for(var i=0;i<manifest.jobs.length;i++) {
        var job=manifest.jobs[i],row={id:job.id,path:job.path};
        try{row.observed=p10Inspect("/work/"+job.path);}catch(error){row.error=String(error);}
        rows.push(row);print("ICT_LAYOUT10 "+JSON.stringify(row));
        p10Write("/work/native-probe.json",{rows:rows});
    }
}catch(error){print("ICT_LAYOUT10_FATAL "+error);throw error;}
