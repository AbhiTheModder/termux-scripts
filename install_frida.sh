#!/data/data/com.termux/files/usr/bin/sh

if ! command -v termux-setup-storage; then
  echo "This script can be executed only on Termux"
  exit 1
fi

clear

echo -e "\033[0mTermux has \033[1;32mresumed support for official Frida builds\033[0m via its package manager as of late July 2025!"
echo ""

echo -e "\033[0;32mInstall with:\033[0m"
echo -e "  \033[1;33mpkg install -y frida-tools\033[0m"
echo ""

echo -e "\033[0;35mNote:\033[0m The package manager version might be slightly behind the latest official release."

echo -e "\033[1;36mIf you want the absolute latest version, or a specific one, you can continue with this script.\033[0m"
echo ""

echo -e "\033[1;32mDo you want to proceed with this script?\033[0m"
echo -e "\033[1;37m(Type 'y' to continue, or any other key to exit)\033[0m"
read -r CONT

if [ "$CONT" != "y" ] && [ "$CONT" != "Y" ]; then
  clear
  echo -e "\033[1;31mAborted.\033[0m Run \033[1;33mpkg install -y frida-tools\033[0m or rerun this script anytime."
  exit 0
fi

clear

termux-setup-storage

cd $HOME

pkg update
pkg upgrade -y

pkg i -y python git

pip install setuptools

if [ -z "$1" ]; then
  FRIDA_VERSION=$(curl --silent "https://api.github.com/repos/frida/frida/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
else
  FRIDA_VERSION="$1"
  RELEASE=$(curl --silent "https://api.github.com/repos/frida/frida/releases/tags/$FRIDA_VERSION")
  if echo "$RELEASE" | grep -q '"message": "Not Found"'; then
    echo -e "\033[0;31m$FRIDA_VERSION isn't a released frida version. Either provide a correct version or run this script without any arguments to install latest version.\033[0m"
    exit 1
  fi
fi
# FRIDA_VERSION=17.0.7

DARCH=$(uname -m)

if [ "$DARCH" == "aarch64" ]; then
  DARCH="arm64"
elif [[ $DARCH == *"arm"* ]]; then
  DARCH="arm"
fi

DEVKIT_URL="https://github.com/frida/frida/releases/download/$FRIDA_VERSION/frida-core-devkit-$FRIDA_VERSION-android-$DARCH.tar.xz"

version() {
  echo "$1" | awk -F. '{ printf("%d%03d%03d", $1,$2,$3); }'
}

curl -L -o frida-core-devkit-android-$DARCH.tar.xz "$DEVKIT_URL"

if [ -d "$HOME/devkit" ]; then
  rm -rf "$HOME/devkit"
fi

mkdir -p "$HOME/devkit"

tar -xvf frida-core-devkit-android-$DARCH.tar.xz -C $HOME/devkit

if [ -f "frida-core-devkit-android-$DARCH.tar.xz" ]; then
  rm -f frida-core-devkit-android-$DARCH.tar.xz
fi

if [ "$(version "$FRIDA_VERSION")" -le "$(version "17.0.7")" ]; then
  if [ "$(version "$FRIDA_VERSION")" -lt "$(version "17.0.0")" ]; then
    TOOLS_VERSION="<=13.7.1"
  else
    TOOLS_VERSION="<=14.0.2"
  fi
  git clone https://github.com/AbhiTheModder/frida-python frida-python-android -b 17.0.7
else
  TOOLS_VERSION=">14.0.2"
  git clone https://github.com/AbhiTheModder/frida-python frida-python-android
fi

cd frida-python-android

FRIDA_VERSION="$FRIDA_VERSION" FRIDA_CORE_DEVKIT="$HOME/devkit" pip install --force-reinstall .

if [ -d "$HOME/frida-python-android" ]; then
  rm -rf "$HOME/frida-python-android"
  cd $HOME
fi

if [ -z "$2" ]; then
  pip install --upgrade frida-tools"$TOOLS_VERSION"
else
  pip install --upgrade frida-tools=="$2"
fi
