#!/bin/bash
set -euxo pipefail

# Generate JavaScript test module from main.js
echo "Generating JavaScript test module..."

# Set paths
SCRIPT_DIR="$(dirname "$0")"
GENERATE_SCRIPT="$SCRIPT_DIR/generate-test-module.js"
OUTPUT_MJS="job_board/static/js/main.mjs"

# Download Node.js binary if it doesn't exist
NODE_BINARY="./node"
if [ ! -f "$NODE_BINARY" ]; then
    echo "Downloading Node.js binary..."
    curl -L https://github.com/vercel/pkg-fetch/releases/download/v3.4/node-v18.5.0-linux-x64 -o ./node
    chmod +x ./node
fi

# Run the generation script
if "$NODE_BINARY" "$GENERATE_SCRIPT"; then
    # Stage the generated file for commit if we're in a git repository
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git add "$OUTPUT_MJS"
        echo "✅ Generated main.mjs and staged for commit"
    else
        echo "✅ Generated main.mjs successfully"
    fi
else
    echo "❌ Failed to generate test module"
    exit 1
fi
