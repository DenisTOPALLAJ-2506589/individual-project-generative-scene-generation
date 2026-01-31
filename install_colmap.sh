#!/bin/bash

# Quick COLMAP Installation using Ubuntu packages
# This is much faster than building from source
# Run this inside the LichtFeld-Studio Docker container

set -e

echo "=========================================="
echo "Installing COLMAP (Ubuntu Package)"
echo "=========================================="
echo ""

# Update package lists
echo "[→] Updating package lists..."
sudo apt update

# Install COLMAP from Ubuntu repositories
echo ""
echo "[→] Installing COLMAP and dependencies..."
sudo apt install -y colmap

# Install bc (basic calculator)
sudo apt install -y bc

# Install ffmpeg
sudo apt install -y ffmpeg

echo "[✓] COLMAP installed"

# Verify installation
echo ""
echo "[→] Verifying COLMAP installation..."
if command -v colmap &>/dev/null; then
	COLMAP_VERSION=$(colmap -h 2>&1 | grep -i "COLMAP" | head -n 1)
	echo "[✓] COLMAP installed successfully!"
	echo "    Version: $COLMAP_VERSION"
else
	echo "[✗] COLMAP installation failed"
	exit 1
fi

echo ""
echo "=========================================="
echo "COLMAP Installation Complete!"
echo "=========================================="
echo ""
echo "COLMAP is ready to use. Common commands:"
echo "  colmap -h                     # Show help"
echo "Note: This uses the Ubuntu package version."
echo ""
