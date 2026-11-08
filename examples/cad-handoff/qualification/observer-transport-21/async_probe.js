// Installed signal/scheduling probe. No blocking waits or drawing open/edit/save.
include('scripts/EAction.js');
var asyncProcess21=null, asyncTicks21=0, asyncStarted21=false, asyncTerminal21=false;
var asyncPoll21=new QTimer(), asyncBeat21=new QTimer(), asyncDeadline21=new QTimer();
var asyncReport21={scope:'Exposed asynchronous capability probe; not CAD qualification',qt:String(RSettings.getQtVersionString())};
function asyncWrite21(name,value){
 var file=new QFile('/work/native/'+name);
 if(!file.open(QIODevice.WriteOnly))throw new Error('Cannot retain '+name);
 var stream=new QTextStream(file);stream.setCodec('UTF-8');stream.writeString(JSON.stringify(value)+'\n');file.close();
}
function asyncDecode21(bytes){var s=new QTextStream(bytes,new QIODevice.OpenMode(1));s.setCodec('UTF-8');return s.readAll();}
function asyncFail21(error){
 asyncPoll21.stop();asyncDeadline21.stop();
 print('ICT_ASYNC_FAILURE '+String(error));
 asyncWrite21('ASYNC-FAILURE.json',{error:String(error),ticks:asyncTicks21,started:asyncStarted21,terminal:asyncTerminal21});
}
asyncBeat21.timeout.connect(function(){asyncTicks21++;});asyncBeat21.start(20);
asyncDeadline21.singleShot=true;
asyncDeadline21.timeout.connect(function(){asyncFail21('Observation deadline; retain same native/helper process');});
asyncPoll21.timeout.connect(function(){
 if(!(new QFile('/work/native/ASYNC-START.json')).exists())return;
 asyncPoll21.stop();
 try{
  asyncProcess21=new QProcess();
  asyncReport21.signals={started:typeof asyncProcess21.started,finished:typeof asyncProcess21.finished,errorOccurred:typeof asyncProcess21.errorOccurred};
  asyncProcess21.started.connect(function(){asyncStarted21=true;asyncReport21.ticks_at_start=asyncTicks21;print('ICT_ASYNC_STARTED');});
  asyncProcess21.errorOccurred.connect(function(error){asyncFail21('QProcess error '+Number(error));});
  asyncProcess21['finished(int,QProcess::ExitStatus)'].connect(function(code,status){
   try{
    asyncTerminal21=true;asyncDeadline21.stop();asyncBeat21.stop();
    asyncReport21.exit=Number(code);asyncReport21.exit_status=Number(status);
    asyncReport21.stdout=asyncDecode21(asyncProcess21.readAllStandardOutput());
    asyncReport21.stderr=asyncDecode21(asyncProcess21.readAllStandardError());
    asyncReport21.started=asyncStarted21;asyncReport21.ticks_at_finish=asyncTicks21;
    var di=EAction.getDocumentInterface(),d=isNull(di)?undefined:di.getDocument();
    asyncReport21.filename=isNull(d)?null:String(d.getFileName());asyncReport21.modified=isNull(d)?null:d.isModified();
    print('ICT_ASYNC_FINISHED '+JSON.stringify(asyncReport21));asyncWrite21('ASYNC.json',asyncReport21);
   }catch(error){asyncFail21(error);}
  });
  asyncProcess21.setProgram('/usr/bin/python3');asyncProcess21.setArguments(['/work/async_helper.py']);
  asyncDeadline21.start(125000);asyncProcess21.start(new QIODevice.OpenMode(3));
 }catch(error){asyncFail21(error);}
});asyncPoll21.start(100);
