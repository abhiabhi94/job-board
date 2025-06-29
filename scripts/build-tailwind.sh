#!/bin/bash

# Smart Tailwind CSS build - only updates if output would change
echo "Checking if Tailwind CSS needs rebuilding..."

# Set paths (relative to scripts directory)
TAILWIND_CLI="../tailwindcss"
INPUT_CSS="../job_board/static/css/input.css"
OUTPUT_CSS="../job_board/static/css/output.css"
TEMP_CSS="../job_board/static/css/output.tmp.css"

# Download standalone CLI if it doesn't exist
if [ ! -f "$TAILWIND_CLI" ]; then
    echo "Downloading Tailwind CSS standalone CLI..."
    curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 -o ../tailwindcss
    chmod +x ../tailwindcss
fi

# Build CSS to temporary file
echo "Building CSS to check for changes..."
$TAILWIND_CLI -i "$INPUT_CSS" -o "$TEMP_CSS" --minify

# Check if output differs from current file
if [ ! -f "$OUTPUT_CSS" ] || ! cmp -s "$TEMP_CSS" "$OUTPUT_CSS"; then
    echo "CSS has changed, updating output.css..."
    mv "$TEMP_CSS" "$OUTPUT_CSS"
    git add "$OUTPUT_CSS"
    echo "Tailwind CSS build completed successfully and staged for commit."
else
    echo "CSS unchanged, skipping update"
    rm "$TEMP_CSS"
fi
