#!/bin/bash
set -e

VCPKG_ROOT="${HOME}/vcpkg"
PROJECT_DIR="$(pwd)"
CLEAN=${1:-""}

# Install prerequisites
sudo apt update
sudo apt install -y ninja-build nasm autoconf autoconf-archive automake libtool

# Set compilers
export CC=/usr/bin/gcc-14
export CXX=/usr/bin/g++-14
export CUDAHOSTCXX=/usr/bin/g++-14
export CMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc

# Setup vcpkg
[ ! -d "$VCPKG_ROOT" ] && {
	git clone https://github.com/microsoft/vcpkg.git "$VCPKG_ROOT"
	cd "$VCPKG_ROOT" && ./bootstrap-vcpkg.sh --disableMetrics && cd -
}

export VCPKG_ROOT

# Clone/update project
[ ! -d "$PROJECT_DIR" ] && git clone --recursive https://github.com/MrNeRF/LichtFeld-Studio.git "$PROJECT_DIR" || {
	cd "$PROJECT_DIR" && git pull && git submodule update --recursive && cd -
}

cd "$PROJECT_DIR"

# Clean and build
[ "$CLEAN" = "clean" ] || [ "$CLEAN" = "--clean" ] && rm -rf build
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" -G Ninja
cmake --build build -- -j$(nproc)
