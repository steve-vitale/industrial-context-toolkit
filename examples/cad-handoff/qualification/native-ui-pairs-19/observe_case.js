// Read-only active-document observations plus declared camera; no document I/O or mutation actions.
include('scripts/EAction.js');
function read19(path){var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error('Cannot read request');
 var t=new QTextStream(f);t.setCodec('UTF-8');var s=t.readAll();f.close();return JSON.parse(s);}
function write19(path,v){var f=new QFile(path);if(!f.open(QIODevice.WriteOnly))throw new Error('Cannot write observation');
 var t=new QTextStream(f);t.setCodec('UTF-8');t.writeString(JSON.stringify(v));f.close();}
function bounds19(e){var b=e.getBoundingBox(),a=b.getMinimum(),z=b.getMaximum();return [a.x,a.y,z.x,z.y];}
var last19=-1,timer19=new QTimer();
timer19.timeout.connect(function(){
 if(!new QFileInfo('/work/request.json').exists())return;
 var r;
 try{
  r=read19('/work/request.json');if(r.seq===last19)return;last19=r.seq;
  var di=EAction.getDocumentInterface(),d=isNull(di)?undefined:di.getDocument();
  var out={request:r,configuration_file:String(RSettings.getFileName()),qt:String(RSettings.getQtVersionString()),
           filename:isNull(d)?null:String(d.getFileName()),modified:isNull(d)?null:d.isModified()};
  if(r.action==='frame'){
   if(isNull(d)||out.filename!==r.expected_path)throw new Error('Wrong drawing for camera request');
   var b=r.frame;if(!(b instanceof Array)||b.length!==4||b.some(function(v){return typeof v!=='number'||!isFinite(v);})||b[0]>=b[2]||b[1]>=b[3])throw new Error('Invalid frame');
   di.zoomTo(new RBox(new RVector(b[0],b[1]),new RVector(b[2],b[3])),24);di.repaintViews();
  }else if(r.action!=='status')throw new Error('Unsupported read-only request');
  if(!isNull(di)){
   var v=di.getLastKnownViewWithFocus();
   out.view=isNull(v)?null:{width:v.getWidth(),height:v.getHeight(),factor:v.getFactor(),offset:[v.getOffset().x,v.getOffset().y]};
   out.selected=d.querySelectedEntities();out.attributes=[];
   var ids=d.queryAllEntities();
   for(var i=0;i<ids.length;i++){
    var e=d.queryEntity(ids[i]);if(e.getType()!==RS.EntityAttribute||e.getBlockId()!==d.getModelSpaceBlockId())continue;
    var p=d.queryEntity(e.getParentId()),box=bounds19(e),a=isNull(v)?null:v.mapToView(new RVector(box[0],box[1])),z=isNull(v)?null:v.mapToView(new RVector(box[2],box[3]));
    out.attributes.push({parent_id:String(e.getParentId()),parent_handle:Number(p.getHandle()).toString(16).toUpperCase(),
      handle:Number(e.getHandle()).toString(16).toUpperCase(),tag:String(e.getTag()),text:String(e.getData().getText()),
      bounds:box,projected:isNull(v)?null:[Math.min(a.x,z.x),Math.min(a.y,z.y),Math.max(a.x,z.x),Math.max(a.y,z.y)]});
   }
  }
  write19('/work/replies/'+r.seq+'.json',out);
 }catch(err){write19('/work/replies/'+(r?r.seq:'unknown')+'.json',{request:r,error:String(err)});}
});timer19.start(250);
