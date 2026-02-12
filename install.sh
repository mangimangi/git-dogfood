#!/bin/bash
# git-dogfood/install.sh - Install or update git-dogfood in a project
#
# Environment (v2 contract):
#   VENDOR_REF        - Version/ref to install
#   VENDOR_REPO       - GitHub repo (owner/name)
#   VENDOR_INSTALL_DIR - Base directory for installed files
#   GH_TOKEN          - Auth token for private repos
#
# Fallback (v1 compat):
#   install.sh <version> [<repo>]
#
set -euo pipefail

VERSION="${VENDOR_REF:-${1:?Usage: install.sh <version> [<repo>]}}"
DOGFOOD_REPO="${VENDOR_REPO:-${2:-mangimangi/git-dogfood}}"
INSTALL_DIR="${VENDOR_INSTALL_DIR:-.dogfood}"

# File download helper - uses gh api when GH_TOKEN is set, curl otherwise
fetch_file() {
    local repo_path="$1"
    local dest="$2"
    local ref="${3:-v$VERSION}"

    if [ -n "${GH_TOKEN:-}" ] && command -v gh &>/dev/null; then
        gh api "repos/$DOGFOOD_REPO/contents/$repo_path?ref=$ref" --jq '.content' | base64 -d > "$dest"
    else
        local base="https://raw.githubusercontent.com/$DOGFOOD_REPO"
        curl -fsSL "$base/$ref/$repo_path" -o "$dest"
    fi
}

echo "Installing git-dogfood v$VERSION from $DOGFOOD_REPO"

# Create directories
mkdir -p "$INSTALL_DIR" .github/workflows

# Download resolve script
echo "Downloading resolve..."
fetch_file "dogfood/resolve" "$INSTALL_DIR/resolve"
chmod +x "$INSTALL_DIR/resolve"

# Install workflow (first install only)
if [ ! -f ".github/workflows/dogfood.yml" ]; then
    if fetch_file "templates/github/workflows/dogfood.yml" \
                  ".github/workflows/dogfood.yml" 2>/dev/null; then
        echo "Installed .github/workflows/dogfood.yml"
    fi
else
    echo "Workflow .github/workflows/dogfood.yml already exists, skipping"
fi

echo ""
echo "Done! git-dogfood v$VERSION installed."
