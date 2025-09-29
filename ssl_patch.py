# -* coding: utf-8 *-
# @auhtor: AbhiTheModder

import argparse
import os
import re
import subprocess
import tempfile
from zipfile import BadZipFile, ZipFile

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"

APKEDITOR_PATH = "APKEditor.jar"  # Please replace with your apkeditor path :)
OKHTTP3_SEARCH_REGEX = r"(\.method public (final )?\S+\(Ljava/lang/String;L[^;]+;\)V)(?:(?!\.end\smethod)[\s\S])*?check-cast [vp]\d+, Ljava/security/cert/X509Certificate;(?:(?!\.end\smethod)[\s\S])*?Ljavax/net/ssl/SSLPeerUnverifiedException;(?:(?!\.end\smethod)[\s\S])*?\.end\smethod"
OKHTTP3_REPLACE_REGEX = r"\1\n\t.registers 3\n\n\treturn-void\n.end method"
JAVAX_SEARCH_REGEX = r"(\.method public (final )?\S+\(Ljava/lang/String;Ljavax/net/ssl/SSLSession;\)Z)(?:(?!\.end\smethod)[\s\S])*?\.end\smethod"
JAVAX_REPLACE_REGEX = (
    r"\1\n\t.registers 3\n\n\tconst/4 v0, 0x1\n\n\treturn v0\n.end method"
)
XML_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system"/>
            <certificates overridePins="true" src="user"/>
        </trust-anchors>
    </base-config>
    <debug-overrides>
        <trust-anchors>
            <certificates src="system"/>
            <certificates overridePins="true" src="user"/>
        </trust-anchors>
    </debug-overrides>
