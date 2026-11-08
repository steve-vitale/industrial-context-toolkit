// Capability inventory only. No document open/edit/save or repair of an earlier process.
include('scripts/EAction.js');
var probeProcess21=null;
function probe21(label,fn,report){try{report[label]={ok:true,value:fn()};}catch(err){report[label]={ok:false,error:String(err)};}}
var probeTimer21=new QTimer();probeTimer21.singleShot=true;
probeTimer21.timeout.connect(function(){
 var report={scope:'Installed QtScript capability probe, not native CAD acceptance',qt:String(RSettings.getQtVersionString()),checks:{}};
 var checks=report.checks, file=new QFile('/home/cad/ict-mailbox-21/probe.bin');
 probe21('file_methods',function(){var out={};for(var i=0,n=['open','close','size','error','errorString','flush','copy','rename'];i<n.length;i++)out[n[i]]=typeof file[n[i]];return out;},checks);
 probe21('classes',function(){return {QFileDevice:typeof QFileDevice,QIODevice:typeof QIODevice,QProcess:typeof QProcess,QTextCodec:typeof QTextCodec,NewOnly:typeof QIODevice.NewOnly};},checks);
 probe21('new_only_first',function(){var ok=file.open(new QIODevice.OpenMode(0x0042));if(!ok)return false;var t=new QTextStream(file);t.setCodec('UTF-8');t.writeString('ORIGINAL CAPABILITY BYTES\n');t.flush();file.close();return true;},checks);
 var collision=new QFile('/home/cad/ict-mailbox-21/probe.bin');
 probe21('new_only_collision',function(){var ok=collision.open(new QIODevice.OpenMode(0x0042));if(ok)collision.close();return ok;},checks);
 probe21('parent_error_string',function(){return String(QIODevice.prototype.errorString.call(collision));},checks);
 probe21('parent_size',function(){return Number(QIODevice.prototype.size.call(file));},checks);
 probe21('process_roundtrip',function(){
  probeProcess21=new QProcess();probeProcess21.setProgram('/usr/bin/python3');
  probeProcess21.setArguments(['-c','import json,os,sys;print(json.dumps({"uid":os.getuid(),"value":"\\u00b5 valve"},ensure_ascii=False));sys.stderr.write("probe stderr\\n")']);
  probeProcess21.start(new QIODevice.OpenMode(3));
  if(!probeProcess21.waitForStarted(5000))throw new Error('Probe helper not started');
  if(!probeProcess21.waitForFinished(5000))throw new Error('Probe helper not terminal; retain same process');
  var stdout=probeProcess21.readAllStandardOutput(),stderr=probeProcess21.readAllStandardError();
  return {pid:Number(probeProcess21.processId()),exit:Number(probeProcess21.exitCode()),exit_status:Number(probeProcess21.exitStatus()),
   codec_stdout:String(QTextCodec.codecForName('UTF-8').toUnicode(stdout)),
   codec_stderr:String(QTextCodec.codecForName('UTF-8').toUnicode(stderr))};
 },checks);
 var di=EAction.getDocumentInterface(),d=isNull(di)?undefined:di.getDocument();
 report.filename=isNull(d)?null:String(d.getFileName());report.modified=isNull(d)?null:d.isModified();
 print('ICT_BINDING_PROBE '+JSON.stringify(report));
 var out=new QFile('/work/native/BINDINGS.json');
 if(!out.open(QIODevice.WriteOnly))throw new Error('Cannot retain binding probe');
 var stream=new QTextStream(out);stream.setCodec('UTF-8');stream.writeString(JSON.stringify(report)+'\n');out.close();
});probeTimer21.start(1);
