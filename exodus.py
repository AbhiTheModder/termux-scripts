import argparse
import importlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict

# Define color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
GREY = "\033[0;37m"
DIM = "\033[2m"
NC = "\033[0m"  # No Color

APK_MAGIC = b"PK\x03\x04"
DEX_MAGIC = b"dex\n"
ELF_MAGIC = b"\x7fELF"


def gen_rule():
    """Generate YARA rules from Exodus API."""
    url = "https://reports.exodus-privacy.eu.org/api/trackers"
    try:
        with urllib.request.urlopen(url) as response:
            data_bytes = response.read()
        data = json.loads(data_bytes)
    except urllib.error.URLError:
        print(f"Error connecting to {url}. Skipping rule generation.", file=sys.stderr)
        return

    trackers = data.get("trackers")

    for _, info in trackers.items():
        code_signature = info.get("code_signature")
        network_signature = info.get("network_signature")
        if network_signature == "\\.facebook\\.com":
            network_signature = ""
        if info.get("name") == "Google Ads":
            network_signature = ""
            code_signature = "com.google.android.gms.ads.identifier"
        code_signature = code_signature.replace(".", "\\.").replace("/", r"\\")
        network_signature = network_signature.replace("/", r"\\")
        code_signature2 = code_signature.replace(".", "/")
        if not code_signature and not network_signature:
            continue
        rule_name = re.sub(
            r"[^a-zA-Z]", "_", info.get("name").strip().replace(" ", "_")
        ).replace("__", "_")
        if rule_name.endswith("_"):
            rule_name = rule_name[:-1]
        rule_name = rule_name.lower()

        yara_rule = f"""
rule {rule_name} : tracker
{{
    meta:
        description = "{info.get("name").replace("Google", "G.").replace("Facebook", "FB.").replace("Notifications", "Notifs")}"
        author      = "Abhi & Exodus API"
        url         = "{info.get("website")}"

    strings:
"""
        if code_signature:
            yara_rule += f"        $code_signature    = /{code_signature}/"
        if network_signature:
            yara_rule += f"\n        $network_signature = /{network_signature}/"
        if code_signature2:
            yara_rule += f"\n        $code_signature2   = /{code_signature2}/"

        yara_rule += """

    condition:
        any of them
}
"""
        existing_rules = ""
        if os.path.exists("trackers.yara"):
            with open("trackers.yara", "r") as f:
                existing_rules = f.read()
        if rule_name not in existing_rules:
            with open("trackers.yara", "a") as f:
                f.write(yara_rule)
        else:
            print(f"Duplicate rule name found: {rule_name}. Skipping.")


def import_library(library_name: str, package_name: str | None = None):
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
        import subprocess

        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name], check=True
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Failed to install library {package_name} (pip exited with code {completed.returncode})"
            ) from exc
        return importlib.import_module(library_name)


yara = import_library("yara", "yara-python-dex")


def scan_apk(apk_path: str, rules_path: str):
    """Scan APK, DEX, and ELF files (iterative, handles embedded APKs)"""
    rules = yara.compile(filepath=rules_path)
    results = {
        "apk": defaultdict(lambda: defaultdict(set)),
        "dex": defaultdict(lambda: defaultdict(lambda: defaultdict(set))),
        "elf": defaultdict(lambda: defaultdict(lambda: defaultdict(set))),
    }

    def scan_file(file_data, file_name, file_type):
        for match in rules.match(data=file_data):
            for _, offset, data in match.strings:
                rule_type = str(offset).replace("$", "")
                results[file_type][file_name][match.rule][rule_type].add(
                    data.decode("utf-8", errors="ignore")
                )

    apk_queue = []
    if isinstance(apk_path, str):
        apk_queue.append((apk_path, None))
    else:
        apk_queue.append((None, apk_path))

    while apk_queue:
        current_path, current_fileobj = apk_queue.pop(0)
        try:
            z = (
                zipfile.ZipFile(current_path)
                if current_path
                else zipfile.ZipFile(current_fileobj)
            )
        except Exception as e:
            print(f"Failed to open APK: {current_path or current_fileobj}: {e}")
            continue

        if current_path:
            for match in rules.match(current_path):
                for _, offset, data in match.strings:
                    rule_type = str(offset).replace("$", "")
                    results["apk"][match.rule][rule_type].add(
                        data.decode("utf-8", errors="ignore")
                    )

        for file in z.namelist():
            with z.open(file) as f:
                file_data = f.read()
                if file_data.startswith(DEX_MAGIC):
                    print(f"\rScanning {file}", end="")
                    scan_file(file_data, file, "dex")
                elif file_data.startswith(ELF_MAGIC):
                    print(f"\rScanning {file}", end="")
                    scan_file(file_data, file, "elf")
                elif file_data.startswith(APK_MAGIC):
                    print(f"\rFound embedded APK: {file}")
                    embedded_apk = io.BytesIO(file_data)
                    apk_queue.append((None, embedded_apk))

    return results


