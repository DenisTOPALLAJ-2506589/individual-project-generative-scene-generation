FROM nvidia/cuda:12.8.0-devel-ubuntu24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV VCPKG_ROOT=/opt/vcpkg
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${VCPKG_ROOT}:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"

# Install system dependencies including COLMAP requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	ca-certificates \
	gnupg2 \
	lsb-release \
	locales \
	x11-apps \
	zenity \
	openssh-client \
	pkg-config \
	xorg-dev \
	curl \
	zip \
	unzip \
	tar \
	cmake \
	build-essential \
	pkg-config \
	ninja-build \
	wget \
	python3 \
	python3-pip \
	libgl1-mesa-dev \
	libglu1-mesa-dev \
	libx11-dev \
	libxrandr-dev \
	libxi-dev \
	libxinerama-dev \
	libxcursor-dev \
	sudo \
	libboost-all-dev \
	libeigen3-dev \
	libflann-dev \
	libfreeimage-dev \
	libmetis-dev \
	libgoogle-glog-dev \
	libgflags-dev \
	libsqlite3-dev \
	libglew-dev \
	qtbase5-dev \
	libqt5opengl5-dev \
	libcgal-dev \
	libceres-dev \
	ffmpeg \
	bc \
	vim \
	nano \
	software-properties-common && \
	add-apt-repository ppa:ubuntu-toolchain-r/test && \
	apt-get update && \
	apt-get install -y \
	gcc-14 \
	g++-14 \
	gfortran-14 && \
	update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 60 && \
	update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 60 && \
	update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-14 60 && \
	update-alternatives --set gcc /usr/bin/gcc-14 && \
	update-alternatives --set g++ /usr/bin/g++-14 && \
	update-alternatives --set gfortran /usr/bin/gfortran-14 && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# Install CMake 3.30 or higher
RUN wget https://github.com/Kitware/CMake/releases/download/v3.30.5/cmake-3.30.5-linux-x86_64.sh -O /tmp/cmake-install.sh && \
	chmod +x /tmp/cmake-install.sh && \
	/tmp/cmake-install.sh --skip-license --prefix=/usr/local && \
	rm /tmp/cmake-install.sh && \
	cmake --version

# Clone the LichtFeld Studio project
WORKDIR /app
RUN git clone https://github.com/MrNeRF/LichtFeld-Studio.git

WORKDIR /app/LichtFeld-Studio

# Install and setup vcpkg
RUN git clone https://github.com/Microsoft/vcpkg.git /opt/vcpkg && \
	/opt/vcpkg/bootstrap-vcpkg.sh && \
	ln -s /opt/vcpkg/vcpkg /usr/local/bin/vcpkg

# Set vcpkg environment variables
ENV PATH="${VCPKG_ROOT}:${PATH}"

# Copy scripts directory
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# Copy install_colmap.sh to LichtFeld-Studio directory for compatibility
RUN if [ -f /app/scripts/install_colmap.sh ]; then \
	cp /app/scripts/install_colmap.sh /app/LichtFeld-Studio/ && \
	chmod +x /app/LichtFeld-Studio/install_colmap.sh; \
	fi

# Run install_colmap.sh (create a wrapper to handle sudo)
RUN if [ -f /app/LichtFeld-Studio/install_colmap.sh ]; then \
	sed -i 's/sudo //g' /app/LichtFeld-Studio/install_colmap.sh && \
	/app/LichtFeld-Studio/install_colmap.sh || true; \
	fi

# Verify COLMAP installation
RUN which colmap || echo "COLMAP not found"

# Install PyTorch C++ (libtorch) for CUDA 12.8
RUN cd /opt && \
	wget https://download.pytorch.org/libtorch/cu124/libtorch-cxx11-abi-shared-with-deps-2.5.1%2Bcu124.zip && \
	unzip libtorch-cxx11-abi-shared-with-deps-2.5.1+cu124.zip && \
	rm libtorch-cxx11-abi-shared-with-deps-2.5.1+cu124.zip

# Set Torch environment variables
ENV Torch_DIR=/opt/libtorch/share/cmake/Torch
ENV LD_LIBRARY_PATH=/opt/libtorch/lib:${LD_LIBRARY_PATH}
ENV CUDA_LAUNCH_BLOCKING=1
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV CUDA_PATH=/usr/local/cuda-12.8
ENV TORCH_USE_CUDA_DSA=1

# Build LichtFeld-Studio with limited parallel jobs to avoid memory issues
RUN mkdir -p build && \
	cd build && \
	cmake .. \
	-DCMAKE_TOOLCHAIN_FILE=${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake \
	-DCMAKE_PREFIX_PATH=/opt/libtorch \
	-DCMAKE_BUILD_TYPE=Release && \
	cmake --build . --config Release -j$(nproc)
# Create necessary directories
RUN mkdir -p /data /app/colmap_project

# Set working directory back to app root
WORKDIR /app

# Expose port for API
EXPOSE 8000

