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
 var ids=d.queryAllObjects(),objects=[],names=d.getVariables(),variables=[];
 for(var n=0;n<names.length;n++)variables.push({name:String(names[n]),value:value(d.getVariable(names[n]),0)});
 variables.sort(function(a,b){return a.name<b.name?-1:a.name>b.name?1:0;});
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
 return {file_version:String(d.getFileVersion()),variables:variables,known:{USERI5:value(d.getKnownVariable(RS.USERI5),0)},objects:objects};
}
function chooseFilter(list,word,version){
 var found=[];
 var exact=word==='OpenDesign'?'All CAD Files [OpenDesign] (*.dxf *.dwg *.dwt *.dxb *.dgn *.dwf)':'DXF Files [dxflib] (*.dxf)';
 for(var i=0;i<list.length;i++){var s=String(list[i]);if(version?(s.indexOf('['+word+']')>=0&&s.indexOf('*.dxf')>=0&&s.indexOf(version+' [')===0):s===exact)found.push(s);}
 if(found.length!==1)throw new Error('Ambiguous/missing '+word+' '+version+' filter: '+JSON.stringify(found));
 return found[0];
}
var importFilters,exportFilters;
function opened(path,filter){
 var d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel()),di=new RDocumentInterface(d),initial=inventory(d);
 if(path!==null && di.importFile(path,filter)!==RDocumentInterface.IoErrorNoError){di.destroy();throw new Error('Native import failed: '+path);}
 return {doc:d,di:di,initial:initial};
}
function execute(job,readOnly){
 var inputFilter=chooseFilter(importFilters,job.importer,null),outputFilter=chooseFilter(exportFilters,job.exporter,job.version);
 var o=opened(readOnly?job.output:job.input,inputFilter),r={id:job.id,import_filter:inputFilter,export_filter:outputFilter,initial:o.initial,imported:inventory(o.doc)};
 try{
  if(!readOnly){
   if(job.rename){
    var block=o.doc.queryBlock(job.rename.before);
    if(!block||block.getName()!==job.rename.before)throw new Error('Missing exact block to rename');
    block.setName(job.rename.after);
    var op=new RAddObjectsOperation();op.addObject(block,false);o.di.applyOperation(op);
   }
   r.after_operation=inventory(o.doc);
   if(new QFileInfo(job.output).exists())throw new Error('Existing output must be retained');
   if(!o.di.exportFile(job.output,outputFilter))throw new Error('Export failed for '+outputFilter);
   r.after_export=inventory(o.doc);
  }
 }catch(error){r.error=String(error);}finally{o.di.destroy();}
 if(r.error)return r;
 if(!readOnly){var again=opened(job.output,inputFilter);try{r.reopened=inventory(again.doc);}finally{again.di.destroy();}}
 return r;
}
try{
 var selected=String(RSettings.getFileName());
 importFilters=RFileImporterRegistry.getFilterStrings();exportFilters=RFileExporterRegistry.getFilterStrings();
 print('ICT_RECORD15_PROFILE '+JSON.stringify({configuration_file:selected,qt_version:String(RSettings.getQtVersionString()),
  importer_filters:importFilters,exporter_filters:exportFilters}));
 if(selected!=='/home/cad/.config/QCAD/QCAD3.conf')throw new Error('Wrong selected settings');
 var m=readJson(getArgument(args,'-m','-manifest'));
 for(var i=0;i<m.jobs.length;i++){
  var result;try{result=execute(m.jobs[i],m.read_only===true);}catch(error){result={id:m.jobs[i].id,error:String(error)};}
  print('ICT_RECORD15 '+JSON.stringify(result));
 }
}catch(error){print('ICT_RECORD15_FATAL '+String(error));}
