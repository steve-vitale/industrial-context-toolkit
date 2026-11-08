// Isolated native glyph-path raster controls. No drawing export or GUI acceptance.
include("scripts/simple.js");
function readJson(path){var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error("Read failed");var t=new QTextStream(f).readAll();f.close();return JSON.parse(t);}
try {
 var config=String(RSettings.getFileName());print("ICT_PIXEL12_PROFILE "+JSON.stringify({configuration_file:config}));
 if(config!=="/home/cad/.config/QCAD/QCAD3.conf")throw new Error("Wrong selected settings");

 var probe=new QImage(32,32,QImage.Format_RGB32);probe.fill(new QColor(0,0,0));
 var control=new QPainter();if(!control.begin(probe))throw new Error('Device control begin failed');
 control.fillRect(0,0,16,16,new QColor(255,255,0));control.end();probe.save('/work/images/device-control.png');
 print('ICT_PIXEL12_DEVICE '+JSON.stringify({pixel:Number(probe.pixel(4,4)),expected_yellow:Number(new QColor(255,255,0).rgb())}));
 var m=readJson('/work/PIXEL-INPUTS.json');
 for(var role in m.drawings) {
  var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d);
  if(di.importFile('/work/'+m.drawings[role])!==RDocumentInterface.IoErrorNoError)throw new Error("Import failed");
  var ids=d.queryAllEntities(),found=[];
  for(var i=0;i<ids.length;i++){var e=d.queryEntity(ids[i]);if(e.getType()===RS.EntityAttribute && e.getTag()==='MODEL')found.push(e);}
  if(found.length!==1)throw new Error("MODEL not unique");
  var data=found[0].getData(),paths=data.getPainterPaths(false),bounds=found[0].getBoundingBox();
  print('ICT_PIXEL12_GLYPH '+JSON.stringify({role:role,text:String(data.getText()),font:String(data.getFontName()),
   bounds:[bounds.getMinimum().x,bounds.getMinimum().y,bounds.getMaximum().x,bounds.getMaximum().y],paths:paths.length}));
  for(var z=0;z<paths.length;z++)print('ICT_PIXEL12_PATH '+JSON.stringify({role:role,index:z,elements:paths[z].elementCount(),feature_size:paths[z].getFeatureSize(),box:String(paths[z].boundingRect())}));
  for(var k=0;k<m.profiles.length;k++) {
   var pr=m.profiles[k],view=m.view,img=new QImage(view.width,view.height,QImage.Format_RGB32);img.fill(new QColor(0,0,0));
   var painter=new QPainter(),transform=new QTransform();if(!painter.begin(img))throw new Error("Painter begin failed");
   transform.scale(1,-1);transform.translate(0,-view.height);transform.scale(view.factor,view.factor);transform.translate(view.offset[0],view.offset[1]);
   print('ICT_PIXEL12_TRANSFORM '+JSON.stringify({role:role,profile:pr.id,transform:String(transform),mapped:String(transform.map(new QPointF(18,18.6)))}));
   painter.setTransform(transform);painter.setRenderHint(QPainter.Antialiasing,pr.antialiasing);
   var pen=new QPen(new QColor(255,255,0));pen.setWidthF(pr.width);pen.setCosmetic(true);pen.setCapStyle(pr.cap==='round'?Qt.RoundCap:Qt.SquareCap);pen.setJoinStyle(Qt.RoundJoin);
   painter.setPen(pen);painter.setBrush(Qt.NoBrush);var drawn=0;
   for(var j=0;j<paths.length;j++){if(paths[j].getFeatureSize()<0)continue;painter.drawPath(paths[j]);drawn++;}
   painter.end();var output='/work/images/'+role+'-'+pr.id+'.png';
   if(new QFileInfo(output).exists())throw new Error('Existing image');if(!img.save(output))throw new Error('Image save failed');
   print('ICT_PIXEL12 '+JSON.stringify({role:role,profile:pr.id,drawn_paths:drawn,output:output}));
  }
  di.destroy();
 }
}catch(e){print('ICT_PIXEL12_FATAL '+String(e));}
