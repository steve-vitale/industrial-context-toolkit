#!/bin/sh
set -eu
printf '%s\n' "$DBUS_SESSION_BUS_ADDRESS" > /work/dbus-address.txt
Xvfb :99 -screen 0 2400x1400x24 -nolisten tcp > /work/xvfb.log 2>&1 &
until xdpyinfo -display :99 >/dev/null 2>&1; do sleep 0.2; done
openbox > /work/openbox.log 2>&1 &
x11vnc -display :99 -localhost -forever -shared -nopw -rfbport 5900 > /work/vnc.log 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 > /work/websockify.log 2>&1 &
if [ "$FONT_PROFILE" = "substitute" ]; then
  exec /opt/qcad/qcad -config /work/qcad-config -font-substitution Standard 'DejaVu Sans' -exec /work/native_views.js
else
  exec /opt/qcad/qcad -config /work/qcad-config -exec /work/native_views.js
fi
