// Native read/import and camera observation only. No entity operation or drawing save/export.
include("scripts/EAction.js");
include("scripts/File/NewFile/NewFile.js");
function f9Read(path) {
    var f=new QFile(path);
    if(!f.open(QIODevice.ReadOnly)) throw new Error("Cannot read "+path);
    var t=new QTextStream(f); setUtf8Codec(t); var s=t.readAll(); f.close(); return JSON.parse(s);
}
function f9Write(path,value) {
    var f=new QFile(path);
    if(!f.open(QIODevice.WriteOnly)) throw new Error("Cannot write receipt "+path);
    var t=new QTextStream(f); setUtf8Codec(t); t.writeString(JSON.stringify(value)); f.close();
}
function f9Bounds(e) {
    var box=e.getBoundingBox(), a=box.getMinimum(), b=box.getMaximum();
    var r=[a.x,a.y,b.x,b.y];
    for(var i=0;i<4;i++) if(!isFinite(r[i])) throw new Error("Nonfinite native bounds");
    return r;
}
function f9Union(rows) {
    if(!rows.length) throw new Error("Empty native frame");
    var r=rows[0].slice();
    for(var i=1;i<rows.length;i++) {
        r[0]=Math.min(r[0],rows[i][0]);r[1]=Math.min(r[1],rows[i][1]);
        r[2]=Math.max(r[2],rows[i][2]);r[3]=Math.max(r[3],rows[i][3]);
    }
    return r;
}
function f9Font(name,text) {
    var r={requested:name,mapped:String(RFontList.getSubName(name)),cad_font:RFontList.isCadFont(name,"")};
    if(r.cad_font) {
        var f=RFontList.get(name,true); r.cad_path=String(f.getFileName());
        r.glyph_check="CAD font coverage will be checked from the pinned local CXF character headers";
    } else {
        var q=new QFont(r.mapped); r.resolved_family=String(new QFontInfo(q).family());
        try {
            var fm=new QFontMetrics(q), missing=[];
            for(var i=0;i<text.length;i++) if(!fm.inFont(text.charAt(i)) && missing.indexOf(text.charAt(i))<0) missing.push(text.charAt(i));
            r.missing_characters=missing; r.glyph_check="QFontMetrics.inFont";
        } catch(error) { r.glyph_check_error=String(error); }
    }
    return r;
}
function f9Inspect(path) {
    var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d);
    try {
        if(di.importFile(path)!==RDocumentInterface.IoErrorNoError) throw new Error("Native import failed");
        var ids=d.queryAllEntities(), groups={},parents={},all=[];
        for(var i=0;i<ids.length;i++) {
            var e=d.queryEntity(ids[i]);
            if(e.getBlockId()!==d.getModelSpaceBlockId()) continue;
            var box=f9Bounds(e);all.push(box);
            if(e.getType()!==RS.EntityAttribute) continue;
            var p=String(e.getParentId());
            if(!groups[p]) groups[p]=[];
            var text=String(e.getData().getText()),tag=String(e.getTag());
            groups[p].push({native_id:String(ids[i]),parent:p,tag:tag,text:text,bounds:box,
                            font:f9Font(String(e.getData().getFontName()),text)});
            parents[p]=f9Bounds(d.queryEntity(e.getParentId()));
        }
        var assets={};
        for(var parent in groups) {
            var identity=groups[parent].filter(function(a){return a.tag==="ICT_ID";});
            if(identity.length!==1 || assets[identity[0].text]) throw new Error("Ambiguous native identity");
            assets[identity[0].text]={attributes:groups[parent],insert_bounds:parents[parent]};
        }
        return {path:path,assets:assets,all_bounds:f9Union(all)};
    } finally {di.destroy();}
}
var f9Cache={},f9Last=-1,f9Timer=new QTimer();
f9Timer.timeout.connect(function() {
    var requestPath="/work/request.json";
    if(!new QFileInfo(requestPath).exists()) return;
    var request;
    try {
        request=f9Read(requestPath);
        if(request.seq===f9Last) return;
        f9Last=request.seq;
        var c=request.case_id;
        if(!f9Cache[c]) f9Cache[c]={source:f9Inspect(request.source),candidate:f9Inspect(request.candidate)};
        var pair=f9Cache[c], boxes=[];
        for(var roleIndex=0;roleIndex<2;roleIndex++) {
            var role=roleIndex===0?"source":"candidate", item=pair[role];
            if(request.asset_id==="__ALL__") boxes.push(item.all_bounds);
            else {
                var asset=item.assets[request.asset_id]; if(!asset) throw new Error("Missing requested native asset");
                boxes.push(asset.insert_bounds);
                for(var i=0;i<asset.attributes.length;i++) boxes.push(asset.attributes[i].bounds);
            }
        }
        var union=f9Union(boxes),pad=Math.max(2,.2*Math.max(union[2]-union[0],union[3]-union[1]));
        var frame=[union[0]-pad,union[1]-pad,union[2]+pad,union[3]+pad];
        var path=request[request.role],w=NewFile.createMdiChild(path);
        if(isNull(w)) throw new Error("Native document activation failed");
        var di=w.getDocumentInterface();
        di.clearPreview();
        di.zoomTo(new RBox(new RVector(frame[0],frame[1]),new RVector(frame[2],frame[3])),24);
        di.repaintViews();QCoreApplication.processEvents();
        var view=di.getLastKnownViewWithFocus();
        if(isNull(view)) throw new Error("Native view unavailable");
        var projected=[];
        for(var j=0;j<boxes.length;j++) {
            var a=view.mapToView(new RVector(boxes[j][0],boxes[j][1]));
            var b=view.mapToView(new RVector(boxes[j][2],boxes[j][3]));
            projected.push([Math.min(a.x,b.x),Math.min(a.y,b.y),Math.max(a.x,b.x),Math.max(a.y,b.y)]);
        }
        f9Write("/work/receipts/"+request.seq+".json",{request:request,pair:pair,union:union,frame:frame,
            loaded_file:String(w.getDocument().getFileName()),view:{width:view.getWidth(),height:view.getHeight(),factor:view.getFactor(),offset:[view.getOffset().x,view.getOffset().y]},projected:projected,
            role:"Read-only native imports and camera; no entity edit/save/export or UI editability claim"});
    } catch(error) {
        f9Timer.stop();f9Write("/work/failure.json",{request:request,error:String(error)});
    }
});
f9Timer.start(250);
