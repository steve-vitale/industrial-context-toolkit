// Appended to the unchanged header16 inventory prefix by prepare.py.
include('scripts/EAction.js');
include('scripts/File/NewFile/NewFile.js');
include('scripts/File/Print/Print.js');
function windows(){return EAction.getMdiArea().subWindowList().length;}
function events(){for(var n=0;n<5;n++)QCoreApplication.processEvents();}
function printValues(d){
 var names=['getPaperWidth','getPaperHeight','getPaperUnit','getPaperSizeMM','getPaperSizeName',
            'getPageOrientationString','getScale','getOffset'],out=[];
 for(var i=0;i<names.length;i++){
  if(typeof Print[names[i]]!=='function')throw new Error('Unsupported Print getter '+names[i]);
  var v=Print[names[i]](d);
  out.push({getter:names[i],value:names[i]==='getPaperSizeMM'?
    {type:'QSizeF',value:[value(v.width(),0),value(v.height(),0)]}:value(v,0)});
 }
 return out;
}
function execute18(job,route){
 var filter=chooseFilter(RFileImporterRegistry.getFilterStrings(),job.importer,null);
 var row={id:job.id,route:route,filter:filter,windows_before:windows()},d,di,w;
 try{
  if(route==='bare'){
   d=new RDocument(new RMemoryStorage(),new RSpatialIndexNavel());di=new RDocumentInterface(d);
   row.import_code=job.input===null?null:di.importFile(job.input,filter);
   if(job.input!==null&&row.import_code!==RDocumentInterface.IoErrorNoError)throw new Error('Native import failed');
  }else{
   w=NewFile.createMdiChild(job.input===null?undefined:job.input,filter,undefined,undefined,true);
   if(isNull(w))throw new Error('Native MDI document unavailable');
   di=w.getDocumentInterface();d=w.getDocument();
  }
  row.loaded_file=String(d.getFileName());row.windows_open=windows();
  row.has_view=!isNull(di.getLastKnownViewWithFocus());row.modified_open=d.isModified();
  row.opened=inventory(d);events();row.noop=inventory(d);
  row.print_values=printValues(d);row.after_print=inventory(d);row.modified_after_print=d.isModified();
 }catch(err){row.error=String(err);}
 finally{
  if(w){d.setModified(false);row.close_result=w.close();events();}
  else if(di)di.destroy();
  row.windows_after=windows();
 }
 return row;
}
var timer18=new QTimer(),started18=false;
timer18.timeout.connect(function(){
 if(started18)return;started18=true;timer18.stop();
 try{
  var run=readJson('/work/current.json'),jobs=readJson('/work/jobs.json').jobs;
  print('ICT_OPEN18_PROFILE '+JSON.stringify({configuration_file:String(RSettings.getFileName()),
   qt:String(RSettings.getQtVersionString()),gui:RSettings.isGuiEnabled(),route:run.route,mode:run.mode}));
  for(var i=0;i<jobs.length;i++)print('ICT_OPEN18_JOB '+JSON.stringify(execute18(jobs[i],run.route)));
  print('ICT_OPEN18_DONE '+JSON.stringify({jobs:jobs.length,route:run.route,mode:run.mode}));
 }catch(err){print('ICT_OPEN18_FATAL '+String(err));}
 // Cleanup does not save: all observed documents were explicitly discarded.
 var ws=EAction.getMdiArea().subWindowList();
 for(var j=0;j<ws.length;j++){ws[j].getDocument().setModified(false);ws[j].close();}
 QCoreApplication.quit();
});
timer18.start(250);
