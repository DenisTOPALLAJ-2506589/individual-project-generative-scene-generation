#!/bin/bash
set -e # Exit on error

# Check if build directory exists and is complete
if [ ! -d "${HOME}/projects/LichtFeld-Studio/build" ] || [ ! -f "${HOME}/projects/LichtFeld-Studio/build/LichtFeld-Studio" ]; then
	echo "Build not found or incomplete, building now..."
	cd ${HOME}/projects/LichtFeld-Studio
	./build.sh 2>&1 | tee /tmp/build.log # Show output and save to log
	echo "Build completed!"
else
	echo "Build directory found, skipping build"
fi

exec "$@"
