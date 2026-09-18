#!/bin/bash
# shellcheck source-path=SCRIPTDIR
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
# shellcheck source=../package/delver/display.inc
source package/delver/display.inc
GAMEDIR="$(mktemp -d)"
trap 'rmdir "$GAMEDIR"' EXIT
for size in 640x480 720x480 720x720 1024x768 1280x720 960x544 320x240; do
    DISPLAY_WIDTH="${size%x*}" DISPLAY_HEIGHT="${size#*x}"
    DELVER_RESOLUTION=auto
    delver_display_setup
    [[ "${display_env[0]}" == "WESTON_HEADLESS_WIDTH=$DISPLAY_WIDTH" ]]
    [[ "${display_env[1]}" == "WESTON_HEADLESS_HEIGHT=$DISPLAY_HEIGHT" ]]
    [[ "${display_java[0]}" == "-Ddelver.width=$DISPLAY_WIDTH" ]]
    [[ "${display_java[1]}" == "-Ddelver.height=$DISPLAY_HEIGHT" ]]
done
DISPLAY_WIDTH=0 DISPLAY_HEIGHT=0
delver_display_setup
[[ "${#display_env[@]}" == 0 && "${#display_java[@]}" == 0 ]]
for bad in 0x480 640x0 100x100 9999x720 640x480oops '640x480;exit' 640X480; do
    DELVER_RESOLUTION="$bad"
    if delver_display_setup; then echo "Accepted invalid size: $bad"; exit 1; fi
done
DELVER_RESOLUTION=0720x0480
delver_display_setup
[[ "${display_java[0]}" == '-Ddelver.width=720' ]]
[[ "${display_java[1]}" == '-Ddelver.height=480' ]]
printf '720x720\r\n' > "$GAMEDIR/resolution.txt"
DELVER_RESOLUTION=""
delver_display_setup
[[ "${display_java[1]}" == '-Ddelver.height=720' ]]
DELVER_RESOLUTION=1280x720
delver_display_setup
[[ "${display_java[0]}" == '-Ddelver.width=1280' ]]
rm -- "$GAMEDIR/resolution.txt"
echo 'DISPLAY_CHECKS_OK: sizes, override precedence, CRLF, invalid inputs, automatic fallback'
