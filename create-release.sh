#!/bin/bash
# WebUIFlasher Release Helper
# Usage: ./create-release.sh v1.0.0 "Release description"

set -e

VERSION=$1
DESCRIPTION=$2

if [ -z "$VERSION" ] || [ -z "$DESCRIPTION" ]; then
    echo "Usage: $0 <version> <description>"
    echo "Example: $0 v1.0.0 'Initial release with Docker support'"
    exit 1
fi

# Validate version format
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format v1.0.0"
    exit 1
fi

echo "🏷️  Creating release $VERSION"
echo "📝 Description: $DESCRIPTION"

# Check if tag already exists
if git tag -l | grep -q "^$VERSION$"; then
    echo "❌ Tag $VERSION already exists"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Working directory is not clean. Please commit all changes first."
    exit 1
fi

# Create and push tag
echo "🏷️  Creating and pushing tag..."
git tag -a "$VERSION" -m "$DESCRIPTION"
git push origin "$VERSION"

echo "✅ Tag $VERSION created and pushed"
echo "🚀 GitHub Actions will now build and publish the Docker image"
echo "📦 Create the release at: https://github.com/the78mole/WebUIFlasher/releases/new?tag=$VERSION"
echo ""
echo "Suggested release title: WebUIFlasher $VERSION"
echo "Suggested release notes:"
echo "---"
echo "$DESCRIPTION"
echo ""
echo "## Docker Images"
echo "- \`ghcr.io/the78mole/webuiflasher:$VERSION\`"
echo "- \`ghcr.io/the78mole/webuiflasher:latest\`"
echo ""
echo "## Quick Start"
echo "\`\`\`bash"
echo "docker run -d --privileged -p 8000:8000 -v /dev:/dev ghcr.io/the78mole/webuiflasher:$VERSION"
echo "\`\`\`"
echo "---"
