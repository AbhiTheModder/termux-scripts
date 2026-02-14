#!/data/data/com.termux/files/usr/bin/bash

if ! command -v termux-setup-storage; then
  echo "This script can be executed only on Termux"
  exit 1
fi

set -e

cd "$HOME"

MARIANA_TRENCH_DIRECTORY="$(pwd)/mariana-trench"
MT_INSTALL_DIRECTORY="$MARIANA_TRENCH_DIRECTORY/install"
DEF_HEURISTICS_PATH="$PREFIX/share/mariana-trench/configuration/heuristics.json"

pkg up -y

pkg install -y git zlib boost googletest jsoncpp openjdk-17 jsoncpp-static boost-headers binutils build-essential rsync

git clone https://github.com/D-os/libbinder.git --depth 1 && rm -rf libbinder/.git/

git clone https://github.com/facebook/mariana-trench.git --depth 1

mkdir -p "$MT_INSTALL_DIRECTORY" && mkdir -p "$MARIANA_TRENCH_DIRECTORY/dependencies"

cd "$MARIANA_TRENCH_DIRECTORY/dependencies"
git clone -b 9.1.0 https://github.com/fmtlib/fmt.git --depth 1
mkdir fmt/build
cd fmt/build
cmake -DCMAKE_CXX_STANDARD=17 -DFMT_TEST=OFF -DCMAKE_INSTALL_PREFIX="$MT_INSTALL_DIRECTORY" ..
make -j4
make install

cd "$HOME"

git clone https://github.com/google/benchmark.git --depth 1
cd benchmark
cmake -E make_directory "build"
cmake -DBENCHMARK_DOWNLOAD_DEPENDENCIES=on -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${PREFIX}" -DBENCHMARK_ENABLE_GTEST_TESTS=OFF -S . -B "build"
cmake --build "build" --config Release --target install

cd "$HOME"

git clone https://github.com/google/re2.git --depth 1
cd re2/
rm -rf build
cmake -DRE2_TEST=ON -DRE2_BENCHMARK=ON -DCMAKE_INSTALL_PREFIX="${PREFIX}" -S . -B build
cd build
make
make install

cd "$MARIANA_TRENCH_DIRECTORY/dependencies"
git clone https://github.com/facebook/redex.git --depth 1
mkdir redex/build
cd redex/build
cmake -DCMAKE_INSTALL_PREFIX="$MT_INSTALL_DIRECTORY" -DCMAKE_CXX_FLAGS="-I$HOME/libbinder/include" ..
make -j4
make install

cd "$MARIANA_TRENCH_DIRECTORY"
mkdir build
cd build
cmake \
 -DREDEX_ROOT="$MT_INSTALL_DIRECTORY" \
 -Dfmt_ROOT="$MT_INSTALL_DIRECTORY" \
 -DCMAKE_INSTALL_PREFIX="$MT_INSTALL_DIRECTORY" \
 ..
make -j4
make install

cd "$MARIANA_TRENCH_DIRECTORY"
python scripts/setup.py \
 --binary "$MT_INSTALL_DIRECTORY/bin/mariana-trench-binary" \
 --pyredex "$MT_INSTALL_DIRECTORY/bin/pyredex" \
 install


rm -rf "$HOME/libbinder/"

if [ ! -f "$DEF_HEURISTICS_PATH" ]; then
 echo "{}" > "$DEF_HEURISTICS_PATH"
fi

printf "[I] All Done!\n"
