#!/bin/sh
# realme GT Neo2 (bitra): drive the rear flash without the camera app.
#
# The qpnp-flash-led-v2 driver needs two writes: the torch node takes a
# current in mA, then the paired switch node actually enables the LED.
# led:switch_0 has qcom,led-mask = 0x1, so it drives fnode id 0 = led:torch_0.
#
# The power menu's Flashlight switch goes through ayatana-indicator-power and
# writes the same pair, so this is only for testing from a shell.
# Usage: torch.sh on|off
TORCH=/sys/class/leds/led:torch_0/brightness
SWITCH=/sys/class/leds/led:switch_0/brightness

case "$1" in
    on)
        echo 255 > "$TORCH" || exit 1
        echo 1 > "$SWITCH" || exit 1
        ;;
    off)
        echo 0 > "$SWITCH" || exit 1
        ;;
    *)
        echo "usage: $0 on|off" >&2
        exit 2
        ;;
esac
