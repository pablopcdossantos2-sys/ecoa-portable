"""Instância única: abrir o app de novo traz a janela da instância já aberta."""
from __future__ import annotations

import sys
import threading

IS_WINDOWS = sys.platform == "win32"
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    _k32.CreateMutexW.restype = wintypes.HANDLE
    _k32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    _k32.CreateEventW.restype = wintypes.HANDLE
    _k32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    _k32.OpenEventW.restype = wintypes.HANDLE
    _k32.SetEvent.argtypes = [wintypes.HANDLE]
    _k32.SetEvent.restype = wintypes.BOOL
    _k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _k32.WaitForSingleObject.restype = wintypes.DWORD
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL


class SingleInstance:
    def __init__(self, name: str = "Ecoa"):
        self._mutex_name = f"Local\\{name}_mutex"
        self._event_name = f"Local\\{name}_show"
        self._mutex = None
        self._event = None
        self._stop = threading.Event()

    def acquire(self) -> bool:
        """True se esta é a primeira instância. Caso contrário, avisa a primeira."""
        if not IS_WINDOWS:
            return True
        self._mutex = _k32.CreateMutexW(None, False, self._mutex_name)
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            handle = _k32.OpenEventW(EVENT_MODIFY_STATE, False, self._event_name)
            if handle:
                _k32.SetEvent(handle)
                _k32.CloseHandle(handle)
            return False
        self._event = _k32.CreateEventW(None, False, False, self._event_name)
        return True

    def listen(self, callback) -> None:
        """Chama ``callback`` (em outra thread) quando uma segunda instância é aberta."""
        if not IS_WINDOWS or not self._event:
            return

        def loop():
            while not self._stop.is_set():
                if _k32.WaitForSingleObject(self._event, 500) == WAIT_OBJECT_0:
                    callback()

        threading.Thread(target=loop, daemon=True, name="ecoa-singleton").start()

    def close(self) -> None:
        self._stop.set()
