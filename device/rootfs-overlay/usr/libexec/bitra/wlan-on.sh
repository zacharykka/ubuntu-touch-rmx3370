#!/bin/sh
# realme GT Neo2 (bitra): bring up the built-in qcacld-3.0 WLAN driver
# (QCA6390).
#
# The driver is built in (CONFIG_QCA_CLD_WLAN=y). It does nothing until
# userspace writes "ON" to /dev/wlan (wlan_hdd_state_ctrl_param_write ->
# hdd_driver_load). On Android the WiFi HAL does that. Under Halium nothing
# does, so no WLAN interface ever appears. During loading the driver asks for
# wlan/WCNSS_qcom_cfg.ini. The Android container's ueventd serves that file
# from /vendor/firmware (a link into persist), so wait for the container first.
#
# Never fail hard: a WLAN problem must not hold up boot.
echo "bitra-wlan: start, uptime $(cut -d' ' -f1 /proc/uptime)"

i=0
while [ $i -lt 90 ]; do
    state=$(lxc-info -n android -s 2>/dev/null | awk '{print $2}')
    [ "$state" = "RUNNING" ] && break
    i=$((i+1)); sleep 1
done
echo "bitra-wlan: container state=$state after ${i}s"

# ueventd must be up to serve the ini; give it a bounded wait.
i=0
while [ $i -lt 60 ] && ! pidof ueventd >/dev/null 2>&1; do i=$((i+1)); sleep 1; done
echo "bitra-wlan: ueventd pid=$(pidof ueventd) after ${i}s"

i=0
while [ $i -lt 20 ] && [ ! -c /dev/wlan ]; do i=$((i+1)); sleep 1; done
if [ ! -c /dev/wlan ]; then
    echo "bitra-wlan: no /dev/wlan, giving up"
    exit 0
fi

for n in 1 2 3; do
    if ls /sys/class/net/ | grep -qE '^(wlan|wlp)'; then break; fi
    printf 'ON' > /dev/wlan 2>/dev/null
    echo "bitra-wlan: attempt $n: write ON rc=$?"
    j=0
    while [ $j -lt 15 ] && ! ls /sys/class/net/ | grep -qE '^(wlan|wlp)'; do j=$((j+1)); sleep 1; done
done
echo "bitra-wlan: WLAN interfaces: $(ls /sys/class/net/ | grep -E '^(wlan|wlp|p2p)' | tr '\n' ' ')"
exit 0
