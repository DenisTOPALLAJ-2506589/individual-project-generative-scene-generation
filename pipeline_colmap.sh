#!/bin/bash

# COLMAP Video to 3D Point Cloud Pipeline for Gaussian Splatting
# This script processes a video file and creates a COLMAP reconstruction
# suitable for 3D Gaussian Splatting projects like LichtFeld-Studio

set -e # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration with better defaults
VIDEO_FILE="${1:-output.mp4}"
PROJECT_DIR="${2:-colmap_project}"
FPS="${3:-30}"         # Extract 30 frames per second by default
MAX_FRAMES="${4:-300}" # Maximum number of frames to extract (prevents too many frames)

# Print functions
log() {
	echo -e "${GREEN}[INFO]${NC} $1"
}

error() {
	echo -e "${RED}[ERROR]${NC} $1"
	exit 1
}

warn() {
	echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
	echo -e "${BLUE}[INFO]${NC} $1"
}

# Display usage
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
	echo "Usage: $0 [VIDEO_FILE] [PROJECT_DIR] [FPS] [MAX_FRAMES]"
	echo ""
	echo "Arguments:"
	echo "  VIDEO_FILE   - Input video file (default: output.mp4)"
	echo "  PROJECT_DIR  - Output directory (default: colmap_project)"
	echo "  FPS         - Frames per second to extract (default: 30)"
	echo "  MAX_FRAMES  - Maximum frames to extract (default: 300)"
	echo ""
	echo "Examples:"
	echo "  $0 myvideo.mp4                    # Use defaults"
	echo "  $0 myvideo.mp4 my_project 15      # Extract 15 fps"
	echo "  $0 myvideo.mp4 my_project 30 500  # Extract 30 fps, max 500 frames"
	exit 0
fi

# Check if video file exists
[ ! -f "$VIDEO_FILE" ] && error "Video file '$VIDEO_FILE' not found!"

command -v ffmpeg >/dev/null 2>&1 || {
	echo "ffmpeg is not installed. Install with: sudo apt install ffmpeg" >&2
	./install_colmap.sh
}

command -v colmap >/dev/null 2>&1 || {
	echo "colmap is not installed. Install with: sudo apt install colmap" >&2
	./install_colmap.sh
}

# Get video information
log "Analyzing video file..."
VIDEO_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE")
VIDEO_FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE" | bc -l 2>/dev/null || echo "30")
TOTAL_FRAMES=$(echo "$VIDEO_DURATION * $VIDEO_FPS" | bc -l 2>/dev/null | cut -d. -f1 || echo "1000")

info "Video duration: ${VIDEO_DURATION}s"
info "Video native FPS: $(printf "%.2f" $VIDEO_FPS 2>/dev/null || echo $VIDEO_FPS)"
info "Total frames in video: $TOTAL_FRAMES"

# Calculate expected frames
EXPECTED_FRAMES=$(echo "$VIDEO_DURATION * $FPS" | bc -l 2>/dev/null | cut -d. -f1 || echo "$MAX_FRAMES")
if [ "$EXPECTED_FRAMES" -gt "$MAX_FRAMES" ]; then
	warn "Expected frames ($EXPECTED_FRAMES) exceeds MAX_FRAMES ($MAX_FRAMES)"
	ADJUSTED_FPS=$(echo "scale=2; $MAX_FRAMES / $VIDEO_DURATION" | bc 2>/dev/null || echo "$FPS")
	warn "Adjusting FPS to $ADJUSTED_FPS to stay under limit"
	FPS=$ADJUSTED_FPS
	EXPECTED_FRAMES=$MAX_FRAMES
fi

info "Will extract approximately $EXPECTED_FRAMES frames at $FPS fps"

# Check GPU availability for matching (not extraction)
if nvidia-smi >/dev/null 2>&1; then
	log "GPU detected - will use GPU for feature matching"
	USE_GPU=1
else
	warn "No GPU detected - falling back to CPU (this will be slower)"
	USE_GPU=0
fi

log "Starting COLMAP pipeline for video: $VIDEO_FILE"
log "Project directory: $PROJECT_DIR"

# Create project structure
log "Creating project directory structure..."
rm -rf "$PROJECT_DIR" # Clean up if exists
mkdir -p "$PROJECT_DIR"/{images,database,sparse,dense}

# Extract frames from video with better quality
log "Extracting frames from video..."
# Use select filter to limit frames and maintain quality
if [ "$EXPECTED_FRAMES" -le "$MAX_FRAMES" ]; then
	ffmpeg -i "$VIDEO_FILE" -vf "fps=$FPS,scale=iw:ih" -q:v 2 "$PROJECT_DIR/images/frame_%05d.jpg" -y 2>&1 | grep -v "frame=" || true
else
	# Use select to pick evenly spaced frames
	SELECT_EXPR="not(mod(n,$((TOTAL_FRAMES / MAX_FRAMES))))"
	ffmpeg -i "$VIDEO_FILE" -vf "select='$SELECT_EXPR',scale=iw:ih" -vsync 0 -q:v 2 "$PROJECT_DIR/images/frame_%05d.jpg" -y 2>&1 | grep -v "frame=" || true
fi

