// ported from https://github.com/AbhiTheModder/termux-scripts/blob/main/flutter_ssl_patch.py
// Usage: r2 -i flutter_ssl_patch.r2.js libflutter.so

const RED = "\x1b[0;31m";
const GREEN = "\x1b[0;32m";
const YELLOW = "\x1b[0;33m";
const BLUE = "\x1b[0;34m";
const NC = "\x1b[0m";

const patterns = {
    "arm64": [
        "F. 0F 1C F8 F. 5. 01 A9 F. 5. 02 A9 F. .. 03 A9 .. .. .. .. 68 1A 40 F9",
        "F. 43 01 D1 FE 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 13 00 40 F9 F4 03 00 AA 68 1A 40 F9",
        "FF 43 01 D1 FE 67 01 A9 .. .. 06 94 .. 7. 06 94 68 1A 40 F9 15 15 41 F9 B5 00 00 B4 B6 4A 40 F9"
    ],
    "arm": [
        "2D E9 F. 4. D0 F8 00 80 81 46 D8 F8 18 00 D0 F8"
    ],
    "x86": [
        "55 41 57 41 56 41 55 41 54 53 50 49 89 fe 48 8b 1f 48 8b 43 30 4c 8b b8 d0 01 00 00 4d 85 ff 74 12 4d 8b a7 90 00 00 00 4d 85 e4 74 4a 49 8b 04 24 eb 46",
        "55 41 57 41 56 41 55 41 54 53 50 49 89 f. 4c 8b 37 49 8b 46 30 4c 8b a. .. 0. 00 00 4d 85 e. 74 1. 4d 8b",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FF 48 8B 1F 48 8B 43 30 4C 8B A0 28 02 00 00 4D 85 E4 74",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02 50 48 8B AF A. 00 00 00 48 85 ED 74 7. 48 83 7D 00 00 74"
    ]
};

function getArch() {
    try {
        let info = JSON.parse(r2.cmd("iaj"));
        let arch_value = info.bins[0].arch;
        let arch_bits = info.bins[0].bits;
        
        if (arch_value === "arm" && arch_bits === 64) {
            return "arm64";
        } else if (arch_value === "arm" && arch_bits === 16) {
            return "arm";
        } else if (arch_value === "x86" && arch_bits === 64) {
            return "x86";
        } else {
            console.log(RED + "Unsupported architecture: " + arch_value + NC);
            return null;
        }
    } catch (e) {
        try {
            let info = JSON.parse(r2.cmd("iAj"));
            let arch_value = info.bins[0].arch;
            let arch_bits = info.bins[0].bits;
            
            if (arch_value === "arm" && arch_bits === 64) {
                return "arm64";
            } else if (arch_value === "arm" && arch_bits === 16) {
                return "arm";
            } else if (arch_value === "x86" && arch_bits === 64) {
                return "x86";
            }
        } catch (e2) {
            console.log(RED + "Error detecting architecture" + NC);
            return null;
        }
    }
}

function findOffset(arch) {
    if (!patterns[arch]) {
        console.log(RED + "No patterns for architecture: " + arch + NC);
        return null;
    }
    
    for (let pattern of patterns[arch]) {
        let searchResult = r2.cmd("/x " + pattern);
        let lines = searchResult.split('\n');
        
        for (let line of lines) {
            if (line.trim() === "") continue;
            
            let offset = line.trim().split(' ')[0];
            if (offset && offset.startsWith("0x")) {
                console.log("ssl_verify_peer_cert found at: " + BLUE + offset + NC);
                
                let searchFcn = r2.cmd(offset + ";afl.").trim().split(' ')[0];
                
                if (!searchFcn && arch === "x86") {
                    searchFcn = offset;
                    r2.cmd("af @" + searchFcn);
                }
                
                if (searchFcn) {
                    console.log("function at: " + YELLOW + searchFcn + NC);
                    return searchFcn;
                }
            }
        }
    }
    
    return null;
}

function main() {
    console.log(YELLOW + "Analyzing function calls..." + NC);
    
    r2.cmd("e log.quiet=true");
    r2.cmd("oo+");
    r2.cmd("aac");
    
    console.log(YELLOW + "Searching for offset..." + NC);
    
    let arch = getArch();
    if (!arch) {
        return;
    }
    
    let offset = findOffset(arch);
    
    if (!offset) {
        console.log(RED + "ssl_verify_peer_cert not found." + NC);
    }
}

main();
