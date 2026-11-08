// Explicit selected-profile guard before either frozen native observation script.
include("scripts/simple.js");
include("scripts/Tools/arguments.js");
var actual=String(RSettings.getFileName());
print("ICT_TRANSFER11_PROFILE "+JSON.stringify({configuration_file:actual,qt_version:String(RSettings.getQtVersionString())}));
if(actual!=="/home/cad/.config/QCAD/QCAD3.conf")throw new Error("Unexpected selected native settings file");
var mode=getArgument(args,"-mode","-mode");
if(mode==="batch")include("/work/native-batch.js");
else if(mode==="bounds")include("/work/native-view-bounds.js");
else throw new Error("Unknown frozen native mode");
