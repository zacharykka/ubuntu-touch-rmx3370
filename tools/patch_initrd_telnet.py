#!/usr/bin/env python3
"""Patch the Halium initrd panic/telnet script for bitra debugging:
 1. prefer configfs: CONFIG_USB_CONFIGFS_UEVENT exposes /sys/class/android_usb/android0
    with only a 'state' attribute, so the legacy android_usb path cannot work;
 2. use CDC-ECM instead of RNDIS (macOS has a native ECM driver, no RNDIS);
 3. mark the gadget product string so the debug image is recognisable on the host."""
import sys

path = sys.argv[1]
src = open(path).read()
orig = src

def sub(old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        sys.exit(f'anchor matched {n} times (expected {count}): {old!r}')
    src = src.replace(old, new)

sub('USB_FUNCTIONS=rndis\n', 'USB_FUNCTIONS=ecm\n')
sub('write $GADGET_DIR/g1/strings/0x409/product      "Failed to boot"',
    'write $GADGET_DIR/g1/strings/0x409/product      "Failed to boot (bitra ECM debug)"')
# create the ECM function next to the (now unused) rndis block
sub('''    echo $USB_FUNCTIONS | grep -q "mass_storage" && mkdir $GADGET_DIR/g1/functions/storage.0
''', '''    if echo $USB_FUNCTIONS | grep -q "ecm"; then
        mkdir $GADGET_DIR/g1/functions/ecm.usb0
    fi
    echo $USB_FUNCTIONS | grep -q "mass_storage" && mkdir $GADGET_DIR/g1/functions/storage.0
''')
sub('''    echo $USB_FUNCTIONS | grep -q "mass_storage" && ln -s $GADGET_DIR/g1/functions/storage.0 $GADGET_DIR/g1/configs/c.1
''', '''    if echo $USB_FUNCTIONS | grep -q "ecm"; then
        ln -s $GADGET_DIR/g1/functions/ecm.usb0 $GADGET_DIR/g1/configs/c.1
    fi
    echo $USB_FUNCTIONS | grep -q "mass_storage" && ln -s $GADGET_DIR/g1/functions/storage.0 $GADGET_DIR/g1/configs/c.1
''')
sub('''    if [ -d $ANDROID_USB ]; then
        usb_setup_android_usb $1
    elif [ -d $GADGET_DIR ]; then
        usb_setup_configfs $1
    fi''', '''    if [ -d $GADGET_DIR ]; then
        usb_setup_configfs $1
    elif [ -d $ANDROID_USB ]; then
        usb_setup_android_usb $1
    fi''')
open(path, 'w').write(src)
print('patched OK')
