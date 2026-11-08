# First native transport attempt failed before a normal reply

Implementation frozen at `a720dcf` before execution; criteria at `ca96ca0`.
The original air/water attempt retains controller exit 1, native exit 0 after a
separate recorded same-process UI cleanup, and container exit 1. The client
reported a missing reply; the native console records `file21.size` unavailable
and the error reporter itself failing on unavailable `file21.error`. No request
was accepted and no drawing was opened or saved. All actual files, methods,
console, UI, command and export records are in the hashed archive.

This is an implementation/capability failure, not the cause of the older camera20
request-open error. The original attempt is not restarted or repaired in place.
The subsequent method invokes registered parent prototypes explicitly, uses
numeric enum results and constructs the documented Qt5.14.2 NewOnly OpenMode
through the older generated flags binding. It must still demonstrate these
bindings in the actual installed native process before any normal/fault claim.

QCAD's [5.14.2 build file](https://github.com/qcad/qcad/blob/master/src/3rdparty/qt-labs-qtscriptgenerator-5.14.2/qt-labs-qtscriptgenerator-5.14.2.pro)
selects its generated5.5 bindings. Their QFile prototype delegates inheritance
to QFileDevice, and its QIODevice flag enumeration lacks NewOnly; the OpenMode
constructor accepts an integer. This source reading motivates a new native test,
not a substitute for that test. Error facts now catch their own diagnostic
failure before the unconditional console record, preventing this secondary error
from suppressing the original failure again.
