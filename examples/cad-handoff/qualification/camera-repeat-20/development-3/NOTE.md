# Preserve the template observation-channel failure

All six original camera-only native applications/controllers/containers exited
zero. The strict receiver accepted five packets, then refused template with
`Camera reply coverage differs`. Its actual command/error and the failed host
command/stdout/stderr/exit and frozen receiver source are retained here.

Template retains all 86 sequential successful replies/actions and an additional
`replies/unknown.json`: `{"error":"Error: Cannot read request"}`. The actual
read-only helper checks existence and then opens the replaceable request path;
its QFile open returned false. A filesystem/path-replacement race is a lead,
not established root cause. The saved file's timestamp precedes the final reply.
The helper writes a fixed filename for anonymous errors, so the retained file
proves at least one failure and cannot establish the total error count/history.
Normal native exit does not make this a clean observation channel.

The strict route remains unchanged: any extra/missing reply refuses. Before a
new diagnostic is run, the separate explicit diagnostic mode is frozen. It can
inspect the complete retained normal replies, UI fields and images only while
retaining well-formed extra error records as failed and marking every image
comparison diagnostic. Missing normal replies or other corrupted evidence still
refuse. This is not an exception for template or permission to remove its error.
Original packet bytes, native method and strict failure remain unchanged.

The next complete native method needs immutable, sequence-bound request/reply
transport and a retained error history with meaningful missing/read/write/error
controls before reserved evaluation. Do not relaunch this exposed case and call
the new run independent validation.
