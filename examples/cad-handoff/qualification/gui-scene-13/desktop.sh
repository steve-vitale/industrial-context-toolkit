#!/bin/sh
set -eu
printf '%s\n' "$DBUS_SESSION_BUS_ADDRESS" > /work/dbus-address.txt
sha256sum /home/cad/.config/QCAD/QCAD3.conf > /work/selected-config-initial.sha256
Xvfb :99 -screen 0 2400x1400x24 -nolisten tcp > /work/xvfb.log 2>&1 &
until xdpyinfo -display :99 >/dev/null 2>&1; do sleep 0.2; done
openbox > /work/openbox.log 2>&1 &
if [ "${OBSERVE_PAINT:-0}" = 1 ]; then
  # The package's qcad launcher is a shell script: its shell also loads the observer.
  # Resolve the frozen package libraries before entering that launcher.
  export LD_LIBRARY_PATH=/opt/qcad${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
  export LD_PRELOAD=/work/paint_trace.so
  export ICT_PAINT_TRACE=/work/paint.jsonl
fi
exec /opt/qcad/qcad -exec /work/native_views.js
