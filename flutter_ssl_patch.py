# -* coding: utf-8 *-
# @auhtor: AbhiTheModder

"""
usage: flutter_ssl_patch.py [-h] [--binary BINARY]

Search & patch for SSL verification bypass patterns in a binary.

options:
  -h, --help       show this help message and exit
  --binary BINARY  Path to the binary file

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

# https://github.com/NVISOsecurity/disable-flutter-tls-verification/blob/main/disable-flutter-tls.js#L25
patterns = {
    "arm64": [
        "F. 0F 1C F8 F. 5. 01 A9 F. 5. 02 A9 F. .. 03 A9 .. .. .. .. 68 1A 40 F9",
        "F. 43 01 D1 FE 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 13 00 40 F9 F4 03 00 AA 68 1A 40 F9",
        "FF 43 01 D1 FE 67 01 A9 .. .. 06 94 .. 7. 06 94 68 1A 40 F9 15 15 41 F9 B5 00 00 B4 B6 4A 40 F9",
    ],
    "arm": [
        "2D E9 F. 4. D0 F8 00 80 81 46 D8 F8 18 00 D0 F8",
    ],
    "x86": [
        "55 41 57 41 56 41 55 41 54 53 50 49 89 f. 4c 8b 37 49 8b 46 30 4c 8b a. .. 0. 00 00 4d 85 e. 74 1. 4d 8b",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FF 48 8B 1F 48 8B 43 30 4C 8B A0 28 02 00 00 4D 85 E4 74",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02 50 48 8B AF A. 00 00 00 48 85 ED 74 7. 48 83 7D 00 00 74",
    ],
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
            if result.startswith("5."):
                result = result.split("-")[0]
                return result
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_offset(r2, patterns, is_iA=False):
    """
    Searches for patterns in the binary using radare2
    :param r2: r2pipe instance
    :param patterns: dictionary of patterns
    """
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
        arch = "x86"
    else:
        print(f"{RED}Unsupported architecture: {arch_value}{NC}")
        return

    if arch in patterns:
        for arch in patterns:
            for pattern in patterns[arch]:
                search_result = r2.cmd(f"/x {pattern}")
                search_result = search_result.strip().split(" ")[0]
                if search_result:
                    search_fcn = r2.cmd(f"{search_result};afl.").strip().split(" ")[0]
                    return search_fcn


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search & patch for SSL verification bypass in flutter binary."
    )
    parser.add_argument("--binary", help="Path to the binary file", required=False)
    args = parser.parse_args()

    try:
        r2_version = tuple(map(int, get_r2_version().split(".")))
        ia_version = tuple(
            map(int, "5.9.5".split("."))
        )  # Because r2 depreciated `ia` 5.9.6 onwards
        if r2_version <= ia_version:
            is_iA = True
        else:
            is_iA = False
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
    offset = find_offset(r2, patterns, is_iA)
    if offset:
        r2.cmd(f"{offset}")
        r2.cmd("wao ret0")
        print(f"{GREEN}ssl_verify_peer_cert patched successfully!{NC}")
    else:
        print(f"{RED}ssl_verify_peer_cert not found.{NC}")
    r2.quit()