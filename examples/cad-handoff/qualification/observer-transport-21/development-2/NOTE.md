# Second native attempt: missing QFileDevice, complete console fallback

Frozen e395618 fails before a normal request. The actual installed binary has no
QFileDevice class. The native console preserves the original error, failed error
publication and diagnostic unavailability. The client detects that console error
and refuses immediately. Original controller1/native0/container1 exits, exact
methods, console, UI and separate same-process normal cleanup/export are retained.
No drawing was opened or saved. This is still a failed normal transport attempt.

The read upstream generated source did not prove class availability in this
installed binary. The next frozen step is a capability probe, not another guessed
repair. Parent methods and QProcess/UTF-8 decoding will be observed directly before
selecting a successor. The older camera20 error remains unexplained by this result.
