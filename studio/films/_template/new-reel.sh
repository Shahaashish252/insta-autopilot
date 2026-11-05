#!/bin/sh
# Start a new Shabd Sketch reel:  sh new-reel.sh <slug> [<films folder>]
# Copies this template (code, fonts, tools) into <films folder>/<slug>/ (default: $LIB/films) with an example spec.json
# to replace; then edit spec.json (and, for a custom illustration, add js/scenes/<name>.js) and run sh <slug>/build.sh.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SLUG=${1:?usage: sh new-reel.sh <slug> [films folder]}
DEST=${2:-${LIB:-$HERE/../..}/films}/$SLUG
[ -e "$DEST" ] && { echo "$DEST already exists"; exit 1; }
mkdir -p "$DEST/out"
cp -r "$HERE/index.html" "$HERE/audio.py" "$HERE/build.sh" "$HERE/js" "$HERE/fonts" "$HERE/tools" "$HERE/CREDITS" "$DEST/"
cp "$HERE/spec.example.json" "$DEST/spec.json"
echo "new reel: $DEST  (edit spec.json, then: sh $DEST/build.sh)"
