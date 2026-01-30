#!/bin/bash

# MDreport-style service installer
PLIST_NAME="com.mattkuo.iasdashboard.plist"
PLIST_SOURCE="./deploy/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "⚙️ Installing IAS Dashboard service..."

if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Source plist not found: $PLIST_SOURCE"
    exit 1
fi

# Copy and load
cp "$PLIST_SOURCE" "$PLIST_DEST"
launchctl unload "$PLIST_DEST" 2>/dev/null
launchctl load "$PLIST_DEST"

echo "✅ Service installed and loaded."
launchctl list | grep iasdashboard
