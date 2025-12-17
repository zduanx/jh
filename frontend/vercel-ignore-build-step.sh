#!/bin/bash

# Vercel Ignored Build Step
# This script determines whether Vercel should build based on file changes
# Returns exit code 1 to skip build, exit code 0 to proceed with build

echo "Checking if frontend files changed..."

# Check if VERCEL_GIT_PREVIOUS_SHA exists (not first deployment)
if [ -z "$VERCEL_GIT_PREVIOUS_SHA" ]; then
  echo "First deployment or no previous commit - proceeding with build"
  exit 0
fi

# Get list of changed files between previous and current commit
CHANGED_FILES=$(git diff --name-only $VERCEL_GIT_PREVIOUS_SHA $VERCEL_GIT_COMMIT_SHA)

echo "Changed files:"
echo "$CHANGED_FILES"

# Check if any frontend files changed
if echo "$CHANGED_FILES" | grep -q "^frontend/"; then
  echo "✓ Frontend files changed - proceeding with build"
  exit 0
else
  echo "✗ No frontend files changed - skipping build"
  exit 1
fi
