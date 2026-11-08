// Read-only native inventory and frozen absolute view recipe, from the exposed UI19/camera20 methods.
function bounds19(e){var b=e.getBoundingBox(),a=b.getMinimum(),z=b.getMaximum();return [a.x,a.y,z.x,z.y];}
function payload21(body,seq){
 if(body===null||typeof body!=='object'||body instanceof Array)throw new Error('Invalid request body');
 var keys=Object.keys(body).sort().join(',');
 if(body.action==='status'&&keys!=='action')throw new Error('Unsupported status body');
 if(body.action==='frame'&&keys!=='action,expected_path,frame')throw new Error('Unsupported frame body');
 var r={seq:seq};for(var key in body)r[key]=body[key];
  var di=EAction.getDocumentInterface(),d=isNull(di)?undefined:di.getDocument();
  var out={request:r,configuration_file:String(RSettings.getFileName()),qt:String(RSettings.getQtVersionString()),
           filename:isNull(d)?null:String(d.getFileName()),modified:isNull(d)?null:d.isModified()};
  if(r.action==='frame'){
   if(isNull(d)||out.filename!==r.expected_path)throw new Error('Wrong drawing for camera request');
   var b=r.frame;if(!(b instanceof Array)||b.length!==4||b.some(function(v){return typeof v!=='number'||!isFinite(v);})||b[0]>=b[2]||b[1]>=b[3])throw new Error('Invalid frame');
   var cameraView=di.getLastKnownViewWithFocus();if(isNull(cameraView))throw new Error('No native camera view');
   var high=RSettings.getHighResolutionGraphicsView(),margin=high?48:24,W=cameraView.getWidth(),H=cameraView.getHeight();
   var f=Math.min((W-2*margin)/(b[2]-b[0]),(H-2*margin)/(b[3]-b[1]));
   if(!isFinite(f)||f<1e-6||f>1e6)throw new Error('Unsupported absolute factor');
   var offset=[W/(2*f)-(b[0]+b[2])/2,H/(2*f)-(b[1]+b[3])/2];
   cameraView.setFactor(f);cameraView.setOffset(new RVector(offset[0],offset[1]));
   out.camera_control={factor:f,offset:offset,high_resolution:high,margin:margin,width:W,height:H};
   di.repaintViews();
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
  return out;
}
