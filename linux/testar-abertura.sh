#!/bin/sh
# Launch test, the same as each instrument's CI (packaging/linux/testar-arranque.sh):
# starts the app on a virtual screen (Xvfb), with no sound card, and checks it
# is still running after N seconds. Catches the instrument that does not even
# open (missing library, a .deb with an unresolvable dependency).
#
#   linux/testar-abertura.sh <executable> [seconds]
set -eu
EXE=$1
WAIT=${2:-15}

H=$(mktemp -d)
export HOME="$H"
export APPIMAGE_EXTRACT_AND_RUN=1

XPID=
if [ -z "${DISPLAY:-}" ] && command -v Xvfb >/dev/null 2>&1; then
    Xvfb :77 -screen 0 1600x1000x24 -nolisten tcp >/dev/null 2>&1 &
    XPID=$!
    export DISPLAY=:77
    sleep 2
fi

"$EXE" >"$H/out.txt" 2>&1 &
PID=$!
sleep "$WAIT"

ok=1
if kill -0 "$PID" 2>/dev/null; then
    echo "still running after ${WAIT} s"
else
    wait "$PID" && st=0 || st=$?
    echo "EXITED — status $st"; ok=0
fi
echo "--- app output (last lines) ---"; tail -n 20 "$H/out.txt" || true
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
if [ -n "$XPID" ]; then kill "$XPID" 2>/dev/null || true; fi
rm -rf "$H"
[ "$ok" = 1 ] && echo "OK: $EXE" || { echo "FAILED: $EXE"; exit 1; }
