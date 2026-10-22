"""Windows user-bound DPAPI encryption; no plaintext voice file or key on disk."""
import ctypes
from ctypes import wintypes
import sys


def _crypt(data, decrypt=False):
    if sys.platform != 'win32':
        raise RuntimeError('Le coffre vocal nécessite Windows et la protection DPAPI du compte courant.')
    class Blob(ctypes.Structure):
        _fields_ = [('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32',use_last_error=True)
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise OSError('Le coffre vocal ne peut pas être ouvert avec ce compte Windows.')
    try:
        return ctypes.string_at(target.data,target.size)
    finally:
        kernel.LocalFree(target.data)


def protect(data): return _crypt(data)
def unprotect(data): return _crypt(data,True)
