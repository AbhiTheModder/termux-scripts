# -* coding: utf-8 *-
# @auhtor: AbhiTheModder

"""
usage: flutter_ssl_patch.py [-h] [-b BINARY] [-a {arm,arm64,x86,x64}] [-P {android,ios,windows,linux}] [-p]

Search & patch for SSL verification bypass in flutter binary.

options:
  -h, --help            show this help message and exit
  -b BINARY, --binary BINARY
                        Path to the binary file
  -a {arm,arm64,x86,x64}, --arch {arm,arm64,x86,x64}
                        Binary arch
  -P {android,ios,windows,linux}, --platform {android,ios,windows,linux}
                        Target platform
  -p, --print           Do Not Patch, Just Print Details

Example(s):
1. Outside r2-shell:
~$ python3 flutter_ssl_patch.py --binary libflutter.so
Analyzing function calls...
Searching for offset...
ssl_verify_peer_cert patched successfully!

2. Inside r2-shell:
[0x00000000]> #!pipe python3 flutter_ssl_patch.py
Analyzing function calls...
Searching for offset...
ssl_verify_peer_cert patched successfully!
"""

import json
import os
import argparse
import importlib
import subprocess
import sys

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def import_library(library_name: str, package_name: str = None):
    """
    Loads a library, or installs it in ImportError case
    :param library_name: library name (import example...)
    :param package_name: package name in PyPi (pip install example)
    :return: loaded module
    """
    if package_name is None:
        package_name = library_name

    try:
        return importlib.import_module(library_name)
    except ImportError as exc:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name], check=True
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Failed to install library {package_name} (pip exited with code {completed.returncode})"
            ) from exc
        return importlib.import_module(library_name)


import_library("r2pipe")

import r2pipe

# https://github.com/NVISOsecurity/disable-flutter-tls-verification/blob/main/disable-flutter-tls.js
patterns = {
    "android": {
        "arm64": [
            ("F. 0F 1C F8 F. 5. 01 A9 F. 5. 02 A9 F. .. 03 A9 .. .. .. .. 68 1A 40 F9", 0),
            ("F. 43 01 D1 FE 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 13 00 40 F9 F4 03 00 AA 68 1A 40 F9", 0),
            ("FF 43 01 D1 FE 67 01 A9 .. .. 06 94 .. 7. 06 94 68 1A 40 F9 15 15 41 F9 B5 00 00 B4 B6 4A 40 F9", 0),
            ("F. 0F 1C F8 F. .. 0. .. .. .. .. .9 .. .. 0. .. 68 1A 40 F9 15 .. 4. F9 B5 00 00 B4 B6 46 40 F9", 0),
            ("FE 0F 1C F8 ?? ?? ?? 9? 13 00 40 F9 F4 03 00 AA 68 1A 40 F9 15 E9 40 F9 ?? ?? ?? B4 96 02 44 F9", 0),
            ("FF .3 01 D1 F. .. 01 A9 .. .. .. 94 .. .. .. 52 48 00 00 39 1A 50 40 F9 DA 02 00 B4 48 03 40 F9", 1),
            ("FF C3 01 D1 FD 7B 01 A9 ?? ?? ?? 9? 08 C0 46 39 ?? ?? ?? 34 F4 03 1F 2A E0 03 14 2A ?? ?? ?? 9? FD 7B 41 A9", 1),
        ],
        "arm": [
            ("2D E9 F. 4. D0 F8 00 80 81 46 D8 F8 18 00 D0 F8", 0),
        ],
        "x64": [
            ("55 41 57 41 56 41 55 41 54 53 50 49 89 fe 48 8b 1f 48 8b 43 30 4c 8b b8 d0 01 00 00 4d 85 ff 74 12 4d 8b a7 90 00 00 00 4d 85 e4 74 4a 49 8b 04 24 eb 46", 0),
            ("55 41 57 41 56 41 55 41 54 53 50 49 89 f. 4. 8b .. 4. 8b 4. 30 4c 8b .. .. 0. 00 00 4d 85 .. 74 1. 4d 8b", 0),
            ("55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FF 48 8B 1F 48 8B 43 30 4C 8B A0 28 02 00 00 4D 85 E4 74", 0),
            ("55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FE 4C 8B 27 49 8B 44 24 30 48 8B 98 D0 01 00 00 48 85 DB", 0),
            ("55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02 50 48 8B AF A. 00 00 00 48 85 ED 74 7. 48 83 7D 00 00 74", 1),
        ],
        "x86": [
            ("55 89 E5 53 57 56 83 E4 F0 83 EC 20 E8 00 00 00 00 5B 81 C3 2B 79 66 00 8B 7D 08 8B 17 8B 42 18 8B 80 88 01", 0),
        ],
    },
    "ios": {
        "arm64": [
            ("FF 83 01 D1 FA 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 FD 7B 05 A9 FD 43 01 91 F4 03 00 AA 68 31 00 F0 08 01 40 F9 08 01 40 F9 E8 07 00 F9", 0),
            ("FF 83 01 D1 FA 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 FD 7B 05 A9 FD 43 01 91 F. 03 00 AA .. 0. 40 F. .8 .. 40 F9 .. .. 4. F9 .. 00 00", 0),
            ("FF 43 01 D1 F8 5F 01 A9 F6 57 02 A9 F4 4F 03 A9 FD 7B 04 A9 FD 03 01 91 F3 03 00 AA 14 00 40 F9 88 1A 40 F9 15 E9 40 F9 B5 00 00 B4 B6 46 40 F9", 0),
        ],
    },
    "windows": {
        "x64": [
            ("41 57 41 56 41 55 41 54 56 57 53 48 83 EC 40 4. 89 CF 48 8B 05 .. .. .. 00 48 31 E0 48 89 44 24 38 4. 8B 31 4. 8B", 0),
            ("41 57 41 56 41 55 41 54 56 57 55 53 48 83 EC 38 48 89 CF 48 8B 05 20 45 C6 00 48 31 E0 48 89 44 24 30 48 8B 31 48", 0),
        ],
    },
    "linux": {
        "x64": [
            ("55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FE 4C 8B 27 49 8B 44 24 30 48 8B 98 D0 01 00 00 48 85 DB", 0),
        ],
    },
}


