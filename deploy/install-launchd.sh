#!/bin/bash

# MDreport-style service installer
PLIST_NAME="com.mattkuo.iasdashboard.plist"
PLIST_SOURCE="./deploy/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "⚙️ Installing IAS Dashboard service..."

if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Source plist not found: $PLIST_SOURCE"
    exit 1
fi

# Render project path into the plist before installing.
TMP_PLIST="$(mktemp /tmp/iasdashboard.plist.XXXXXX)"
sed "s#__PROJECT_DIR__#${PROJECT_DIR//\#/\\#}#g" "$PLIST_SOURCE" > "$TMP_PLIST"

# Copy and load
cp "$TMP_PLIST" "$PLIST_DEST"
launchctl unload "$PLIST_DEST" 2>/dev/null
launchctl load "$PLIST_DEST"
rm -f "$TMP_PLIST"

echo "✅ Service installed and loaded."
launchctl list | grep iasdashboard
