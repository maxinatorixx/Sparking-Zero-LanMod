"""Conservative local process check before modifying this game's files/saves."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path

NAMES = {"sparkingzero.exe", "sparkingzero-win64-shipping.exe"}


def game_running():
    # Refuse any running copy, even another installation: false negatives are
    # worse than asking the operator to close a second copy first.
    if os.name != "nt":
        for process in Path("/proc").iterdir():
            if not process.name.isdecimal():
                continue
            try:
                args = (process / "cmdline").read_bytes().split(b"\0")
            except (FileNotFoundError, ProcessLookupError):
                continue
            except PermissionError:
                continue  # Other OS users cannot write this user's save via us.
            for arg in args:
                name = arg.decode("utf-8", errors="replace").replace("\\", "/").rsplit("/", 1)[-1].lower()
                if name in NAMES:
                    return True
        return False

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError("Cannot verify that the game is closed")
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        present = kernel.Process32FirstW(handle, ctypes.byref(entry))
        if not present:
            raise OSError("Cannot enumerate game processes")
        while present:
            if entry.szExeFile.lower() in NAMES:
                return True
            present = kernel.Process32NextW(handle, ctypes.byref(entry))
        if ctypes.get_last_error() not in (0, 18):  # ERROR_NO_MORE_FILES
            raise OSError("Process enumeration did not complete")
        return False
    finally:
        kernel.CloseHandle(handle)
