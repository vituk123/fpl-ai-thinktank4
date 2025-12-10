#!/bin/bash

# Script to push code to GitHub after authentication

set -e

echo "=== Pushing to GitHub ==="

# Check if authenticated
if ! gh auth status &>/dev/null; then
    echo "Please authenticate first by running: gh auth login"
    exit 1
fi

# Create repo and push
echo "Creating repository 'fpl-ai-thinktank4' on GitHub..."
gh repo create fpl-ai-thinktank4 --public --source=. --remote=origin --push

echo "✅ Successfully pushed to GitHub!"
echo "Repository URL: https://github.com/$(gh api user --jq .login)/fpl-ai-thinktank4"

