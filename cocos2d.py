import os
from zlib import decompress, MAX_WBITS, error as zlib_err
from xxtea import decrypt as xdec


def decrypt(file_path: str, key: str) -> None:
    ext = ".js"
    file_name = file_path.split(os.sep)[-1]

    with open(file_path, "rb") as file:
        encrypted_data = file.read()

    decrypted_data = xdec(encrypted_data, key, False)

    if len(decrypted_data) == 0:
        exit("Bad Key or File not encrypted!")

    try:
        decompressed = decompress(decrypted_data, 16+MAX_WBITS)
        decrypted_data = decompressed
    except zlib_err:
        pass

    with open(f"{file_name}{ext}", "wb") as file:
        file.write(decrypted_data)

    print(f"[*] Output: {file_name}{ext}")


if __name__ == "__main__":
    file_path: str = input("[?] File Path: ")
    key: str = input("[?] Key: ")
    if file_path and key:
        decrypt(file_path, key)
        print("[+] All Done!")
