"""Launcher-to-child liveness without PID reuse races or killing the game.

The parent keeps the write end of the child's stdin pipe open. A launcher
crash, SIGKILL or normal exit closes that handle in the OS; EOF requests the
bridge's ordinary, bounded cleanup path. Do not inherit this pipe into games.
"""
from __future__ import annotations

import signal
import os
import sys
import threading


def parent_stream():
    """Recover piped stdin even in a PyInstaller Windows --windowed executable."""
    if sys.stdin is not None:
        stream = getattr(sys.stdin, "buffer", sys.stdin)
        try:
            # Never block a daemon thread while holding Python's buffered-stdin
            # lock: a normal early exit could otherwise fail at finalization.
            return os.fdopen(os.dup(stream.fileno()), "rb", buffering=0)
        except (AttributeError, OSError, ValueError):
            return stream  # In-memory/test streams have no OS descriptor.
    if os.name != "nt":
        return os.fdopen(os.dup(0), "rb", buffering=0)
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = (wintypes.DWORD,)
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.argtypes = ()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.DuplicateHandle.argtypes = (wintypes.HANDLE, wintypes.HANDLE,
                                      wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE),
                                      wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.DuplicateHandle.restype = wintypes.BOOL
    handle = kernel.GetStdHandle(-10 & 0xffffffff)
    if not handle or handle == ctypes.c_void_p(-1).value:
        raise OSError("Launcher liveness pipe is missing")
    process = kernel.GetCurrentProcess()
    duplicate = wintypes.HANDLE()
    if not kernel.DuplicateHandle(process, handle, process, ctypes.byref(duplicate), 0, False, 2):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(duplicate.value, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle(duplicate)
        raise
    return os.fdopen(descriptor, "rb", buffering=0)


def watch_parent_stream(stream, stop):
    """Start a daemon EOF watcher; the caller owns the supplied stop Event."""
    if stream is None:
        stop.set()
        return None

    def watch():
        try:
            while stream.read(1):
                pass  # The protocol carries no data; any bytes are ignored.
        except (OSError, ValueError):
            pass
        finally:
            stop.set()

    thread = threading.Thread(target=watch, name="launcher-liveness", daemon=True)
    thread.start()
    return thread


def install_stop_signals(stop):
    """Map catchable termination signals to normal cleanup, preserving handlers."""
    previous = {}
    if threading.current_thread() is not threading.main_thread():
        return previous
    for name in ("SIGTERM", "SIGINT", "SIGHUP", "SIGBREAK"):
        number = getattr(signal, name, None)
        if number is not None:
            previous[number] = signal.getsignal(number)
            signal.signal(number, lambda _number, _frame: stop.set())
    return previous


def restore_signals(previous):
    for number, handler in previous.items():
        signal.signal(number, handler)
