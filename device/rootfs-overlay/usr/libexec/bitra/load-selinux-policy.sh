#!/bin/sh
# realme GT Neo2 (bitra): load the vendor SELinux policy into the kernel
# before the Android container starts.
#
# Halium replaces Android's first-stage init, so nothing calls
# selinux_android_load_policy() and the kernel runs with no policy at all
# (/sys/fs/selinux/class is empty). selinux_check_access() then fails with
# EINVAL for the service_manager class. Permissive mode does not hide that:
# it only waives denials of permissions the policy knows about.
# vndservicemanager cannot register itself, display.qservice never appears,
# the QTI composer exits in a loop and Mir never gets a display.
#
# This loads the vendor's precompiled policy. Android itself would only use
# that file if its hashes matched the system policy, which they do not with
# the Halium GSI. For a permissive system it is enough that the classes exist.
#
# /sys/fs/selinux/load only accepts the whole policy in a single write().
# Chunked writes (cat, or dd with a small bs) fail with EINVAL.
POL=/odm/etc/selinux/precompiled_sepolicy
SELINUXFS=/sys/fs/selinux

if [ ! -f "$POL" ]; then
    echo "bitra-selinux: $POL not found (is /android/odm mounted?)" >&2
    exit 1
fi
mountpoint -q $SELINUXFS || mount -t selinuxfs selinuxfs $SELINUXFS || exit 1

before=$(ls $SELINUXFS/class 2>/dev/null | wc -l)
if [ "$before" -eq 0 ]; then
    size=$(stat -c %s "$POL")
    if ! dd if="$POL" of=$SELINUXFS/load bs="$size" count=1 status=none; then
        echo "bitra-selinux: loading $POL ($size bytes) failed" >&2
        exit 1
    fi
fi
after=$(ls $SELINUXFS/class 2>/dev/null | wc -l)
echo "bitra-selinux: policy classes before=$before after=$after"
if [ ! -d $SELINUXFS/class/service_manager ]; then
    echo "bitra-selinux: no service_manager class after loading $POL" >&2
    exit 1
fi

# Stay permissive during bring-up. The kernel already starts permissive
# (CONFIG_SECURITY_SELINUX_DEVELOP=y); make it explicit.
echo 0 > $SELINUXFS/enforce
