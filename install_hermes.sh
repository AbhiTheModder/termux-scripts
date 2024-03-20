if ! command -v termux-setup-storage; then
  echo "This script can be executed only on Termux"
  exit 1
fi

termux-setup-storage

cd $HOME

pkg update
pkg upgrade -y
pkg i -y ncurses-utils

green="$(tput setaf 2)"
nocolor="$(tput sgr0)"
red="$(tput setaf 1)"
blue="$(tput setaf 32)"
yellow="$(tput setaf 3)"
note="$(tput setaf 6)"

echo "${green}━━━ Basic Requirements Setup ━━━${nocolor}"
pkg i -y cmake git ninja libicu python zip readline

if [ -d "hermes" ]; then
    rm -rf hermes
fi

echo "${note}Below are the list of hbcversions, please provide target version which you want to install${nocolor}"
echo "${green}hbc84 
hbc85 
hbc89 
hbc90 
hbc94 
hbc95 
hbc96 
latest ${nocolor}"
read -r -p "hbcversion > " hbcversion

if [[ $hbcversion = "" ]]; then
  echo "${red}Target hbcversion not provided exiting :0"
  exit 1
elif [[ $hbcversion = "hbc96" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b rn/0.73-stable 
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "hbc95" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b update-publish-tag-label
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "hbc94" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b rn/0.72-stable 
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "hbc90" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b rn/0.71-stable
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "hbc89" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b rn/0.70-stable
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "hbc85" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b rn/0.69-stable
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "hbc84" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes -b release-v0.10
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
elif [[ $hbcversion = "latest" ]]; then
  echo "${green}━━━ Starting hermes for $hbcversion installation ━━━${nocolor}"
  git clone https://github.com/facebook/hermes
  cmake -S hermes -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build ./build_release
else
  echo "${red}Wrong Target hbcversion provided${nocolor}${note}or it isn't supported right now${nocolor}${red}exiting :0"
  exit 1
fi


echo "${yellow}hermes $version Successfully Installed!${nocolor}"
