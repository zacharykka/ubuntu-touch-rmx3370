#!/bin/sh
# realme GT Neo2 (bitra): tell usb-moded which extcon device reports a USB
# data connection. Runs as usb-moded.service ExecStartPre.
#
# usb-moded lets the extcon state override the charger type it reads from
# /sys/class/power_supply/usb: "USB=1" means a PC, "USB=0" a dedicated
# charger. Without extcon_path it reads every extcon device and the last one
# wins. This phone has six; only the PM8150B PD PHY reports the cable
# (USB=1 on a PC), the others (EUD, the extcon-usb-gpio ID pin, smb5, two
# DP/HDMI) report USB=0. usb-moded therefore saw a dedicated charger while
# power_supply/usb said REAL_TYPE=USB:
#   "Mode charging_only_adb requested while not connected to pc"
#
# extcon_path must be a syspath that includes the extconN number, and that
# number depends on probe order (the PD PHY defers its probe), so resolve it
# at boot. /etc/usb-moded/30-bitra-cable-detection.ini links to the file
# written here, the same way the UBports configurator publishes its config.
OUT=/run/bitra-usb-moded
PDPHY=/sys/devices/platform/soc/c440000.qcom,spmi/spmi-0/spmi0-02/c440000.qcom,spmi:qcom,pm8150b@2:qcom,usb-pdphy@1700

mkdir -p $OUT
EXTCON=$(ls -d $PDPHY/extcon/extcon* 2>/dev/null | head -1)
if [ -z "$EXTCON" ]; then
    # Leave usb-moded on its defaults rather than fail the unit.
    echo "bitra-usb: no extcon under $PDPHY, cable detection not overridden" >&2
    : > $OUT/30-bitra-cable-detection.ini
    exit 0
fi
printf "[udev]\nextcon_path = %s\n" "$EXTCON" > $OUT/30-bitra-cable-detection.ini
echo "bitra-usb: extcon_path=$EXTCON state=$(tr "\n" " " < $EXTCON/state)"
