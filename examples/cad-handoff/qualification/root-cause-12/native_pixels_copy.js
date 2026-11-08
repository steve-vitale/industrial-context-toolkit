// Isolated native glyph-path raster controls. No drawing export or GUI acceptance.
include("scripts/simple.js");
function readJson(path){var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error("Read failed");var t=new QTextStream(f).readAll();f.close();return JSON.parse(t);}
try {
 var config=String(RSettings.getFileName());print("ICT_PIXEL12_PROFILE "+JSON.stringify({configuration_file:config}));
 if(config!=="/home/cad/.config/QCAD/QCAD3.conf")throw new Error("Wrong selected settings");
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

  var qtpaths=[],retained=[];
  for(var z=0;z<paths.length;z++) {
   if(paths[z].getFeatureSize()<0)continue;
   var count=paths[z].getElementCount(),qp=new QPainterPath(),elements=[];
   if(count<=0 || count>100000)throw new Error('Invalid native wrapper element count');
   for(var el=0;el<count;el++)elements.push([Number(paths[z].getTypeAt(el)),paths[z].getXAt(el),paths[z].getYAt(el)]);
   for(var el=0;el<elements.length;el++) {
    var v=elements[el];
    if(v[0]===0)qp.moveTo(v[1],v[2]);
    else if(v[0]===1)qp.lineTo(v[1],v[2]);
    else if(v[0]===2 && el+2<elements.length && elements[el+1][0]===3 && elements[el+2][0]===3){qp.cubicTo(v[1],v[2],elements[el+1][1],elements[el+1][2],elements[el+2][1],elements[el+2][2]);el+=2;}
    else throw new Error('Unsupported native element sequence');
   }
   if(qp.elementCount()!==count)throw new Error('Copied Qt path count differs');
   qtpaths.push(qp);retained.push(elements);
  }
  print('ICT_PIXEL12_ELEMENTS '+JSON.stringify({role:role,paths:retained}));
  for(var k=0;k<m.profiles.length;k++) {
   var pr=m.profiles[k],view=m.view,img=new QImage(view.width,view.height,QImage.Format_RGB32);img.fill(new QColor(0,0,0));
   var painter=new QPainter(),transform=new QTransform();if(!painter.begin(img))throw new Error("Painter begin failed");
   transform.scale(1,-1);transform.translate(0,-view.height);transform.scale(view.factor,view.factor);transform.translate(view.offset[0],view.offset[1]);
   painter.setTransform(transform);painter.setRenderHint(QPainter.Antialiasing,pr.antialiasing);
   var pen=new QPen(new QColor(255,255,0));pen.setWidthF(pr.width);pen.setCosmetic(true);pen.setCapStyle(pr.cap==='round'?Qt.RoundCap:Qt.SquareCap);pen.setJoinStyle(Qt.RoundJoin);
   painter.setPen(pen);painter.setBrush(Qt.NoBrush);var drawn=0;
   for(var j=0;j<qtpaths.length;j++){painter.drawPath(qtpaths[j]);drawn++;}
   painter.end();var output='/work/images/'+role+'-'+pr.id+'.png';
   if(new QFileInfo(output).exists())throw new Error('Existing image');if(!img.save(output))throw new Error('Image save failed');
   print('ICT_PIXEL12 '+JSON.stringify({role:role,profile:pr.id,drawn_paths:drawn,output:output}));
  }
  di.destroy();
 }
}catch(e){print('ICT_PIXEL12_FATAL '+String(e));}
