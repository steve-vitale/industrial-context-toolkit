// Private immutable transport only. payload21 performs read-only observations/camera.
include('scripts/EAction.js');
include('/work/payload.js');
var root21='/home/cad/ict-mailbox-21', protocol21='ict-native-mailbox/1';
var seq21=0, error21=0, seen21={}, timer21=new QTimer(), run21=null;
var stage21='startup', path21=null, file21=null, text21=null;
// QCAD's 5.14.2 project uses generated 5.5 bindings. Invoke registered parent
// prototypes explicitly; QFile objects need not inherit their methods correctly.
function fileError21(f){return Number(QFileDevice.prototype.error.call(f));}
function fileMessage21(f){return String(QIODevice.prototype.errorString.call(f));}
function name21(n){return ('00000000'+n).slice(-8)+'.json';}
function facts21(){
 var out={path:path21,exists:null,size:null,code:null,message:null};
 try{var info=path21===null?null:new QFileInfo(path21);
  out.exists=info===null?null:info.exists();out.size=info===null?null:Number(info.size());
  out.code=file21===null?null:fileError21(file21);out.message=file21===null?null:fileMessage21(file21);
 }catch(err){out.diagnostic_failure=String(err);}
 return out;
}
function read21(path){
 path21=path;stage21='read-open';file21=new QFile(path);
 if(!file21.open(QIODevice.ReadOnly))throw new Error('Request read-open failed');
 if(new QFileInfo(path).size()>65536){file21.close();throw new Error('Request exceeds wire limit');}
 stage21='read-text';var t=new QTextStream(file21);t.setCodec('UTF-8');var s=t.readAll();
 if(Number(t.status())!==0||fileError21(file21)!==0){file21.close();throw new Error('Request read failed');}
 file21.close();return s;
}
function publish21(folder,name,value){
 var target=root21+'/'+folder+'/'+name, temporary=root21+'/staging/'+folder+'/'+name;
 stage21='publish-collision';path21=target;file21=null;
 if(new QFileInfo(target).exists()||new QFileInfo(temporary).exists())throw new Error('Publication collision');
 stage21='write-open';path21=temporary;file21=new QFile(temporary);
 // The old generated enum lacks NewOnly; Qt 5.14.2 defines it as 0x0040.
 // Its OpenMode flags constructor accepts an integer, retaining the actual flag.
 if(!file21.open(new QIODevice.OpenMode(0x0042)))throw new Error('Publication write-open failed');
 stage21='write-text';var t=new QTextStream(file21);t.setCodec('UTF-8');t.writeString(JSON.stringify(value)+'\n');t.flush();
 if(Number(t.status())!==0||!QFileDevice.prototype.flush.call(file21)||fileError21(file21)!==0){file21.close();throw new Error('Publication flush failed');}
 file21.close();stage21='publish-copy';path21=temporary+'.pending';
 // Keep the closed original staging record, then publish a distinct closed copy.
 if(!file21.copy(path21))throw new Error('Publication staging copy failed');
 var check=new QFile(path21);if(!check.open(QIODevice.ReadOnly))throw new Error('Publication readback open failed');
 var stream=new QTextStream(check);stream.setCodec('UTF-8');var got=stream.readAll();check.close();
 if(got!==JSON.stringify(value)+'\n')throw new Error('Publication readback differs');
 stage21='publish-rename';file21=check;path21=target;
 if(!check.rename(target))throw new Error('Publication rename failed');
}
function fatal21(err){
 timer21.stop();error21++;
 var row={protocol:protocol21,run_id:run21,error_id:error21,seq:seq21+1,
  stage:stage21,file:facts21(),request_wire:text21,error:String(err)};
 // Console always retains the original, even if the journal cannot be written.
 print('ICT_MAILBOX_FATAL '+JSON.stringify(row));
 try{publish21('errors',name21(error21),row);}
 catch(publication){print('ICT_MAILBOX_ERROR_PUBLICATION '+JSON.stringify({original:row,stage:stage21,file:facts21(),error:String(publication)}));}
}
timer21.timeout.connect(function(){
 try{
  if(run21===null){
   var config=JSON.parse(read21('/work/transport.json'));run21=config.run_id;
   if(config.protocol!==protocol21||!(/^[a-f0-9]{32}$/).test(run21))throw new Error('Invalid transport configuration');
  }
  // Every previously published request remains immutable throughout this process.
  for(var old in seen21){if(read21(root21+'/requests/'+old)!==seen21[old])throw new Error('Published request changed');}
  var names=new QDir(root21+'/requests').entryList(['*.json'],new QDir.Filters(QDir.Files),new QDir.SortFlags(QDir.Name));
  var expected=name21(seq21+1),next=[];
  for(var k=0;k<names.length;k++)if(!seen21.hasOwnProperty(String(names[k])))next.push(String(names[k]));
  if(next.length===0)return;
  stage21='sequence';path21=root21+'/requests/'+next[0];file21=null;text21=null;
  if(next.length!==1||next[0]!==expected)throw new Error('Noncontiguous request sequence');
  text21=read21(root21+'/requests/'+expected);stage21='envelope';
  if((/[^\x00-\x7f]/).test(text21))throw new Error('Request wire must be ASCII JSON');
  var envelope=JSON.parse(text21),keys=Object.keys(envelope).sort().join(',');
  if(keys!=='body,protocol,run_id,seq'||envelope.protocol!==protocol21||envelope.run_id!==run21||envelope.seq!==seq21+1)throw new Error('Envelope sequence/run binding differs');
  stage21='observation';var observation=payload21(envelope.body,envelope.seq);
  var reply={protocol:protocol21,run_id:run21,seq:envelope.seq,request_wire:text21,observation:observation};
  publish21('replies',expected,reply);seen21[expected]=text21;seq21++;
 }catch(err){fatal21(err);}
});
timer21.start(250);
