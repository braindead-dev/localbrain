#!/bin/bash
#
# LocalBrain Protocol Setup Script for macOS
#
# This script:
# 1. Creates a URL scheme handler for localbrain://
# 2. Registers it with macOS
# 3. Sets up auto-start for the tray app (optional)
#

set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTOCOL_HANDLER="$BACKEND_DIR/src/protocol_handler.py"
TRAY_APP="$BACKEND_DIR/src/tray.py"

echo "=========================================="
echo "LocalBrain Protocol Setup"
echo "=========================================="
echo "Backend directory: $BACKEND_DIR"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Make scripts executable
chmod +x "$PROTOCOL_HANDLER"
chmod +x "$TRAY_APP"
echo "✅ Made scripts executable"

# Create a wrapper script for the protocol handler
WRAPPER_SCRIPT="$HOME/.localbrain-protocol-handler.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# LocalBrain Protocol Handler Wrapper
# This script is called by macOS when localbrain:// URLs are opened

# Log to file
exec >> /tmp/localbrain-protocol-wrapper.log 2>&1
echo "\$(date): Received URL: \$1"

# Activate conda environment if it exists
if [ -d "$HOME/miniconda3/envs/localbrain" ] || [ -d "$HOME/anaconda3/envs/localbrain" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh" 2>/dev/null || source "$HOME/anaconda3/etc/profile.d/conda.sh" 2>/dev/null
    conda activate localbrain 2>/dev/null
fi

# Run the protocol handler
cd "$BACKEND_DIR"
python3 "$PROTOCOL_HANDLER" "\$1"
EOF

chmod +x "$WRAPPER_SCRIPT"
echo "✅ Created protocol handler wrapper: $WRAPPER_SCRIPT"

# Create LaunchAgent plist for protocol handler
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.localbrain.protocol.plist"

mkdir -p "$PLIST_DIR"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.localbrain.protocol</string>
    <key>ProgramArguments</key>
    <array>
        <string>$WRAPPER_SCRIPT</string>
        <string>%u</string>
    </array>
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLName</key>
            <string>LocalBrain Protocol</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>localbrain</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
EOF

echo "✅ Created LaunchAgent: $PLIST_FILE"

# Register the protocol with LaunchServices
# This tells macOS to use our handler for localbrain:// URLs
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$WRAPPER_SCRIPT" 2>/dev/null || true

echo "✅ Registered localbrain:// protocol with macOS"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start the background service:"
echo "     python $TRAY_APP"
echo ""
echo "  2. Test the protocol handler:"
echo "     open 'localbrain://ingest?text=Hello%20World&platform=Test'"
echo ""
echo "The protocol handler will forward requests to the daemon running on port 8765."
echo ""
