#!/bin/sh
# realme GT Neo2 (bitra): let the phablet user drive the rear flash LED.
#
# The kernel exposes the flash LED brightness nodes as root:root 0644, so
# ayatana-indicator-power (which runs as phablet) fails its
# fopen(..., "w") on them, toggle_flashlight_action_qcom() returns 0 without
# logging anything, and the Flashlight switch in the power menu does nothing.
#
# The indicator probes for the torch node by itself and picks this pair
# (led:torch_0 + led:switch_0), and drive it in two steps: first a current on
# the torch node, then 1 on the switch node, whose qcom,led-mask = 0x1 enables
# fnode id 0. So both nodes need to be writable for the toggle to work.
#
# Group plugdev: phablet is already a member (it is the group for local
# user-drivable devices), so no new group and no changes to the phablet
# account are needed. Only brightness is opened up; max_current and the
# trigger stay root-only.
set -e

for led in led:torch_0 led:switch_0; do
    node=/sys/class/leds/$led/brightness
    [ -e "$node" ] || continue
    chgrp plugdev "$node"
    chmod 0660 "$node"
done
