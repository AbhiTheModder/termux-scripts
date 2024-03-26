#!/bin/bash

if ! command -v termux-setup-storage; then
  echo "This script can be executed only on Termux"
  exit 1
fi

termux-setup-storage

cd $HOME
pkg update
pkg upgrade -y
pkg i -y python keytool

mkdir -p ~/softs
cd ~/softs
wget https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar
wget https://bitbucket.org/JesusFreke/smali/downloads/baksmali-2.5.2.jar
wget https://github.com/mstrobel/procyon/releases/download/v0.6.0/procyon-decompiler-0.6.0.jar
wget https://github.com/pxb1988/dex2jar/releases/download/v2.4/dex-tools-v2.4.zip
unzip dex-tools-v2.4.zip 
rm -f dex-tools-v2.4.zip

cd $HOME

python3 -m venv venv-droidlysis
source ~/venv-droidlysis/bin/activate
pip3 install git+https://github.com/cryptax/droidlysis

if [ -d ".config" ]; then
  cp -r /data/user/0/com.termux/files/home/venv-droidlysis/lib/python3.11/site-packages/conf/* ~/.config/
  cd ~/.config
  wget https://gist.githubusercontent.com/AbhiTheModder/9701648aed08ac3997f06df77e7d1066/raw/94916ffe823b40eaa68efb2faaa96363143f9135/general.conf -O general.conf
else
  mkdir ~/.config
  cp -r /data/user/0/com.termux/files/home/venv-droidlysis/lib/python3.11/site-packages/conf/* ~/.config/
  cd ~/.config
  wget https://gist.githubusercontent.com/AbhiTheModder/9701648aed08ac3997f06df77e7d1066/raw/94916ffe823b40eaa68efb2faaa96363143f9135/general.conf -O general.conf
fi

new_path="export PATH=\$PATH:source ~/venv-droidlysis/bin/activate && python3 venv-droidlysis/bin/droidlysis3.py --config ~/.config/general.conf"

if grep -Fxq "$new_path" ~/.bashrc
then
    echo "Path already exists in .bashrc"
    exit 1
else
    
    onePresent=0
    
    if [ -f ~/.zshrc ]; then
        echo "$new_path" >> ~/.zshrc
        source ~/.zshrc
        echo "Path added to .zshrc"
        onePresent=1
    fi
    
    if [ -f ~/.bashrc ]; then
        echo "$new_path" >> ~/.bashrc
        source ~/.bashrc
        echo "Path added to .bashrc"
        onePresent=1
    fi
    
    if [ -f ~/.profile ]; then
        echo "$new_path" >> ~/.profile
        source ~/.profile
        echo "Path added to .profile"
        onePresent=1
    fi
    
    if [ -f $PREFIX/etc/bash.bashrc ]; then
        echo "$new_path" >> $PREFIX/etc/bash.bashrc
        source $PREFIX/etc/bash.bashrc
        echo "Path added to .profile"
        onePresent=1
    fi
    
    if [ $onePresent -eq 0 ]; then
        echo "No .bashrc, .zshrc or .profile found. Please add the following line to your shell config file:"
        echo "$new_path"
        exit 1
    fi
fi

echo "droidlysis installed successfully!"
echo "open a new terminal and run 'droidlysis' to get started."
