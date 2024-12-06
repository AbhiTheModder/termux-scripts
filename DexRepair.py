#!/usr/bin/env python3

#  This file is part of RevEngi - @RevEngiBot (Telegram Bot)
#  Copyright (C) 2023-present RevEngiSquad - Organization
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import argparse
import struct
import zlib
import hashlib

# ref: https://source.android.com/docs/core/runtime/dex-format#embedded-in-header_item
DEX_MAGIC_035 = b"dex\n035\0"
DEX_MAGIC_037 = b"dex\n037\0"
DEX_MAGIC_038 = b"dex\n038\0"
DEX_MAGIC_039 = b"dex\n039\0"
DEX_MAGIC_VERSIONS = [DEX_MAGIC_035, DEX_MAGIC_037, DEX_MAGIC_038, DEX_MAGIC_039]


class DexRepairError(Exception):
    pass


def is_valid_dex_magic(dex_file):
    """
    This function checks if the DEX magic number in the given bytearray is valid.

    Parameters:
    dex_file (bytearray): The bytearray containing the dex data.

    Returns:
    bool: True if the magic number is valid, False otherwise.

    Note:
    The DEX magic number is the first 8 bytes of the dex data. The valid magic numbers are defined in the DEX_MAGIC_VERSIONS list.
    This function returns True if the magic number is in the list of valid magic numbers, and False otherwise.
    """
    magic = dex_file[:8]
    return magic in DEX_MAGIC_VERSIONS


def repair_dex_magic(dex_data: bytearray):
    """
    This function checks if the DEX magic number in the given bytearray is valid. If it is not valid, it replaces the magic number with a valid one (DEX_MAGIC_035).

    Parameters:
    dex_data (bytearray): The bytearray containing the dex data.

    Returns:
    bytearray: The bytearray containing the updated dex data.

    Note:
    The DEX magic number is the first 8 bytes of the dex data. The valid magic number for this function is DEX_MAGIC_035.
    If the magic number is not valid, it is updated with the valid magic number.
    """

    if not is_valid_dex_magic(dex_data):
        dex_data[:8] = DEX_MAGIC_035
    return dex_data


def update_dex_hashes(dex_data: bytearray, repair_sha1: bool = False):
    """
    This function updates the checksum and signature in the DEX header of a given bytearray containing dex data.

    Parameters:
    dex_data (bytearray): The bytearray containing the dex data.
    repair_sha1 (bool): If True, the SHA-1 signature is updated. If False, the SHA-1 signature is not updated.

    Returns:
    bytearray: The bytearray containing the updated dex data.

    Note:
    The checksum is calculated using the zlib.adler32 function, starting from the 13th byte of the dex data.
    The signature is calculated using the hashlib.sha1 function, starting from the 33rd byte of the dex data.
    The updated checksum is then packed into a 4-byte little-endian integer and written back into the dex data, starting from the 9th byte.
    The updated signature is then written back into the dex data, starting from the 13th byte.
    """
    if repair_sha1:
        signature = hashlib.sha1(dex_data[32:]).digest()
        print(f"Signature: {signature.hex()}")
        dex_data[12:32] = signature

    checksum = zlib.adler32(dex_data[12:])
    print(f"Checksum: {checksum:#x}")
    dex_data[8:12] = struct.pack("<I", checksum)

    return dex_data


def repair_dex(
    dex_path: str,
    repair_sha1: bool = False,
    output_dex_path: str = None,
):
    """
    This function repairs dex files in the given path. If the path is a directory, it will repair all dex files within that directory. If the path is a file, it will repair that specific dex file.

    Parameters:
    dex_path (str): The path to the dex file or directory containing dex files.
    repair_sha1 (bool, optional): If True, the SHA-1 signature is updated. If False, the SHA-1 signature is not updated. Default is False.
    output_dex_path (str, optional): The output path for the repaired dex files. If not provided, the repaired dex files will be overwritten in the original location.

    Returns:
    None

    Raises:
    DexRepairError: If the provided dex_path is not a valid directory or file.
    """
    if os.path.isdir(dex_path):
        for filename in os.listdir(dex_path):
            if filename.endswith(".dex"):
                file_path = os.path.join(dex_path, filename)
                output_file_path = (
                    os.path.join(output_dex_path, filename) if output_dex_path else None
                )
                if not os.path.isdir(output_dex_path):
                    raise DexRepairError(f"{output_dex_path} not a directory!")
                print(f"Repairing {file_path}...")
                repair_dex_file(file_path, repair_sha1, output_file_path)
    elif os.path.isfile(dex_path):
        repair_dex_file(dex_path, repair_sha1, output_dex_path)
    else:
        raise DexRepairError(f"Path not found: {dex_path}")


def repair_dex_file(
    dex_file_path: str, repair_sha1: bool = False, output_dex_path: str = None
):
    """
    This function repairs a single dex file by fixing the DEX magic number and updating the checksum and signature in the DEX header. The repaired dex file is then written to the output path if it is provided, or to the original path if it is not.

    Parameters:
    dex_file_path (str): The path to the dex file to be repaired.
    repair_sha1 (bool, optional): If True, the SHA-1 signature is updated. If False, the SHA-1 signature is not updated. Default is False.
    output_dex_path (str, optional): The output path for the repaired dex file. If not provided, the repaired dex file will be overwritten in the original location.

    Returns:
    None

    Raises:
    DexRepairError: If the provided dex_file_path is not a valid file.
    """
    try:
        with open(dex_file_path, "rb") as f:
            dex_data = bytearray(f.read())
    except FileNotFoundError:
        raise DexRepairError(f"DEX file not found: {dex_file_path}")

    dex_data = repair_dex_magic(dex_data)
    dex_data = update_dex_hashes(dex_data, repair_sha1)

    if output_dex_path:
        with open(output_dex_path, "wb") as f:
            f.write(dex_data)
    else:
        with open(dex_file_path, "wb") as f:
            f.write(dex_data)


def main():
    epilog = "A command-line tool for repairing DEX files. It fixes the DEX magic number and updates the checksum and signature in the DEX header."
    parser = argparse.ArgumentParser(description="DEX Repair Tool", epilog=epilog)
    parser.add_argument("dex_file", help="Path to the DEX file")
    parser.add_argument("-o", "--output", help="Path to the output DEX file (optional)")
    parser.add_argument(
        "-s", "--sha", action="store_true", help="Repair SHA1 hash (optional)"
    )

    args = parser.parse_args()

    if args.output:
        output = args.output
    else:
        output = args.dex_file.replace(".dex", "_repaired.dex")

    try:
        repair_dex(args.dex_file, args.sha, output)
        print("DEX repair completed successfully.")

    except DexRepairError as e:
        print(f"Error during DEX repair: {e}")


if __name__ == "__main__":
    main()
