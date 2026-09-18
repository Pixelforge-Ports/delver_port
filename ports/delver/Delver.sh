#!/bin/bash
XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source "$controlfolder/control.txt"
[ -f "$controlfolder/mod_${CFW_NAME}.txt" ] && source "$controlfolder/mod_${CFW_NAME}.txt"
get_controls

GAMEDIR="/${directory#/}/ports/delver"
java_runtime="zulu17.54.21-ca-jre17.0.13-linux"
jar_filename="delver.jar"

cd "$GAMEDIR" || { pm_message "Delver: game folder missing."; pm_finish; exit 1; }
exec > >(tee "$GAMEDIR/log.txt") 2>&1

SAVEDIR="$GAMEDIR/save/"
CACHEDIR="$GAMEDIR/cache/"

weston_dir=/tmp/weston
export JAVA_HOME="/tmp/javaruntime/"
weston_mounted=0
java_mounted=0
weston_started=0
mapper_pid=""

cleanup() {
  if [ -n "$mapper_pid" ]; then
    kill "$mapper_pid" 2>/dev/null
    wait "$mapper_pid" 2>/dev/null
    mapper_pid=""
  fi
  if [ "$weston_started" = 1 ]; then
    $ESUDO "$weston_dir/westonwrap.sh" cleanup
  fi

  if [ "$PM_CAN_MOUNT" != N ]; then
    if [ "$java_mounted" = 1 ]; then
      $ESUDO umount "$JAVA_HOME"
    fi
    if [ "$weston_mounted" = 1 ]; then
      $ESUDO umount "$weston_dir"
    fi
  fi
  pm_finish
}

fail() {
  pm_message "Delver: $* See delver/log.txt."
  sleep 5
  cleanup
  exit 1
}
$ESUDO mkdir -p "$SAVEDIR" "$CACHEDIR" || fail "Cannot create save folders."
[ "$DEVICE_ARCH" = aarch64 ] || fail "64-bit ARM firmware is required."
[ "$(getconf LONG_BIT)" = 64 ] || fail "64-bit userland is required."
[ -f "$GAMEDIR/$jar_filename" ] || fail "Copy your owned delver.jar to delver/delver.jar."
[ -n "$GPTOKEYB2" ] || fail "Update PortMaster for controller support."

$ESUDO mkdir -p "${weston_dir}" || fail "Cannot create Weston directory."
weston_runtime="weston_pkg_0.2"
if [ ! -f "$controlfolder/libs/${weston_runtime}.squashfs" ]; then
  if [ ! -f "$controlfolder/harbourmaster" ]; then
    fail "This port requires the latest PortMaster to run, please go to https://portmaster.games/ for more info."
  fi
  $ESUDO "$controlfolder/harbourmaster" --quiet --no-check runtime_check "${weston_runtime}.squashfs" || fail "Cannot download Weston."
fi
if [[ "$PM_CAN_MOUNT" != "N" ]]; then
    $ESUDO umount "${weston_dir}" 2>/dev/null || true
fi
$ESUDO mount "$controlfolder/libs/${weston_runtime}.squashfs" "$weston_dir" \
  || fail "Cannot mount Weston."
weston_mounted=1

$ESUDO mkdir -p "${JAVA_HOME}" || fail "Cannot create Java directory."
if [ ! -f "$controlfolder/libs/${java_runtime}.squashfs" ]; then
  if [ ! -f "$controlfolder/harbourmaster" ]; then
    fail "This port requires the latest PortMaster to run, please go to https://portmaster.games/ for more info."
  fi
  $ESUDO "$controlfolder/harbourmaster" --quiet --no-check runtime_check "${java_runtime}.squashfs" || fail "Cannot download Java."
fi
if [[ "$PM_CAN_MOUNT" != "N" ]]; then
    $ESUDO umount "${JAVA_HOME}" 2>/dev/null || true
fi
$ESUDO mount "$controlfolder/libs/${java_runtime}.squashfs" "$JAVA_HOME" \
  || fail "Cannot mount Java."
java_mounted=1
export PATH="$JAVA_HOME/bin:$PATH"

cd "$GAMEDIR" || fail "Cannot open the game directory."

"$JAVA_HOME/bin/java" -Xmx64m -cp runtime/delver-host.jar org.portmaster.delver.VerifyGame "$GAMEDIR/$jar_filename" || fail "Unsupported or damaged game JAR. Check the README checksum."
source "$GAMEDIR/display.inc" || fail "Display helper missing."
delver_display_setup || fail "Use auto or WIDTHxHEIGHT in resolution.txt."
printf 'Firmware: %s; display: %s\n' "$CFW_NAME" "$delver_display_description"
export SDL_TOUCH_MOUSE_EVENTS=0
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"
export HOTKEY=back
$GPTOKEYB2 java -c "$GAMEDIR/delver.ini" > /dev/null &
mapper_pid=$!
sleep 1
kill -0 "$mapper_pid" 2>/dev/null || fail "Controller mapper failed to start."
pm_platform_helper "$JAVA_HOME/bin/java"

weston_started=1
$ESUDO env "${display_env[@]}" "$weston_dir/westonwrap.sh" headless noop kiosk crusty_glx_gl4es \
  "PATH=$JAVA_HOME/bin:$PATH" "JAVA_HOME=$JAVA_HOME" "HOME=$SAVEDIR" \
  "XDG_DATA_HOME=$SAVEDIR" "XDG_CONFIG_HOME=$SAVEDIR/config" \
  "XDG_CACHE_HOME=$CACHEDIR" "WAYLAND_DISPLAY=" \
  "$JAVA_HOME/bin/java" -Xms32m -Xmx384m -XX:+UseSerialGC \
  "-Duser.home=$SAVEDIR" "-Djava.io.tmpdir=$CACHEDIR" \
  "-Ddelver.jar=$GAMEDIR/$jar_filename" --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED \
  -Ddelver.fullscreen=true -Ddelver.mappedInput=true "${display_java[@]}" \
  -cp "$GAMEDIR/runtime/delver-host.jar:$GAMEDIR/runtime/lib/*:$GAMEDIR/$jar_filename" org.portmaster.delver.Main

status=$?
cleanup
exit "$status"
