"""QA only: per-process Windows Core Audio meter (no recording, no dependencies)."""
import ctypes as c
import os
import uuid


class GUID(c.Structure):
    _fields_ = [('bytes', c.c_ubyte * 16)]
    @classmethod
    def parse(cls, text):
        return cls((c.c_ubyte * 16).from_buffer_copy(uuid.UUID(text).bytes_le))


def invoke(pointer, index, types, *args):
    table = c.cast(pointer, c.POINTER(c.POINTER(c.c_void_p))).contents
    call = c.WINFUNCTYPE(c.c_long, c.c_void_p, *types)(table[index])
    result = call(pointer, *args)
    if result < 0:
        raise OSError(f'Core Audio HRESULT {result & 0xffffffff:08x}, method {index}')


def query(pointer, iid):
    target = c.c_void_p()
    invoke(pointer, 0, [c.POINTER(GUID), c.POINTER(c.c_void_p)], c.byref(GUID.parse(iid)), c.byref(target))
    return target


def release(pointer):
    if pointer:
        table = c.cast(pointer, c.POINTER(c.POINTER(c.c_void_p))).contents
        c.WINFUNCTYPE(c.c_ulong, c.c_void_p)(table[2])(pointer)


class ProcessAudioMeter:
    """Meter only this Python PID's audio sessions on the default render device."""
    def __init__(self):
        self.enumerator = c.c_void_p()
        self.ole = c.OleDLL('ole32')
        # QApplication initializes the GUI thread's COM apartment first.
        self.ole.CoCreateInstance.argtypes = [c.POINTER(GUID), c.c_void_p, c.c_ulong, c.POINTER(GUID), c.POINTER(c.c_void_p)]
        self.ole.CoCreateInstance(c.byref(GUID.parse('bcde0395-e52f-467c-8e3d-c4579291692e')), None, 1,
            c.byref(GUID.parse('a95664d2-9614-4f35-a746-de8db63617e6')), c.byref(self.enumerator))

    def peak(self):
        owned = []
        try:
            device = c.c_void_p(); owned.append(device)
            invoke(self.enumerator, 4, [c.c_int, c.c_int, c.POINTER(c.c_void_p)], 0, 1, c.byref(device))
            manager = c.c_void_p(); owned.append(manager)
            invoke(device, 3, [c.POINTER(GUID), c.c_ulong, c.c_void_p, c.POINTER(c.c_void_p)],
                c.byref(GUID.parse('77aa99a0-1bd6-484f-8bc7-2c654c9a9b6f')), 1, None, c.byref(manager))
            sessions = c.c_void_p(); owned.append(sessions)
            invoke(manager, 5, [c.POINTER(c.c_void_p)], c.byref(sessions))
            count = c.c_int(); invoke(sessions, 3, [c.POINTER(c.c_int)], c.byref(count))
            peak = 0.0
            for i in range(count.value):
                control = c.c_void_p()
                invoke(sessions, 4, [c.c_int,c.POINTER(c.c_void_p)], i,c.byref(control))
                control2 = meter = None
                try:
                    control2 = query(control, 'bfb7ff88-7239-4fc9-8fa2-07c950be9c6d')
                    pid = c.c_ulong()
                    invoke(control2, 14, [c.POINTER(c.c_ulong)], c.byref(pid))
                    if pid.value == os.getpid():
                        meter = query(control, 'c02216f6-8c67-4b5b-9d00-d008e73e0064')
                        value = c.c_float()
                        invoke(meter, 3, [c.POINTER(c.c_float)], c.byref(value))
                        peak = max(peak, value.value)
                finally:
                    release(meter); release(control2); release(control)
            return peak
        finally:
            for pointer in reversed(owned):
                release(pointer)

    def close(self):
        release(self.enumerator)
        self.enumerator = None
