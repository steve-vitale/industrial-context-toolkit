# Observed cleanup failure and controller correction

The first frozen process emitted all 14 job records and DONE, then its final
`QCoreApplication.quit()` raised TypeError: this function is unavailable in the installed QtScript API.
That original exception remains in stderr. It is not a CAD crash, lost observation or successful scripted
shutdown. No CAD process is restarted and the frozen observation script is not changed mid-batch.

The original startup controller matched an X11 tree entry even after the Trial window was hidden. It
sent four retained Return-key commands; only the first acknowledged the visible notice. Its three extra
activations/Return commands are controller errors, not additional independent trials. The 14 job records
and DONE already exist, and the main window now has no drawing. The controller was interrupted, exit 1;
the native CAD process remained live. No original controller exception traceback was produced.

Before continuing, `control_native.py` corrects visibility detection and handles normal application exit:
acknowledge only a visible exactly named Trial window; after that process's DONE and retained quit TypeError,
send the normal window-manager close request to the single visible exactly named QCAD main window. Retain
before screenshots, commands and process identifiers. Unknown/ambiguous dialogs stop automation. The same
frozen methods continue in the existing batch, with every scripted cleanup exception and actual UI close
kept explicit. This is additional external GUI cleanup, not an unassisted scripted-shutdown pass or native
entity-edit qualification. Selected working settings may change through normal close, as planned.
