#!/usr/bin/env bash
#
# install.sh — set up the voaice Python speech tools in a virtualenv.
#
# Creates a venv beside this script (python/.venv) and installs the TTS/STT
# backends you choose. The voaice Node bridge (voaice/python) auto-detects this
# venv, so after running this once, `PythonSpeech` just works.
#
#   ./install.sh                     # light  — pyttsx3 + vosk (offline, torch-free)
#   ./install.sh --online            # + gTTS + SpeechRecognition (need network)
#   ./install.sh --full              # + Coqui TTS + openai-whisper (pull torch, heavy)
#   ./install.sh --profile full
#   ./install.sh --venv /path/to/venv
#   VOAICE_PYTHON=python3.11 ./install.sh
#
# Nothing here needs root. If `python3 -m venv` fails, it tells you the one apt
# package to install and stops — it never sudo's on your behalf.
#
# © Professor Codephreak - rage.pythai.net
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py="${VOAICE_PYTHON:-python3}"
venv="$here/.venv"
profiles=("requirements-light.txt")

while [ $# -gt 0 ]; do
  case "$1" in
    --online) profiles+=("requirements-online.txt") ;;
    --full)   profiles+=("requirements-online.txt" "requirements-full.txt") ;;
    --profile) shift; case "${1:-}" in
                 light)  profiles=("requirements-light.txt") ;;
                 online) profiles=("requirements-light.txt" "requirements-online.txt") ;;
                 full)   profiles=("requirements-light.txt" "requirements-online.txt" "requirements-full.txt") ;;
                 *) echo "unknown profile: ${1:-} (light|online|full)" >&2; exit 2 ;;
               esac ;;
    --venv)   shift; venv="${1:?--venv needs a path}" ;;
    --python) shift; py="${1:?--python needs an executable}" ;;
    -h|--help) sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# de-dup the profile list, preserving order
mapfile -t profiles < <(printf '%s\n' "${profiles[@]}" | awk '!seen[$0]++')

echo "🐍 voaice Python speech tools"

command -v "$py" >/dev/null 2>&1 || { echo "✗ '$py' not found — install Python 3.8+ or set VOAICE_PYTHON." >&2; exit 1; }
ver="$("$py" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
echo "  python: $py ($ver)"
"$py" -c 'import sys;sys.exit(0 if sys.version_info[:2]>=(3,8) else 1)' \
  || { echo "✗ Python $ver is too old — need 3.8+." >&2; exit 1; }

if [ ! -d "$venv" ]; then
  echo "  creating venv: $venv"
  if ! "$py" -m venv "$venv" 2>/tmp/voaice_venv_err; then
    echo "✗ could not create the venv:" >&2; cat /tmp/voaice_venv_err >&2
    echo "  on Debian/Ubuntu this usually means:  sudo apt install python3-venv" >&2
    exit 1
  fi
else
  echo "  reusing venv: $venv"
fi

vpy="$venv/bin/python"
echo "  upgrading pip…"
"$vpy" -m pip install --quiet --upgrade pip >/dev/null

for req in "${profiles[@]}"; do
  echo "  installing $req …"
  "$vpy" -m pip install --quiet -r "$here/$req"
done

echo ""
echo "✓ installed. capability:"
"$vpy" "$here/voaice_speech.py" capability

cat <<EOF

Use it:
  $venv/bin/python $here/voaice_speech.py tts --text "the machine speaks" --out out.wav
  $venv/bin/python $here/voaice_speech.py stt --in clip.wav

From Node, voaice's PythonSpeech auto-detects this venv — no extra config.
EOF
