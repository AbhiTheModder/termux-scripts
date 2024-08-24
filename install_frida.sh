#!/data/data/com.termux/files/usr/bin/sh

if ! command -v termux-setup-storage; then
  echo "This script can be executed only on Termux"
  exit 1
fi

termux-setup-storage

cd $HOME

pkg update
pkg upgrade -y

pkg i -y python git

pip install setuptools

FRIDA_VERSION=$(curl --silent "https://api.github.com/repos/frida/frida/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

DEVKIT_URL="https://github.com/frida/frida/releases/download/$FRIDA_VERSION/frida-core-devkit-$FRIDA_VERSION-android-arm64.tar.xz"

curl -L -o frida-core-devkit-android-arm64.tar.xz "$DEVKIT_URL"

if [ -d "$HOME/devkit" ]; then
  rm -rf "$HOME/devkit"
fi

mkdir -p "$HOME/devkit"

tar -xvf frida-core-devkit-android-arm64.tar.xz -C $HOME/devkit

if [ -f "frida-core-devkit-android-arm64.tar.xz" ]; then
  rm -f frida-core-devkit-android-arm64.tar.xz
fi

git clone https://github.com/AbhiTheModder/frida-python-android

cd frida-python-android

FRIDA_VERSION="$FRIDA_VERSION" FRIDA_CORE_DEVKIT="$HOME/devkit" pip install --force-reinstall .

if [ -d "$HOME/frida-python-android" ]; then
  rm -rf "$HOME/frida-python-android"
  cd $HOME
fi

pip install --upgrade frida-tools
