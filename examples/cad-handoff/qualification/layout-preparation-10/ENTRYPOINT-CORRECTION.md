# Retain unintended desktop entrypoint launch

The third container creation omitted the explicit entrypoint override used by the
earlier CLI containers. Inspection showed `dbus-run-session -- /opt/desktop.sh`
instead of `/usr/bin/python3`. The image ignored the supplied Python arguments and
launched its desktop. No `native/` directory, evidence driver or probe had started.
The host retained this diagnosis before stopping that unintended desktop container.
Its terminal state, logs and exact untouched inputs are retained as a setup failure;
it is never an accepted native batch. This stop was intentional correction of a
known wrong process, not a reaction to quiet output or a capture timeout.

Before a fourth run, require `--entrypoint /usr/bin/python3` and inspect the created
container's exact Path/Args/Image/User/mount and absence of published ports before
starting it. Require every earlier container to be terminal. The corrected settings
driver and selected-path observer stay exactly frozen at `9567e59`; all original
source/route/method pins remain unchanged. Package the failed third and receiving
fourth batches separately from the unchanged initial archive.