FRAME_COUNT=$(ls "$PROJECT_DIR/images"/*.jpg 2>/dev/null | wc -l)
[ "$FRAME_COUNT" -eq 0 ] && error "No frames extracted from video!"
log "Successfully extracted $FRAME_COUNT frames"

# Check if we have enough frames for reconstruction
if [ "$FRAME_COUNT" -lt 10 ]; then
	error "Not enough frames ($FRAME_COUNT). Need at least 10 frames. Try increasing FPS parameter."
fi

# Feature extraction
log "Extracting features using CPU (this may take a while)..."
warn "Using CPU for feature extraction to avoid GPU/OpenGL issues in Docker"

export QT_QPA_PLATFORM=offscreen

colmap feature_extractor \
	--database_path "$PROJECT_DIR/database/database.db" \
	--image_path "$PROJECT_DIR/images" \
	--ImageReader.single_camera 1 \
	--ImageReader.camera_model PINHOLE \
	--SiftExtraction.use_gpu 0 # FIX: was missing; forces CPU extraction

log "Feature extraction complete"

# Sequential matching (replaces exhaustive_matcher)
# sequential_matcher is O(n·k) instead of O(n²) — correct for video input.
log "Matching features sequentially..."

GPU_FLAG=0
[ "$USE_GPU" -eq 1 ] && GPU_FLAG=1

colmap sequential_matcher \
	--database_path "$PROJECT_DIR/database/database.db" \
	--SequentialMatching.overlap 25 \
	--SequentialMatching.quadratic_overlap 1 \
	--SequentialMatching.loop_detection 0 \
	--SiftMatching.use_gpu "$GPU_FLAG"

log "Feature matching complete"

# Sparse reconstruction
log "Building sparse reconstruction..."
colmap mapper \
	--database_path "$PROJECT_DIR/database/database.db" \
	--image_path "$PROJECT_DIR/images" \
	--output_path "$PROJECT_DIR/sparse" \
	--Mapper.ba_refine_focal_length 1 \
	--Mapper.ba_refine_extra_params 1

# Check if reconstruction succeeded
if [ ! -d "$PROJECT_DIR/sparse/0" ]; then
	error "Sparse reconstruction failed! Check if your video has enough distinct features and camera motion."
fi

# Count registered images
REGISTERED_IMAGES=$(colmap model_analyzer \
	--path "$PROJECT_DIR/sparse/0" 2>&1 | grep "Registered images" | awk '{print $3}' || echo "0")

log "Sparse reconstruction complete - registered $REGISTERED_IMAGES/$FRAME_COUNT images"

if [ "$REGISTERED_IMAGES" -lt 3 ]; then
	error "Too few images registered ($REGISTERED_IMAGES). The video might not have enough motion or features."
fi

# Export to txt format (needed for Gaussian Splatting)
log "Exporting sparse model to text format..."
colmap model_converter \
	--input_path "$PROJECT_DIR/sparse/0" \
	--output_path "$PROJECT_DIR/sparse/0" \
	--output_type TXT

# Image undistortion
log "Undistorting images..."
colmap image_undistorter \
	--image_path "$PROJECT_DIR/images" \
	--input_path "$PROJECT_DIR/sparse/0" \
	--output_path "$PROJECT_DIR/dense" \
	--output_type COLMAP

: <<'SKIP_DENSE'
# Dense reconstruction (optional - can be skipped for Gaussian Splatting)
read -p "$(echo -e ${YELLOW}Perform dense reconstruction? This can take a long time. [y/N]:${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
	log "Starting dense reconstruction..."

	if [ "$USE_GPU" -eq 1 ]; then
		colmap patch_match_stereo \
			--workspace_path "$PROJECT_DIR/dense" \
			--workspace_format COLMAP \
			--PatchMatchStereo.geom_consistency true \
			--PatchMatchStereo.gpu_index 0
	else
		export COLMAP_NO_GPU=1
		colmap patch_match_stereo \
			--workspace_path "$PROJECT_DIR/dense" \
			--workspace_format COLMAP \
			--PatchMatchStereo.geom_consistency true
	fi

	# Stereo fusion
	log "Fusing stereo depth maps..."
	colmap stereo_fusion \
		--workspace_path "$PROJECT_DIR/dense" \
		--workspace_format COLMAP \
		--input_type geometric \
		--output_path "$PROJECT_DIR/dense/fused.ply"

	DENSE_STATUS="✓ Created: $PROJECT_DIR/dense/fused.ply"
else
	log "Skipping dense reconstruction"
	DENSE_STATUS="✗ Skipped"
fi
SKIP_DENSE

log "================================"
log "PIPELINE COMPLETE!"
log "================================"
log "Project location: $PROJECT_DIR"
log ""
log "Output files:"
log "  ✓ Sparse reconstruction: $PROJECT_DIR/sparse/0"
log "  ✓ Camera parameters: $PROJECT_DIR/sparse/0/cameras.txt"
log "  ✓ Image poses: $PROJECT_DIR/sparse/0/images.txt"
log "  ✓ 3D points: $PROJECT_DIR/sparse/0/points3D.txt"
log "  ✓ Undistorted images: $PROJECT_DIR/dense/images"
log "  $DENSE_STATUS"
log ""
log "Statistics:"
log "  Input frames: $FRAME_COUNT"
log "  Registered images: $REGISTERED_IMAGES ($(echo "scale=1; $REGISTERED_IMAGES*100/$FRAME_COUNT" | bc 2>/dev/null || echo "N/A")%)"
log "  Reconstruction: $([ -f "$PROJECT_DIR/sparse/0/cameras.bin" ] && echo "SUCCESS ✓" || echo "FAILED ✗")"
log ""
log "For LichtFeld-Studio / Gaussian Splatting, use:"
log "  ./build/LichtFeld-Studio -d $PROJECT_DIR/ -o output/$PROJECT_DIR/ --gut"
log ""
log "Note: Feature extraction used CPU mode to avoid OpenGL issues in Docker."
log "      This is slower but more reliable in containerized environments."
