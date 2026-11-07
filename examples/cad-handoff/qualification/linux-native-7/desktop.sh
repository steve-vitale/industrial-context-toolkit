#!/bin/sh
set -eu
Xvfb :99 -screen 0 1600x1000x24 -nolisten tcp > /work/xvfb.log 2>&1 &
until xdpyinfo -display :99 >/dev/null 2>&1; do sleep 0.2; done
openbox > /work/openbox.log 2>&1 &
# VNC listens only within the container; only noVNC's port is published on host loopback.
x11vnc -display :99 -localhost -forever -shared -nopw -rfbport 5900 > /work/vnc.log 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 > /work/websockify.log 2>&1 &
exec /opt/qcad/qcad -config /work/qcad-config
