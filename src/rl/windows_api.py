"""Narrow ctypes boundary for Windows process and system resource queries."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

ERROR_INVALID_PARAMETER = 87

_SNAP_PROCESS = 0x2
_QUERY_LIMITED = 0x1000
_SYNCHRONIZE = 0x00100000
_TERMINATE = 0x0001
_WAIT_OBJECT = 0
_WAIT_TIMEOUT = 0x102
_WAIT_FAILED = 0xFFFFFFFF
_NO_MORE_FILES = 18
_INVALID_HANDLE = ctypes.c_void_p(-1).value


@dataclass(frozen=True, slots=True)
class SystemMemory:
    physical_total_bytes: int
    physical_available_bytes: int
    commit_total_bytes: int
    commit_limit_bytes: int


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (name, ctypes.c_size_t)
        for name in (
            "PeakWorkingSetSize WorkingSetSize QuotaPeakPagedPoolUsage "
            "QuotaPagedPoolUsage QuotaPeakNonPagedPoolUsage "
            "QuotaNonPagedPoolUsage PagefileUsage PeakPagefileUsage"
        ).split()
    ]


class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = (
        [("cb", wintypes.DWORD)]
        + [
            (name, ctypes.c_size_t)
            for name in (
                "CommitTotal CommitLimit CommitPeak PhysicalTotal PhysicalAvailable "
                "SystemCache KernelTotal KernelPaged KernelNonpaged PageSize"
            ).split()
        ]
        + [
            ("HandleCount", wintypes.DWORD),
            ("ProcessCount", wintypes.DWORD),
            ("ThreadCount", wintypes.DWORD),
        ]
    )


class _FILETIME(ctypes.Structure):
    _fields_ = (("low", wintypes.DWORD), ("high", wintypes.DWORD))

    def as_int(self) -> int:
        return (int(self.high) << 32) | int(self.low)


def windows_abi_sizes() -> dict[str, int]:
    if sys.platform != "win32":
        raise OSError("Windows resource sampling requires Windows")
    return {
        "PERFORMANCE_INFORMATION": ctypes.sizeof(PERFORMANCE_INFORMATION),
        "PROCESSENTRY32W": ctypes.sizeof(PROCESSENTRY32W),
        "PROCESS_MEMORY_COUNTERS": ctypes.sizeof(PROCESS_MEMORY_COUNTERS),
    }


class WindowsCallError(OSError):
    def __init__(self, operation: str, code: int) -> None:
        super().__init__(code, f"{operation}: {ctypes.FormatError(code)}")
        self.winerror = code


def _pin(library: object, name: str, arguments: list[object], result: object) -> object:
    function = getattr(library, name)
    function.argtypes = arguments
    function.restype = result
    return function


class WindowsApi:
    """Own Win32 function signatures and translate failures into one error type."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("Windows resource sampling requires Windows")
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self.create_snapshot = _pin(
            k32,
            "CreateToolhelp32Snapshot",
            [wintypes.DWORD, wintypes.DWORD],
            wintypes.HANDLE,
        )
        self.first = _pin(
            k32,
            "Process32FirstW",
            [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)],
            wintypes.BOOL,
        )
        self.next = _pin(
            k32,
            "Process32NextW",
            [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)],
            wintypes.BOOL,
        )
        self.open = _pin(
            k32,
            "OpenProcess",
            [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD],
            wintypes.HANDLE,
        )
        self.times = _pin(
            k32,
            "GetProcessTimes",
            [wintypes.HANDLE] + [ctypes.POINTER(_FILETIME)] * 4,
            wintypes.BOOL,
        )
        self.wait = _pin(
            k32,
            "WaitForSingleObject",
            [wintypes.HANDLE, wintypes.DWORD],
            wintypes.DWORD,
        )
        self.close_handle = _pin(k32, "CloseHandle", [wintypes.HANDLE], wintypes.BOOL)
        self.terminate_process = _pin(
            k32,
            "TerminateProcess",
            [wintypes.HANDLE, wintypes.UINT],
            wintypes.BOOL,
        )
        self.memory = _pin(
            psapi,
            "GetProcessMemoryInfo",
            [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                wintypes.DWORD,
            ],
            wintypes.BOOL,
        )
        self.performance = _pin(
            psapi,
            "GetPerformanceInfo",
            [ctypes.POINTER(PERFORMANCE_INFORMATION), wintypes.DWORD],
            wintypes.BOOL,
        )

    @staticmethod
    def _error(operation: str) -> WindowsCallError:
        return WindowsCallError(operation, ctypes.get_last_error())

    def snapshot(self) -> tuple[tuple[int, int], ...]:
        handle = self.create_snapshot(_SNAP_PROCESS, 0)
        if handle == _INVALID_HANDLE:
            raise self._error("CreateToolhelp32Snapshot")
        rows: list[tuple[int, int]] = []
        try:
            entry = PROCESSENTRY32W(dwSize=ctypes.sizeof(PROCESSENTRY32W))
            ctypes.set_last_error(0)
            if not self.first(handle, ctypes.byref(entry)):
                code = ctypes.get_last_error()
                if code != _NO_MORE_FILES:
                    raise WindowsCallError("Process32FirstW", code)
                return ()
            while True:
                rows.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID)))
                ctypes.set_last_error(0)
                if not self.next(handle, ctypes.byref(entry)):
                    code = ctypes.get_last_error()
                    if code != _NO_MORE_FILES:
                        raise WindowsCallError("Process32NextW", code)
                    return tuple(rows)
        finally:
            self.close(handle)

    def open_process(self, pid: int) -> tuple[object, int]:
        handle = self.open(_QUERY_LIMITED | _SYNCHRONIZE | _TERMINATE, False, pid)
        if not handle:
            raise self._error("OpenProcess")
        try:
            creation = self.process_times(handle)[0]
        except BaseException:
            self.close(handle)
            raise
        return handle, creation

    def process_times(self, handle: object) -> tuple[int, int, int, int]:
        values = [_FILETIME() for _ in range(4)]
        if not self.times(handle, *map(ctypes.byref, values)):
            raise self._error("GetProcessTimes")
        return tuple(value.as_int() for value in values)  # type: ignore[return-value]

    def is_alive(self, handle: object) -> bool:
        status = int(self.wait(handle, 0))
        if status in (_WAIT_OBJECT, _WAIT_TIMEOUT):
            return status == _WAIT_TIMEOUT
        if status == _WAIT_FAILED:
            raise self._error("WaitForSingleObject")
        raise WindowsCallError("WaitForSingleObject", status)

    def working_set(self, handle: object) -> int:
        counters = PROCESS_MEMORY_COUNTERS(cb=ctypes.sizeof(PROCESS_MEMORY_COUNTERS))
        if not self.memory(handle, ctypes.byref(counters), counters.cb):
            raise self._error("GetProcessMemoryInfo")
        return int(counters.WorkingSetSize)

    def system_memory(self) -> SystemMemory:
        info = PERFORMANCE_INFORMATION(cb=ctypes.sizeof(PERFORMANCE_INFORMATION))
        if not self.performance(ctypes.byref(info), info.cb):
            raise self._error("GetPerformanceInfo")
        page = int(info.PageSize)
        return SystemMemory(
            int(info.PhysicalTotal) * page,
            int(info.PhysicalAvailable) * page,
            int(info.CommitTotal) * page,
            int(info.CommitLimit) * page,
        )

    def terminate(self, handle: object, exit_code: int = 1) -> None:
        if not self.terminate_process(handle, exit_code):
            raise self._error("TerminateProcess")

    def close(self, handle: object) -> None:
        if not self.close_handle(handle):
            raise self._error("CloseHandle")
