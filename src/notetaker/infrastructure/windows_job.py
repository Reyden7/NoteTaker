"""Kill the whole Windows worker tree when its parent closes the job handle."""
import os
import subprocess


def start_process(command, **kwargs):
    """Assign the root before a Windows launcher can spawn untracked children."""
    flags = kwargs.pop('creationflags', 0)
    process = subprocess.Popen(command, creationflags=flags | (0x4 if os.name == 'nt' else 0), **kwargs)
    job = None
    try:
        job = WindowsJob(process)
        if os.name == 'nt':
            import psutil
            psutil.Process(process.pid).resume()
        return process, job
    except BaseException:
        if job:
            job.close()
        if process.poll() is None:
            process.kill()
        process.wait()
        raise

class WindowsJob:
    def __init__(self, process):
        self.handle = None
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", w.DWORD), ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]
        class Counters(ctypes.Structure):
            _fields_ = [(key, ctypes.c_ulonglong) for key in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Counters), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes, self.api.CreateJobObjectW.restype = [ctypes.c_void_p, w.LPCWSTR], w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.SetInformationJobObject.restype = w.BOOL
        self.api.AssignProcessToJobObject.argtypes, self.api.AssignProcessToJobObject.restype = [w.HANDLE, w.HANDLE], w.BOOL
        self.api.CloseHandle.argtypes, self.api.CloseHandle.restype = [w.HANDLE], w.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError("WORKER_JOB_OBJECT_CREATION_FAILED")
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not self.api.AssignProcessToJobObject(self.handle, w.HANDLE(int(process._handle))):
            self.close()
            raise OSError("WORKER_JOB_OBJECT_ASSIGNMENT_FAILED")

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None