def get_r2_version():
    """
    Gets the version of radare2 installed on the system
    :return: version string
    """
    try:
        result = subprocess.run(
            ["r2", "-V"], capture_output=True, text=True, check=True
        )
        # Extract the version number from the output
        results = result.stdout.strip().split()
        for result in results:
            if result.startswith(("5.", "6.")):
                result = result.split("-")[0]
                return result
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def detect_platform(binary_path):
    fname = os.path.basename(binary_path).lower()
    if "flutter_windows" in fname:
        return "windows"
    if "flutter_linux_gtk" in fname:
        return "linux"
    if "libflutter" in fname:
        return "android"
    if "flutter" in fname:
        return "ios"
    return "android"


def find_offset(r2, patterns, is_iA=False, arch=None, platform=None):
    """
    Searches for patterns in the binary using radare2
    :param r2: r2pipe instance
    :param patterns: dictionary of patterns
    """
    if not arch:
        if is_iA:
            arch = json.loads(r2.cmd("iAj"))
        else:
            arch = json.loads(r2.cmd("iaj"))
        arch_value = arch["bins"][0]["arch"]
        arch_bits = arch["bins"][0]["bits"]
        if arch_value == "arm" and arch_bits == 64:
            arch = "arm64"
        elif arch_value == "arm" and arch_bits == 16:
            arch = "arm"
        elif arch_value == "x86" and arch_bits == 64:
            arch = "x64"
        elif arch_value == "x86" and arch_bits == 32:
            arch = "x86"
        else:
            print(f"{RED}Unsupported architecture: {arch_value}{NC}")
            return

    if not platform:
        platform = "android"

    matches = []
    seen = set()
    if platform in patterns and arch in patterns[platform]:
        for pattern, retval in patterns[platform][arch]:
            search_result = r2.cmd(f"/x {pattern}")
            search_result = search_result.strip().split(" ")[0]
            if search_result:
                fname = "session_verify_cert_chain" if retval else "ssl_verify_peer_cert"
                print(f"{fname} found at: {BLUE}{search_result}{NC}")
                if search_result not in seen:
                    seen.add(search_result)
                    matches.append((search_result, retval))
        return matches
    else:
        print(f"{RED}No patterns found for platform '{platform}' and architecture '{arch}'{NC}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search & patch for SSL verification bypass in flutter binary."
    )
    parser.add_argument(
        "-b", "--binary", help="Path to the binary file", required=False
    )
    parser.add_argument(
        "-a",
        "--arch",
        help="Binary arch",
        choices=["arm", "arm64", "x86", "x64"],
        default=None,
        required=False,
    )
    parser.add_argument(
        "-P",
        "--platform",
        help="Target platform",
        choices=["android", "ios", "windows", "linux"],
        default=None,
        required=False,
    )
    parser.add_argument(
        "-p",
        "--print",
        help="Do Not Patch, Just Print Details",
        action="store_true",
        required=False,
    )
    args = parser.parse_args()

    if not args.arch:
        try:
            r2_version = tuple(map(int, get_r2_version().split(".")))
            ia_version = tuple(
                map(int, "5.9.5".split("."))
            )  # Because r2 depreciated `ia` 5.9.6 onwards
            is_iA = r2_version <= ia_version
        except Exception as e:
            print(f"{RED}Error: {str(e)}{NC}")
            sys.exit(1)

    if r2pipe.in_r2():
        r2 = r2pipe.open()
        r2.cmd("e log.quiet=true")
        r2.cmd("oo+")
    else:
        if not args.binary:
            print(f"{RED}Error: Please provide a binary file path.{NC}")
            sys.exit(1)
        r2 = r2pipe.open(args.binary, flags=["-w", "-e", "log.quiet=true"])
    print(f"{YELLOW}Analyzing function calls...{NC}")
    r2.cmd("aac")
    print(f"{YELLOW}Searching for offset...{NC}")
    platform = args.platform or detect_platform(args.binary) if args.binary else "android"
    if args.arch:
        result = find_offset(r2, patterns, arch=args.arch, platform=platform)
    else:
        result = find_offset(r2, patterns, is_iA, platform=platform)
    if result:
        for offset, retval in result:
            if not args.print:
                r2.cmd(f"{offset}")
                r2.cmd(f"wao ret{retval}")
                fname = "session_verify_cert_chain" if retval else "ssl_verify_peer_cert"
                print(f"{GREEN}{fname} patched successfully!{NC}")
    else:
        print(f"{RED}ssl_verify_peer_cert not found.{NC}")
    r2.quit()
