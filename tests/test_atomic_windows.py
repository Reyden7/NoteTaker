"""Actual Windows sharing violation, not a mocked replace implementation."""
import ctypes
import json
import os
import threading
import time
from ctypes import wintypes as w
import pytest
from notetaker.infrastructure.atomic import atomic_json


@pytest.mark.skipif(os.name != 'nt', reason='Windows file sharing semantics')
def test_temporary_reader_lock_keeps_old_json_then_replaces_atomically(tmp_path):
    path = tmp_path/'report.json'
    atomic_json(path, {'complete': 'old'})
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
    api.CreateFileW.restype = w.HANDLE
    api.CloseHandle.argtypes, api.CloseHandle.restype = [w.HANDLE], w.BOOL
    handle = api.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)  # read+write sharing, no delete
    assert handle != w.HANDLE(-1).value
    failures = []
    def replace():
        try:
            atomic_json(path, {'complete': 'new'})
        except BaseException as error:
            failures.append(error)
    thread = threading.Thread(target=replace)
    thread.start()
    try:
        time.sleep(.15)
        assert json.loads(path.read_text(encoding='utf-8')) == {'complete': 'old'}
    finally:
        api.CloseHandle(handle)
    thread.join(timeout=5)
    assert not thread.is_alive() and not failures
    assert json.loads(path.read_text(encoding='utf-8')) == {'complete': 'new'}
    assert list(tmp_path.glob('*.tmp')) == []
