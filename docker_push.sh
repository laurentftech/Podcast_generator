#!/bin/bash

# This script automates the process of building and pushing two versions of a Docker image
# to Docker Hub: a full version ('latest') and a lightweight version ('light').
# Each version is tagged with a specific version, a major version, and a fixed tag.
#
# Usage:
#   1. Make the script executable: chmod +x docker_push.sh
#   2. Run the script with a version number: ./docker_push.sh <version>
#
# Example:
#   ./docker_push.sh 2.0.0b8

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Your Docker Hub username
USERNAME="gandulf78"
# The name of the image
IMAGE_NAME="podcast_generator"

# --- Script Logic ---

# Check if a version tag was provided as an argument
if [ -z "$1" ]; then
  echo "Error: No version tag provided." >&2
  echo "Usage: ./docker_push.sh <version>" >&2
  echo "Example: ./docker_push.sh 2.0.0b8" >&2
  exit 1
fi

VERSION=$1
# Extract the major version number (e.g., "2" from "2.0.0b8")
MAJOR_VERSION=$(echo "$VERSION" | cut -d. -f1)

# --- Full Version (with WhisperX) ---
TAG_SPECIFIC_FULL="$USERNAME/$IMAGE_NAME:$VERSION"
TAG_MAJOR_FULL="$USERNAME/$IMAGE_NAME:$MAJOR_VERSION"
TAG_LATEST_FULL="$USERNAME/$IMAGE_NAME:latest"

echo "--- Building and tagging FULL Docker image (with WhisperX) ---"
echo "  > Specific tag: $TAG_SPECIFIC_FULL"
echo "  > Major tag:    $TAG_MAJOR_FULL"
echo "  > Latest tag:   $TAG_LATEST_FULL"

# 1. Build the full image using the 'with_whisperx' target
docker build --target with_whisperx -t "$TAG_SPECIFIC_FULL" .

# 2. Add the other tags to the same image
docker tag "$TAG_SPECIFIC_FULL" "$TAG_MAJOR_FULL"
docker tag "$TAG_SPECIFIC_FULL" "$TAG_LATEST_FULL"

echo "--- Pushing all FULL tags to Docker Hub ---"
# 3. Push all full tags to Docker Hub
docker push "$TAG_SPECIFIC_FULL"
docker push "$TAG_MAJOR_FULL"
docker push "$TAG_LATEST_FULL"

echo "✅ Successfully pushed all FULL tags to Docker Hub!"

# --- Light Version (without WhisperX) ---
TAG_SPECIFIC_LIGHT="$USERNAME/$IMAGE_NAME:${VERSION}-light"
TAG_MAJOR_LIGHT="$USERNAME/$IMAGE_NAME:${MAJOR_VERSION}-light"
TAG_FIXED_LIGHT="$USERNAME/$IMAGE_NAME:light"

echo ""
echo "--- Building and tagging LIGHT Docker image (without WhisperX) ---"
echo "  > Specific tag: $TAG_SPECIFIC_LIGHT"
echo "  > Major tag:    $TAG_MAJOR_LIGHT"
echo "  > Fixed tag:    $TAG_FIXED_LIGHT"

# 1. Build the light image using the 'without_whisperx' target
docker build --target without_whisperx -t "$TAG_SPECIFIC_LIGHT" .

# 2. Add the other tags to the same image
docker tag "$TAG_SPECIFIC_LIGHT" "$TAG_MAJOR_LIGHT"
docker tag "$TAG_SPECIFIC_LIGHT" "$TAG_FIXED_LIGHT"

echo "--- Pushing all LIGHT tags to Docker Hub ---"
# 3. Push all light tags to Docker Hub
docker push "$TAG_SPECIFIC_LIGHT"
docker push "$TAG_MAJOR_LIGHT"
docker push "$TAG_FIXED_LIGHT"

echo "✅ Successfully pushed all LIGHT tags to Docker Hub!"
echo ""
echo "🚀 All versions have been successfully built and pushed."