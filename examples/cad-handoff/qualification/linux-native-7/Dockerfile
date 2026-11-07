# Infrastructure experiment, not a distributable CAD image or a CI prerequisite.
# Supply the recorded immutable Ubuntu digest and downloaded publisher package hash.
ARG BASE=ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
FROM ${BASE}
ARG QCAD_SHA256
ENV DEBIAN_FRONTEND=noninteractive DISPLAY=:99 QT_X11_NO_MITSHM=1 QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates xvfb openbox x11vnc novnc websockify xdotool x11-utils wmctrl scrot \
    dbus-x11 at-spi2-core python3 python3-pyatspi fonts-dejavu-core \
    libxcb1 libx11-xcb1 libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 \
    libxcb-render0 libxcb-shm0 libxcb-keysyms1 libxcb-image0 libxcb-icccm4 \
    libxcb-xkb1 libxcb-shape0 libxcb-randr0 libxcb-render-util0 libxcb-sync1 \
    libgl1 libegl1 libfontconfig1 libdbus-1-3 libxrender1 libxi6 libxrandr2 libxfixes3 \
    libsm6 libice6 libnss3 libasound2t64 \
    && rm -rf /var/lib/apt/lists/*
COPY qcad.tar.gz /tmp/qcad.tar.gz
RUN test -n "$QCAD_SHA256" && echo "$QCAD_SHA256  /tmp/qcad.tar.gz" | sha256sum -c - \
    && mkdir /opt/qcad && tar -xzf /tmp/qcad.tar.gz --strip-components=1 -C /opt/qcad \
    && rm /tmp/qcad.tar.gz \
    && useradd --create-home --uid 1001 cad && mkdir /work && chown cad:cad /work
COPY desktop.sh /opt/desktop.sh
RUN chmod 755 /opt/desktop.sh && dpkg-query -W > /opt/installed-packages.tsv
USER cad
WORKDIR /work
ENTRYPOINT ["dbus-run-session", "--", "/opt/desktop.sh"]
