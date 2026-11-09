// Waiting poll: one live asynchronous child during idle time; client owns posted-request deadline.
include('scripts/EAction.js');
include('/work/payload.js');
var runAsyncBridge21=null, seqAsyncBridge21=0, callAsyncBridge21=0, seenAsyncBridge21={};
var processAsyncBridge21=null, busyAsyncBridge21=false, failedAsyncBridge21=false;
var timerAsyncBridge21=new QTimer();
function asciiAsyncBridge21(value){return JSON.stringify(value).replace(/[\u007f-\uffff]/g,function(c){return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4);});}
function decodeAsyncBridge21(bytes){var stream=new QTextStream(bytes,new QIODevice.OpenMode(1));stream.setCodec('UTF-8');return stream.readAll();}
function failAsyncBridge21(error){
 if(failedAsyncBridge21)return;
 failedAsyncBridge21=true;timerAsyncBridge21.stop();
 print('ICT_MAILBOX_FATAL '+asciiAsyncBridge21({run_id:runAsyncBridge21,seq:seqAsyncBridge21+1,call_id:callAsyncBridge21,error:String(error)}));
}
function callAsyncIO21(operation,extra,done){
 if(busyAsyncBridge21||failedAsyncBridge21)throw new Error('Overlapping or post-failure helper invocation');
 var call={io_protocol:'ict-native-io/1',call_id:++callAsyncBridge21,operation:operation,run_id:runAsyncBridge21,seq:seqAsyncBridge21+1,seen:seenAsyncBridge21};
 if(extra)for(var key in extra)call[key]=extra[key];
 var input=asciiAsyncBridge21(call);if(input.length>60000)throw new Error('Bounded helper argument exceeded');
 var id=callAsyncBridge21, child=new QProcess(), deadline=new QTimer();deadline.singleShot=true;
 processAsyncBridge21=child;busyAsyncBridge21=true;
 print('ICT_IO_START '+asciiAsyncBridge21({call_id:id,input_wire:input}));
 deadline.timeout.connect(function(){failAsyncBridge21('Helper observation timeout; retain same native/helper process');});
 child.errorOccurred.connect(function(error){failAsyncBridge21('Actual QProcess error '+Number(error));});
 child['finished(int,QProcess::ExitStatus)'].connect(function(code,status){
  deadline.stop();
  try{
   var stdout=decodeAsyncBridge21(child.readAllStandardOutput()),stderr=decodeAsyncBridge21(child.readAllStandardError());
   var terminal={call_id:id,exit:Number(code),exit_status:Number(status),stdout:stdout,stderr:stderr};
   print('ICT_IO_END '+asciiAsyncBridge21(terminal));
   busyAsyncBridge21=false;
   if(failedAsyncBridge21)return; // A later termination cannot promote the expired observation.
   if(stdout.length>65536||stderr!=='')throw new Error('Helper output bound/stderr differs');
   var result=JSON.parse(stdout);
   if(result.io_protocol!=='ict-native-io/1'||result.call_id!==id||(runAsyncBridge21!==null&&result.run_id!==runAsyncBridge21))throw new Error('Helper response identity differs');
   if(result.ok!==true||terminal.exit!==0||terminal.exit_status!==0)throw new Error('Helper failed: '+stdout);
   done(result);
  }catch(error){failAsyncBridge21(error);}
 });
 child.setProgram('/usr/bin/python3');child.setArguments(['/work/native_io.py',input]);
 if(operation!=='poll')deadline.start(5000);child.start(new QIODevice.OpenMode(3));
}
timerAsyncBridge21.timeout.connect(function(){
 if(busyAsyncBridge21||failedAsyncBridge21)return;
 try{
  if(runAsyncBridge21===null){callAsyncIO21('initialize',null,function(result){runAsyncBridge21=result.run_id;});return;}
  callAsyncIO21('poll',null,function(next){
   if(next.status==='idle')return;
   if(next.status==='stopped'){timerAsyncBridge21.stop();print('ICT_IO_STOPPED '+asciiAsyncBridge21({run_id:runAsyncBridge21,call_id:callAsyncBridge21}));return;}
   if(next.status!=='request')throw new Error('Unexpected poll status');
   var request=next.request,body=request.body,observation,extra={request_wire:next.request_wire};
   try{
    if(body.action==='seal'){
     if(Object.keys(body).join(',')!=='action')throw new Error('Unsupported transport seal body');
     observation=payload21({action:'status'},request.seq);observation.request={seq:request.seq,action:'seal'};
    }else observation=payload21(body,request.seq);
    extra.observation=observation;
   }catch(nativeError){extra.native_error={message:String(nativeError),stage:'native-observation'};}
   callAsyncIO21('publish',extra,function(){
    seenAsyncBridge21[('00000000'+request.seq).slice(-8)+'.json']=next.request_sha256;seqAsyncBridge21++;
    if(body.action==='seal'){timerAsyncBridge21.stop();print('ICT_IO_SEALED '+asciiAsyncBridge21({run_id:runAsyncBridge21,seq:seqAsyncBridge21,call_id:callAsyncBridge21}));}
   });
  });
 }catch(error){failAsyncBridge21(error);}
});timerAsyncBridge21.start(250);
