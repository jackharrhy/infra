#!/usr/bin/env python3
"""Build launcher artifacts from the checked-in, pinned packwiz metadata."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT.parent / "downloads"
PACK_URL = "https://cheesetown.rocks/pack.toml"
BOOTSTRAP_URL = "https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/packwiz-installer-bootstrap.jar"
BOOTSTRAP_SHA256 = "a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c"
ZIP_NAME = "cheesepack-v1.zip"
MRPACK_NAME = "cheesepack-v1.mrpack"
PRELAUNCH = f'"$INST_JAVA" -jar packwiz-installer-bootstrap.jar -g -s client {PACK_URL}'
COMPONENTS = {
    "formatVersion": 1,
    "components": [
        {"uid": "net.minecraft", "version": "26.2", "important": True},
        {"uid": "net.fabricmc.fabric-loader", "version": "0.19.5", "important": True},
    ],
}
INSTANCE = "\n".join([
    "[General]", "ConfigVersion=1.2", "InstanceType=OneSix",
    "name=Cheesepack v1", "iconKey=cheesepack",
    # Qt INI syntax requires escaping the command's literal quotes.
    "OverrideCommands=true", f"PreLaunchCommand={json.dumps(PRELAUNCH)}",
    "PostExitCommand=", "WrapperCommand=",
    "notes=Minecraft 26.2 / Fabric 0.19.5. Requires Java 25. HTTPS pack updates before each launch.", "",
])


def main():
    DOWNLOADS.mkdir(exist_ok=True)
    packwiz = os.environ.get("PACKWIZ", "/tmp/minecraft-tools/packwiz")
    cli = [packwiz, "--cache", str(DOWNLOADS / ".cache")]
    subprocess.run(cli + ["refresh"], cwd=ROOT, check=True)
    subprocess.run(cli + ["modrinth", "export", "-o", str(DOWNLOADS / MRPACK_NAME)], cwd=ROOT, check=True)
    with zipfile.ZipFile(DOWNLOADS / MRPACK_NAME, "a", zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT.parent / "assets/pack-icon.png", "icon.png")
    bootstrap = urllib.request.urlopen(BOOTSTRAP_URL, timeout=60).read()
    if hashlib.sha256(bootstrap).hexdigest() != BOOTSTRAP_SHA256:
        raise ValueError("Bootstrap does not match the reviewed upstream v0.0.3 binary")
    (DOWNLOADS / "packwiz-installer-bootstrap.jar").write_bytes(bootstrap)
    with zipfile.ZipFile(DOWNLOADS / ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("cheesepack/instance.cfg", INSTANCE)
        archive.writestr("cheesepack/mmc-pack.json", json.dumps(COMPONENTS, indent=2) + "\n")
        archive.writestr("cheesepack/.minecraft/packwiz-installer-bootstrap.jar", bootstrap)
        archive.write(ROOT.parent / "assets/pack-icon.png", "cheesepack/cheesepack.png")
    shutil.copyfile(DOWNLOADS / ZIP_NAME, DOWNLOADS / "Cheesepack v1.zip")
    (DOWNLOADS / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256((DOWNLOADS / name).read_bytes()).hexdigest()}  {name}\n"
        for name in [ZIP_NAME, "Cheesepack v1.zip", MRPACK_NAME, "packwiz-installer-bootstrap.jar"]
    ))


if __name__ == "__main__":
    main()
