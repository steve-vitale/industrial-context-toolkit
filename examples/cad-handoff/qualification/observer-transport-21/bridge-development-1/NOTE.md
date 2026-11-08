# First Python-I/O bridge: native replies, then failed UI flow

Frozen eef0788 returned two status replies. The original UI typing routine refused
an immediate filename readback and controller/host exited1. The exact mismatch
was not logged by that routine. Later read-only inspection observed the complete
filename without another typing action. The separately frozen first Cancel click
also timed out; neither failure is a normal bridge pass.

The second separately frozen cleanup published the run-bound stop marker. Native
acknowledged it at helper call1645, with no live helper. Open Drawing still existed;
one further Cancel then completed and the same unmodified unnamed process closed
normally. Native0/controller1/container1 stay distinct. No drawing opened or saved.

The archive retains all3407 actual files (8,510,738 raw bytes), including the frozen
method/input, complete1645-call console/event chain, private mailbox, two replies,
original failure, both cleanup sources/commands/results, snapshots and process/
export/terminal receipts. `INVENTORY.json` binds every archive member. These are
exposed development observations, not an independent review or CAD qualification.

```sh
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_bridge_development.py
```

The asynchronous capability probe is a separately frozen successor. A bounded
filename read alone does not establish that the blocking GUI interference is fixed.
