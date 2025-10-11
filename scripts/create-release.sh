#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

VERSION=$1

echo "🚀 Creating release $VERSION"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
    echo "❌ Error: Must be on main branch to create release"
    echo "Current branch: $BRANCH"
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Working directory is not clean"
    echo "Please commit all changes before creating release"
    git status --short
    exit 1
fi

echo "📝 Creating and pushing tag $VERSION"
git tag -a "$VERSION" -m "Release $VERSION"
git push origin "$VERSION"

echo "⬆️ Pushing latest changes to main branch"
git push origin main

echo "✅ Release $VERSION created successfully!"
echo "📦 GitHub Actions is now building the release..."
echo "🔗 Check progress at: https://github.com/TestCraft-App/api-automation-agent/actions"
echo "🎯 Release will be available at: https://github.com/TestCraft-App/api-automation-agent/releases/tag/$VERSION"

echo ""
echo "⏳ Waiting a moment for GitHub to process the tag..."
sleep 5

if command -v open >/dev/null 2>&1; then
    echo "🌐 Opening GitHub releases page..."
    open "https://github.com/TestCraft-App/api-automation-agent/releases"
elif command -v xdg-open >/dev/null 2>&1; then
    echo "🌐 Opening GitHub releases page..."
    xdg-open "https://github.com/TestCraft-App/api-automation-agent/releases"
else
    echo "🌐 Visit: https://github.com/TestCraft-App/api-automation-agent/releases"
fi