def to_json(results):
    """Convert results to JSON"""
    json_results = {"apk": {}, "dex": {}, "elf": {}}

    for rule, types_dict in results["apk"].items():
        json_results["apk"][rule] = {
            rule_type: sorted(list(sigs)) for rule_type, sigs in types_dict.items()
        }

    for dex_file, rules_dict in results["dex"].items():
        json_results["dex"][dex_file] = {
            rule: {
                rule_type: sorted(list(sigs)) for rule_type, sigs in types_dict.items()
            }
            for rule, types_dict in rules_dict.items()
        }

    for elf_file, rules_dict in results["elf"].items():
        json_results["elf"][elf_file] = {
            rule: {
                rule_type: sorted(list(sigs)) for rule_type, sigs in types_dict.items()
            }
            for rule, types_dict in rules_dict.items()
        }

    return json_results


def print_matches(results):
    """Print matches"""
    if results["apk"] and len(results["apk"]):
        print(f"{GREEN}\nMatches in APK:{NC}")
        for rule, types_dict in sorted(results["apk"].items()):
            print(f"\n{YELLOW}Rule: {rule}{NC}")
            for rule_type, sigs in sorted(types_dict.items()):
                print(f"{BLUE}Type: {DIM}{rule_type.replace('2', '')}{NC}")
                for sig in sorted(sigs):
                    print(f"{GREY}  {sig}{NC}")

    if results["dex"] and len(results["dex"]):
        for dex_file, rules_dict in sorted(results["dex"].items()):
            print(f"\n{GREEN}Matches in {dex_file}:{NC}")
            for rule, types_dict in sorted(rules_dict.items()):
                print(f"\n{YELLOW}Rule: {rule}{NC}")
                for rule_type, sigs in sorted(types_dict.items()):
                    print(f"{BLUE}Type: {DIM}{rule_type.replace('2', '')}{NC}")
                    for sig in sorted(sigs):
                        print(f"{GREY}  {sig}{NC}")

    if results.get("elf") and len(results["elf"]):
        for elf_file, rules_dict in sorted(results["elf"].items()):
            print(f"\n{GREEN}Matches in {elf_file}:{NC}")
            for rule, types_dict in sorted(rules_dict.items()):
                print(f"\n{YELLOW}Rule: {rule}{NC}")
                for rule_type, sigs in sorted(types_dict.items()):
                    print(f"{BLUE}Type: {DIM}{rule_type.replace('2', '')}{NC}")
                    for sig in sorted(sigs):
                        print(f"{GREY}  {sig}{NC}")


def main():
    parser = argparse.ArgumentParser(description="Exodus CLI")
    parser.add_argument("apk", nargs="?", help="Path to APK file")
    parser.add_argument(
        "-r",
        "--rules",
        nargs="?",
        default="trackers.yara",
        const="trackers.yara",
        help="Path to YARA rules file",
    )
    parser.add_argument(
        "-j", "--json", nargs="?", const="output.json", help="Save results to JSON file"
    )
    parser.add_argument(
        "-g",
        "--gen",
        nargs="?",
        const="default",
        help="Generate YARA rules.",
    )
    args = parser.parse_args()

    if args.gen:
        if os.path.exists(args.rules):
            print(
                f"File {args.rules} already exists, please don't abuse Exodus. Exiting."
            )
            sys.exit(1)

        gen_rule()
        print()

        print("\033c", end="") if args.apk else None
        sys.exit(0) if not args.apk else None

    if not args.apk:
        print(f"{RED}ERROR:{NC} The following arguments are required: apk{NC}")
        parser.print_help()
        sys.exit(1)

    results = scan_apk(args.apk, args.rules)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(to_json(results), f, indent=2)
        print(f"Results saved to {args.json}")
    else:
        print_matches(results)


if __name__ == "__main__":
    main()
