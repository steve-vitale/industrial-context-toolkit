# Native MDI close accepts before deferred wrapper removal

The MDI observation process also emitted all 14 records and DONE. Every per-job close returned true,
but `subWindowList()` still counted the closed wrapper while the same timer callback ran. The final
cleanup loop then encountered a wrapper whose `getDocument()` was null. The exact TypeError remains
in stderr. This confirms that the window-count observation is not proof of live document retention
or completed wrapper deletion. Do not assert count removal or an interactive close/reopen pass.

Keep the frozen method unchanged. `close_mdi.py` may send the same normal window-manager close only
after each MDI process has emitted DONE and this exact observed null-document cleanup exception.
The second controller continues handling visible startup notices and bare-process quit exceptions;
the new controller handles only this separately observed MDI cleanup condition. Both retain their
actual actions. No process is restarted, no additional CAD mutation/save is introduced, and no incomplete
job is promoted. The startup notice briefly disables OK during its countdown; repeated retained Return
commands before enablement do not count as additional runs or bypass that countdown.
