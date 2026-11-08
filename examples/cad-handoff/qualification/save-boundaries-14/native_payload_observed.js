// Public native object/version observations and no-operation exports. No UI qualification.
include('scripts/simple.js');
include('scripts/Tools/arguments.js');
function readJson(path){var f=new QFile(path);if(!f.open(QIODevice.ReadOnly))throw new Error('Cannot read '+path);var s=new QTextStream(f).readAll();f.close();return JSON.parse(s);}
function value(v,depth){
 if(depth>8)return {type:'unsupported-depth',display:String(v)};
 if(v===null)return {type:'null',value:null};
 var kind=typeof v;
 if(kind==='undefined')return {type:'undefined'};
 if(kind==='string'||kind==='boolean')return {type:kind,value:v};
 if(kind==='number'){if(!isFinite(v))return {type:'nonfinite',display:String(v)};return {type:'number',value:v};}
 if(v instanceof Array){var a=[];for(var i=0;i<v.length;i++)a.push(value(v[i],depth+1));return {type:'array',value:a};}
 if(v instanceof RVector)return {type:'RVector',value:[v.x,v.y,v.z]};
 return {type:'unsupported-native-value',display:String(v)};
}
function inventory(d){
 var ids=d.queryAllObjects(),objects=[];
 for(var i=0;i<ids.length;i++){
  var o=d.queryObject(ids[i]),titles=o.getCustomPropertyTitles(),custom=[];
  for(var j=0;j<titles.length;j++){
   var keys=o.getCustomPropertyKeys(titles[j]);
   for(var k=0;k<keys.length;k++)custom.push({title:String(titles[j]),key:String(keys[k]),value:value(o.getCustomProperty(titles[j],keys[k]),0)});
  }
  var named=typeof o.getName==='function';
  objects.push({id:String(ids[i]),handle:Number(o.getHandle()).toString(16).toUpperCase(),type:Number(o.getType()),
   name_accessor:named,name:named?String(o.getName()):null,custom:custom,
   attribute:o.getType()===RS.EntityAttribute?{parent:String(o.getParentId()),tag:String(o.getTag()),
    text:String(o.getData().getText()),layer_id:String(o.getLayerId())}:null});
 }
 return {file_version:String(d.getFileVersion()),known:{USERI5:value(d.getKnownVariable(RS.USERI5),0)},objects:objects};
}
function opened(path){
 var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d),initial=inventory(d);
 if(path!==null && di.importFile(path)!==RDocumentInterface.IoErrorNoError){di.destroy();throw new Error('Native import failed: '+path);}
 return {doc:d,di:di,initial:initial};
}
function execute(job,readOnly){
 var o=opened(readOnly?job.output:job.input),r={id:job.id,initial:o.initial,imported:inventory(o.doc)};
 try{
  if(!readOnly){
   if(new QFileInfo(job.output).exists())throw new Error('Existing output must be retained');
   if(!o.di.exportFile(job.output,job.format))throw new Error('Export failed for '+job.format);
   r.after_export=inventory(o.doc);
  }
 }finally{o.di.destroy();}
 if(!readOnly){var again=opened(job.output);try{r.reopened=inventory(again.doc);}finally{again.di.destroy();}}
 return r;
}
try{
 var selected=String(RSettings.getFileName());
 print('ICT_BOUND14_PROFILE '+JSON.stringify({configuration_file:selected,qt_version:String(RSettings.getQtVersionString()),
  exporter_filters:RFileExporterRegistry.getFilterStrings()}));
 if(selected!=='/home/cad/.config/QCAD/QCAD3.conf')throw new Error('Wrong selected settings');
 var m=readJson(getArgument(args,'-m','-manifest'));
 for(var i=0;i<m.jobs.length;i++){
  var result;try{result=execute(m.jobs[i],m.read_only===true);}catch(error){result={id:m.jobs[i].id,error:String(error)};}
  print('ICT_BOUND14 '+JSON.stringify(result));if(result.error)throw new Error('Stop after failed job');
 }
}catch(error){print('ICT_BOUND14_FATAL '+String(error));}