</network-security-config>"""


def merge_apks(file_path: str) -> str | None:
    file_name = os.path.basename(file_path)
    out_path = os.path.join(
        os.path.dirname(file_path), file_name.rsplit(".", maxsplit=1)[0] + ".apk"
    )
    cmdr = ["java", "-jar", APKEDITOR_PATH, "m", "-i", file_path, "-o", out_path]
    try:
        subprocess.run(cmdr, check=True)
        return out_path
    except subprocess.CalledProcessError:
        print(f"{RED}ERROR: Failed to merge apk{NC}")
        return None


# https://github.com/AbhiTheModder/termux-scripts/blob/1e90d618bc9725798c96ca1313d79a71e31b5dcb/tgpatcher.py#L240
def apply_regex(root_directory: str, search_pattern: str, replace_pattern: str):
    """Apply a regex search and replace patch across all smali files in the root directory."""
    pattern = re.compile(search_pattern)

    print(f"INFO: Applying regex patch to {root_directory}")

    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if filename.endswith(".smali"):
                file_path = os.path.join(dirpath, filename)
                with open(file_path, "r") as file:
                    file_content = file.read()

                new_content = pattern.sub(replace_pattern, file_content)

                if new_content != file_content:
                    with open(file_path, "w") as file:
                        file.write(new_content)
                    print(f"INFO: Applied regex patch to {file_path}")


def decompile_apk(temp_dir: str, file_path: str, okhttp: bool) -> None:
    cmdr = [
        "java",
        "-jar",
        APKEDITOR_PATH,
        "d",
        "-i",
        file_path,
        "-o",
        f"{temp_dir}/out",
        "-dex",
        "-f",
    ]
    if okhttp:
        cmdr.remove("-dex")
    try:
        subprocess.run(cmdr, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        exit(1)


def recompile_apk(temp_dir: str, file_name: str) -> None:
    cmdr = [
        "java",
        "-jar",
        APKEDITOR_PATH,
        "b",
        "-i",
        f"{temp_dir}/out",
        "-o",
        file_name,
        "-f",
    ]
    try:
        subprocess.run(cmdr, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        exit(1)


def find_next_id(root) -> str:
    xml_ids = []
    pattern = re.compile(r"0x7f([0-9a-f]{2})([0-9a-f]{4})", re.IGNORECASE)
    used_prefixes = set()

    for elem in root.findall("public"):
        id_value = elem.get("id")
        if id_value and pattern.match(id_value):
            used_prefixes.add((int(id_value, 16) & 0x00FF0000) >> 16)
        if elem.get("type") == "xml" and id_value and pattern.match(id_value):
            xml_ids.append(int(id_value, 16))

    if not xml_ids:
        default_prefix = 0x14
        if default_prefix in used_prefixes:
            for candidate in range(0x10, 0x80):
                if candidate not in used_prefixes:
                    default_prefix = candidate
                    break
        base = 0x7F000000 | (default_prefix << 16)
        return hex(base)

    first_id = xml_ids[0]
    type_prefix = (first_id & 0x00FF0000) >> 16
    base = 0x7F000000 | (type_prefix << 16)
    next_id = max(xml_ids) + 1
    if ((next_id & 0x00FF0000) >> 16) != type_prefix:
        next_id = base
        while next_id in xml_ids:
            next_id += 1
    return hex(next_id)


def modify_public_xml(xml_file: str) -> None:
    import xml.etree.ElementTree as ET  # skipcq

    import defusedxml.ElementTree as DET

    tree = DET.parse(xml_file)
    root = tree.getroot()

    for elem in root.findall("public"):
        if elem.get("name") == "network_security_config":
            print("network_security_config already exists. No modification needed.")
            return

    new_id = find_next_id(root)

    new_element = ET.Element("public")
    new_element.set("id", new_id)
    new_element.set("type", "xml")
    new_element.set("name", "network_security_config")

    last_xml = None
    for elem in root.findall("public"):
        if elem.get("type") == "xml":
            last_xml = elem

    if last_xml is not None:
        index = list(root).index(last_xml) + 1
        root.insert(index, new_element)
    else:
        root.append(new_element)

    tree.write(xml_file, encoding="utf-8", xml_declaration=True)


def modify_xml(patch_path: str) -> None:
    import xml.etree.ElementTree as ET  # skipcq

    import defusedxml.ElementTree as DET

    config_file_path = None
    for root, _, files in os.walk(patch_path):
        for file in files:
            if file == "network_security_config.xml":
                config_file_path = os.path.join(root, file)
                break
        if config_file_path:
            break

    if not config_file_path:
        config_file_path = os.path.join(patch_path, "network_security_config.xml")
        with open(config_file_path, "w") as f:
            f.write(XML_CONTENT)
    else:
        with open(config_file_path, "r") as f:
            xml_content = f.read()

        root = DET.fromstring(xml_content)

        def modify_config(config_element):
            if config_element is None:
                return

            if "cleartextTrafficPermitted" in config_element.attrib:
                if config_element.attrib["cleartextTrafficPermitted"] == "false":
                    config_element.set("cleartextTrafficPermitted", "true")
            else:
                config_element.set("cleartextTrafficPermitted", "true")

            trust_anchors = config_element.find("trust-anchors")
            if trust_anchors is None:
                trust_anchors = ET.SubElement(config_element, "trust-anchors")
                ET.SubElement(trust_anchors, "certificates", {"src": "system"})
                ET.SubElement(
                    trust_anchors,
                    "certificates",
                    {"src": "user", "overridePins": "true"},
                )
            else:
                for child in trust_anchors.findall("certificates"):
                    if child.get("src") == "user":
                        trust_anchors.remove(child)

                ET.SubElement(
                    trust_anchors,
                    "certificates",
                    {"src": "user", "overridePins": "true"},
                )

        base_config = root.find("base-config")
        if base_config is None:
            with open(config_file_path, "w") as f:
                f.write(XML_CONTENT)
            return
        modify_config(base_config)

        debug_overrides = root.find("debug-overrides")
        if debug_overrides:
            modify_config(debug_overrides)

            base_conf = debug_overrides.find("base-config")
            if base_conf is not None:
                debug_overrides.remove(base_conf)

        xml_str = ET.tostring(root, encoding="utf-8").decode()
        with open(config_file_path, "w") as f:
            f.write(xml_str)


def modify_manifest(manifest_path: str) -> None:
    import xml.etree.ElementTree as ET  # skipcq

    import defusedxml.ElementTree as DET

    ET.register_namespace("android", "http://schemas.android.com/apk/res/android")

    with open(manifest_path, "r") as f:
        file_contents = f.read()

    manifest_start = file_contents.index("<manifest")
    before_manifest = file_contents[:manifest_start]

    root = DET.fromstring(file_contents[manifest_start:])

    application = root.find("application")
    nsc = "@xml/network_security_config"
    application.set("android:networkSecurityConfig", nsc)

    application.set("android:usesCleartextTraffic", "true")

    xml_str = ET.tostring(root, encoding="utf-8").decode()
    output = before_manifest + xml_str

    with open(manifest_path, "w") as f:
        f.write(output)


def modify_apk(temp_dir: str, okhttp: bool) -> None:
    lib_dirs = [
        f"{temp_dir}/out/root/lib/armeabi-v7a",
        f"{temp_dir}/out/root/lib/arm64-v8a",
        f"{temp_dir}/out/root/lib/x86_64",
    ]
    try:
        if okhttp:
            apply_regex(
                f"{temp_dir}/out/smali", OKHTTP3_SEARCH_REGEX, OKHTTP3_REPLACE_REGEX
            )
            apply_regex(
                f"{temp_dir}/out/smali", JAVAX_SEARCH_REGEX, JAVAX_REPLACE_REGEX
            )
        modify_manifest(f"{temp_dir}/out/AndroidManifest.xml")
        modify_public_xml(f"{temp_dir}/out/resources/package_1/res/values/public.xml")
        xml_path = f"{temp_dir}/out/resources/package_1/res/xml"
        os.makedirs(xml_path, exist_ok=True)
        modify_xml(xml_path)
        for lib_dir in lib_dirs:
            if os.path.exists(lib_dir):
                for file in os.listdir(lib_dir):
                    if file == "libflutter.so":
                        print(
                            f"{GREEN}[TIP]{NC}{YELLOW}This application seems to be a Flutter app.{NC}"
                        )
                        print(
                            f"{YELLOW}You might need to patch the Flutter engine.{NC}"
                        )
                        print(
                            f"{YELLOW}Feel free to use the flutter patch script if required.{NC}"
                        )

    except Exception as e:
        raise RuntimeError(f"Error modifying APK: {str(e)}")


def patch_apk(apk_path: str, okhttp: bool) -> None:
    file_name = os.path.basename(apk_path) + "_ssl_patched.apk"
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"{GREEN}Decompiling APK...{NC}")
        decompile_apk(temp_dir, apk_path, okhttp)
        if not os.path.exists(f"{temp_dir}/out"):
            print(f"{RED}ERROR: {NC}Failed to decompile APK.")
            exit(1)
        print(f"{GREEN}Modifying APK...{NC}")
        modify_apk(temp_dir, okhttp)

        print(f"{GREEN}Recompiling APK...{NC}")
        recompile_apk(temp_dir, file_name)
        if os.path.exists(file_name):
            print(f"{GREEN}APK patched successfully!{NC}")
            print(f"{GREEN}Patched APK saved as {file_name}{NC}")
        else:
            print(f"{RED}ERROR: {NC}Failed to recompile APK.")
            exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Patch APK to bypass SSL verification."
    )
    parser.add_argument("apk_path", help="Path to the APK/APKS file")
    parser.add_argument(
        "--okhttp", help="Patch OkHttp3", action="store_true", required=False
    )
    args = parser.parse_args()
    apk_path = args.apk_path
    okhttp = args.okhttp

    if not os.path.exists(APKEDITOR_PATH):
        print(
            f"{RED}Hey, You forgot to edit the {YELLOW}APKEDITOR_PATH{NC} variable!{NC}"
        )
        exit(1)

    if apk_path.endswith(".apks"):
        try:
            with ZipFile(apk_path, "r") as zip_ref:
                zip_ref.testzip()
            print("Split APK file detected. Merging...")
            apk_path = merge_apks(apk_path)
            if apk_path:
                print(f"Merged APK saved as {apk_path}")
            else:
                print(f"{RED}ERROR: {NC}Failed to merge APKS file.")
                exit(1)
        except BadZipFile:
            print(f"{RED}ERROR: {NC}Invalid APKS file: {apk_path}")
            exit(1)
    patch_apk(apk_path, okhttp)
