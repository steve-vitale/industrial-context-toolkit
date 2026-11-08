// Receiving-only observer: prove the selected settings path before the frozen probe.
include("scripts/simple.js");
var selected=String(RSettings.getFileName());
var f=new QFile("/work/native-profile.json");
if(!f.open(QIODevice.WriteOnly))throw new Error("Cannot retain selected native profile");
var stream=new QTextStream(f);setUtf8Codec(stream);
stream.writeString(JSON.stringify({configuration_file:selected,qt_version:String(RSettings.getQtVersionString())}));
f.close();
if(selected!=="/home/cad/.config/QCAD/QCAD3.conf")throw new Error("Wrong actual native settings file");
include("/work/native_probe.js");
