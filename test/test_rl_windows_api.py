from __future__ import annotations

import ctypes
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.windows_api import windows_abi_sizes


@unittest.skipUnless(sys.platform == "win32", "Windows API integration")
class TestWindowsApi(unittest.TestCase):
    def test_ctypes_abi_matches_windows_sdk_on_x64(self) -> None:
        if ctypes.sizeof(ctypes.c_void_p) != 8:
            self.skipTest("x64 ABI assertion")
        self.assertEqual(
            windows_abi_sizes(),
            {
                "PERFORMANCE_INFORMATION": 104,
                "PROCESSENTRY32W": 568,
                "PROCESS_MEMORY_COUNTERS": 72,
            },
        )


if __name__ == "__main__":
    unittest.main()
