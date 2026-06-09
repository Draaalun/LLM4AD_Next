#!/bin/bash
# Build script for sorting benchmark

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BUILD_DIR="$SCRIPT_DIR/build"

# Create build directory if it doesn't exist
mkdir -p "$BUILD_DIR"

cd "$BUILD_DIR"

# Run CMake
cmake ..

# Build
make -j$(nproc)

echo "Build complete. Executable: $BUILD_DIR/sorting_benchmark"
