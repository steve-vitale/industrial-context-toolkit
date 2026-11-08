// Native read-only payload, private Python I/O owner, complete console call history.
include('scripts/EAction.js');
include('/work/payload.js');
var runBridge21=null, seqBridge21=0, callBridge21=0, seenBridge21={}, processBridge21=null;
var timerBridge21=new QTimer();
function asciiBridge21(value){return JSON.stringify(value).replace(/[\u007f-\uffff]/g,function(c){return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4);});}
function decodeBridge21(bytes){var stream=new QTextStream(bytes,new QIODevice.OpenMode(1));stream.setCodec('UTF-8');return stream.readAll();}
function callBridgeIO21(operation,extra){
 var call={io_protocol:'ict-native-io/1',call_id:++callBridge21,operation:operation,run_id:runBridge21,seq:seqBridge21+1,seen:seenBridge21};
 if(extra)for(var key in extra)call[key]=extra[key];
 var input=asciiBridge21(call);if(input.length>60000)throw new Error('Bounded helper argument exceeded');
 print('ICT_IO_START '+asciiBridge21({call_id:callBridge21,input_wire:input}));
 processBridge21=new QProcess();processBridge21.setProgram('/usr/bin/python3');processBridge21.setArguments(['/work/native_io.py',input]);
 processBridge21.start(new QIODevice.OpenMode(3));
 if(!processBridge21.waitForStarted(5000))throw new Error('Helper launch failed: '+Number(processBridge21.error()));
 if(!processBridge21.waitForFinished(5000))throw new Error('Helper observation timeout; keep same native/helper process');
 var stdout=decodeBridge21(processBridge21.readAllStandardOutput()),stderr=decodeBridge21(processBridge21.readAllStandardError());
 var terminal={call_id:callBridge21,exit:Number(processBridge21.exitCode()),exit_status:Number(processBridge21.exitStatus()),stdout:stdout,stderr:stderr};
 print('ICT_IO_END '+asciiBridge21(terminal));
 if(stdout.length>65536||stderr!=='')throw new Error('Helper output bound/stderr differs');
 var result=JSON.parse(stdout);
 if(result.io_protocol!=='ict-native-io/1'||result.call_id!==callBridge21||(runBridge21!==null&&result.run_id!==runBridge21))throw new Error('Helper response identity differs');
 if(result.ok!==true||terminal.exit!==0||terminal.exit_status!==0)throw new Error('Helper failed: '+stdout);
 return result;
}
timerBridge21.timeout.connect(function(){
 try{
  if(runBridge21===null){var initialized=callBridgeIO21('initialize');runBridge21=initialized.run_id;}
  var next=callBridgeIO21('poll');
  if(next.status==='idle')return;
  if(next.status==='stopped'){timerBridge21.stop();print('ICT_IO_STOPPED '+asciiBridge21({run_id:runBridge21,call_id:callBridge21}));return;}
  if(next.status!=='request')throw new Error('Unexpected poll status');
  var request=next.request,body=request.body,observation,extra={request_wire:next.request_wire};
  try{
   if(body.action==='seal'){
    if(Object.keys(body).join(',')!=='action')throw new Error('Unsupported transport seal body');
    observation=payload21({action:'status'},request.seq);observation.request={seq:request.seq,action:'seal'};
   }else observation=payload21(body,request.seq);
   extra.observation=observation;
  }catch(nativeError){extra.native_error={message:String(nativeError),stage:'native-observation'};}
  callBridgeIO21('publish',extra);
  seenBridge21[('00000000'+request.seq).slice(-8)+'.json']=next.request_sha256;seqBridge21++;
  if(body.action==='seal'){timerBridge21.stop();print('ICT_IO_SEALED '+asciiBridge21({run_id:runBridge21,seq:seqBridge21,call_id:callBridge21}));}
 }catch(err){timerBridge21.stop();print('ICT_MAILBOX_FATAL '+asciiBridge21({run_id:runBridge21,seq:seqBridge21+1,call_id:callBridge21,error:String(err)}));}
});
timerBridge21.start(250);
