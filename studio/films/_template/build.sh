#!/bin/sh
# Shabd Sketch · शब्द-चित्र — build one reel from its spec.json:
#   sh build.sh            (from the reel's folder or anywhere; LIB = the Lemo-Opuscar library)
# voice (online, edge-tts) → speech check → events → mix → picture → master → reading check → subtitles → poster
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
LIB=${LIB:-$(cd "$HERE/../.." && pwd)}
export LIB
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1 HF_HUB_DISABLE_SYMLINKS_WARNING=1   # Hindi text in a Windows console
[ -f "$LIB/core/render/video.mjs" ] || { echo "set LIB to the Lemo-Opuscar library folder"; exit 1; }
if [ -n "$PY" ]; then :; elif [ -x "$LIB/.venv/bin/python" ]; then PY="$LIB/.venv/bin/python"; else PY="$LIB/.venv/Scripts/python"; fi
NAME=$(basename "$HERE"); FPS=30; SIZE=1080x1920
PHERE=$(cygpath -m "$HERE" 2>/dev/null || echo "$HERE")      # a path Python understands on Windows too
spec() { "$PY" -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8')).get(sys.argv[2],sys.argv[3]))" "$PHERE/spec.json" "$1" "$2"; }
VOICE=$(spec voice hi-IN-SwaraNeural); RATE=$(spec rate +6%)
cd "$LIB"
"$PY" "$HERE/tools/lines.py"
"$PY" core/tts/tts_zh.py "$HERE/lines.json" "$HERE/vo" --voice "$VOICE" --rate="$RATE"
"$PY" core/tts/asr_check.py "$HERE/lines.json" "$HERE/vo" --lang hi --model small || echo "(speech check: listen to the lines it flags)"
node core/render/events.mjs "$HERE" --size $SIZE
"$PY" "$HERE/audio.py"
node core/render/readcheck.mjs "$HERE" --size $SIZE > "$HERE/out/readcheck.txt" 2>&1 && echo "readcheck ok" || { tail -20 "$HERE/out/readcheck.txt"; exit 1; }
node core/render/video.mjs "$HERE" --size $SIZE --fps $FPS --workers 3 --out "$HERE/out/video.mp4"
sh core/render/mux.sh "$HERE/out/video.mp4" "$HERE/mix.wav" "$HERE/$NAME.mp4" $FPS 1
"$PY" "$HERE/tools/srt.py" "$HERE/$NAME.srt"
DUR=$("$PY" -c "import json,sys;print(round(json.load(open(sys.argv[1]))['dur']-1.2,1))" "$PHERE/events.json")
node core/render/still.mjs "$HERE" $DUR --size $SIZE --out "$HERE/out" --prefix poster_ && cp "$HERE/out/poster_$DUR.jpg" "$HERE/poster.jpg"
echo "done: $HERE/$NAME.mp4"
