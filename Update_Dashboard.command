#!/bin/bash

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "---------------------------------------------------"
echo "🚀 Starting Update & Deploy Process..."
echo "---------------------------------------------------"

# Run the update script
./scripts/update_and_deploy.sh

# Keep window open to see results
echo "---------------------------------------------------"
read -p "Press [Enter] key to close..."
