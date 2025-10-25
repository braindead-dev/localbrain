#!/bin/bash

# Simple script to create a basic icon for development
# For production, you'll need proper .icns files

echo "Creating basic app icon..."

# Create a simple PNG icon (you'll want to replace this with your actual icon)
if command -v convert >/dev/null 2>&1; then
    # Using ImageMagick if available
    convert -size 512x512 xc:"#4F46E5" -fill white -pointsize 72 -gravity center -annotate +0+0 "LB" assets/icon.png
    echo "Created icon.png using ImageMagick"
elif command -v magick >/dev/null 2>&1; then
    # Using newer ImageMagick
    magick -size 512x512 xc:"#4F46E5" -fill white -pointsize 72 -gravity center -annotate +0+0 "LB" assets/icon.png
    echo "Created icon.png using ImageMagick"
else
    echo "ImageMagick not found. Please install it or manually create assets/icon.png"
    echo "For now, creating a placeholder..."
    touch assets/icon.png
fi
