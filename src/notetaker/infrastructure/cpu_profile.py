"""Windows CPU accounting in seconds, including terminated descendants in a job."""
import ctypes
import os
from ctypes import wintypes as w


def process_cpu(process):
    if os.name != 'nt':
        return None
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.GetProcessTimes.argtypes = [w.HANDLE, *([ctypes.POINTER(w.FILETIME)] * 4)]
    api.GetProcessTimes.restype = w.BOOL
    times = [w.FILETIME() for _ in range(4)]
    if not api.GetProcessTimes(w.HANDLE(int(process._handle)), *(ctypes.byref(t) for t in times)):
        raise ctypes.WinError(ctypes.get_last_error())
    seconds = lambda t: ((t.dwHighDateTime << 32) | t.dwLowDateTime) / 10_000_000
    return {'kernel_seconds': seconds(times[2]), 'user_seconds': seconds(times[3])}


def job_cpu(job):
    if not job.handle:
        return None
    class Accounting(ctypes.Structure):
        _fields_ = [(name, ctypes.c_longlong) for name in
                    ('user', 'kernel', 'period_user', 'period_kernel')] + [
                    (name, w.DWORD) for name in ('faults', 'processes', 'active', 'terminated')]
    api = job.api
    api.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
    api.QueryInformationJobObject.restype = w.BOOL
    info = Accounting()
    if not api.QueryInformationJobObject(job.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'user_seconds': info.user / 10_000_000, 'kernel_seconds': info.kernel / 10_000_000,
            'processes': info.processes, 'active': info.active}
