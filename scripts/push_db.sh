#!/bin/bash
git pull
cd "$(dirname "$0")" || exit 1
git add .
if git diff-index --quiet HEAD --; then
    : # No changes
else
    git commit -m "Update database $(date +'%Y-%m-%d %H:%M:%S')"
    git push origin main
fi