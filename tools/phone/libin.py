import ctypes, ctypes.util

libc = ctypes.CDLL("libc.so.6", use_errno=True)
libc.open.restype = ctypes.c_int
libc.open.argtypes = [ctypes.c_char_p, ctypes.c_int]
udev = ctypes.CDLL(ctypes.util.find_library("udev") or "libudev.so.1")
li = ctypes.CDLL(ctypes.util.find_library("input") or "libinput.so.10")

OPEN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
CLOSE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_void_p)

def _open(path, flags, data):
    return libc.open(path, flags)

def _close(fd, data):
    libc.close(fd)

class Iface(ctypes.Structure):
    _fields_ = [("open_restricted", OPEN), ("close_restricted", CLOSE)]

cb_open, cb_close = OPEN(_open), CLOSE(_close)
iface = Iface(cb_open, cb_close)

udev.udev_new.restype = ctypes.c_void_p
u = udev.udev_new()

li.libinput_udev_create_context.restype = ctypes.c_void_p
li.libinput_udev_create_context.argtypes = [ctypes.POINTER(Iface), ctypes.c_void_p, ctypes.c_void_p]
li.libinput_udev_assign_seat.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
li.libinput_dispatch.argtypes = [ctypes.c_void_p]
li.libinput_get_event.restype = ctypes.c_void_p
li.libinput_get_event.argtypes = [ctypes.c_void_p]
li.libinput_event_get_type.argtypes = [ctypes.c_void_p]
li.libinput_event_get_type.restype = ctypes.c_int
li.libinput_event_get_device.argtypes = [ctypes.c_void_p]
li.libinput_event_get_device.restype = ctypes.c_void_p
li.libinput_device_get_name.argtypes = [ctypes.c_void_p]
li.libinput_device_get_name.restype = ctypes.c_char_p
li.libinput_device_get_sysname.argtypes = [ctypes.c_void_p]
li.libinput_device_get_sysname.restype = ctypes.c_char_p
li.libinput_device_has_capability.argtypes = [ctypes.c_void_p, ctypes.c_int]
li.libinput_device_has_capability.restype = ctypes.c_int
li.libinput_event_destroy.argtypes = [ctypes.c_void_p]

ctx = li.libinput_udev_create_context(ctypes.byref(iface), None, u)
print("libinput ctx=%s" % ctx)
print("assign_seat rc=%s" % li.libinput_udev_assign_seat(ctx, b"seat0"))

seen = 0
for _ in range(5):
    li.libinput_dispatch(ctx)
    while True:
        ev = li.libinput_get_event(ctx)
        if not ev:
            break
        t = li.libinput_event_get_type(ev)
        if t in (1, 2):
            d = li.libinput_event_get_device(ev)
            name = li.libinput_device_get_name(d)
            sy = li.libinput_device_get_sysname(d)
            caps = [n for n, c in (("kbd", 0), ("ptr", 1), ("touch", 2))
                    if li.libinput_device_has_capability(d, c)] or ["NONE"]
            print("%s name=%r sysname=%r caps=%s"
                  % ("ADD" if t == 1 else "REM", name, sy, caps))
            seen += 1
        li.libinput_event_destroy(ev)
print("total device events: %d" % seen)
