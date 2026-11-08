#!/bin/sh
set -eu
cd /work
g++ --version > compiler.txt
pkg-config --modversion Qt5Gui Qt5Core > header-versions.txt
dpkg-query -W > packages.txt
nm -D native-libs/libQt5Gui.so.5 | c++filt > native-gui-symbols.txt
g++ -std=c++17 -fPIC -shared -O2 -Wall -Wextra -DQT_NO_VERSION_TAGGING \
  $(pkg-config --cflags Qt5Gui Qt5Core) paint_trace.cpp \
  -L/work/native-libs -l:libQt5Gui.so.5 -l:libQt5Core.so.5 -ldl -pthread -o paint_trace.so
sha256sum paint_trace.cpp paint_trace.so native-libs/libQt5Gui.so.5 native-libs/libQt5Core.so.5 > hashes.txt
readelf -d paint_trace.so > helper-dynamic.txt
nm -D --undefined-only paint_trace.so | c++filt > helper-undefined.txt
