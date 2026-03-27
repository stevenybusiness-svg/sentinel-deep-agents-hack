#!/bin/bash
# Sentinel — One-Command Deploy
#
# Usage: ./scripts/deploy.sh "commit message"
#
# What happens:
#   1. Commits your local changes
#   2. Pushes to GitHub
#   3. Vercel auto-deploys frontend (GitHub integration)
#   4. GitHub Actions auto-deploys EC2 backend (SSH action)
#
# That's it. One command, everything updates.

set -e
cd "$(git rev-parse --show-toplevel)"

COMMIT_MSG="$1"

# Check for changes
if [ -z "$(git status --porcelain)" ]; then
  echo "No changes to deploy."
  # Still push in case there are unpushed commits
  git push origin master 2>/dev/null && echo "Pushed unpushed commits." || echo "Already up to date."
  exit 0
fi

# Get commit message
if [ -z "$COMMIT_MSG" ]; then
  echo "Changes:"
  git status --short
  echo ""
  read -p "Commit message: " COMMIT_MSG
  [ -z "$COMMIT_MSG" ] && echo "Aborted." && exit 1
fi

# Commit and push
git add -A
git commit -m "$COMMIT_MSG"
git push origin master

echo ""
echo "Deployed."
echo "  Vercel: auto-deploying frontend now"
echo "  EC2:    GitHub Actions deploying backend now"
echo ""
echo "Check status: https://github.com/stevenybusiness-svg/sentinel-deep-agents-hack/actions"
