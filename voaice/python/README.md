# voaice Python speech tools

Optional **Python** text-to-speech and speech-to-text backends for
[voaice](../README.md). The voaice core is torch-free, zero-Python JS DSP;
these reach richer Python stacks **when a host has them**, and degrade honestly
when it doesn't — the same doctrine as the JS `voaice/tts` and `voaice/stt`.

## Use

```bash
python3 voaice_speech.py capability          # what's installed here (JSON)

python3 voaice_speech.py tts --text "the machine speaks" --out out.wav
python3 voaice_speech.py tts --text "..." --out out.wav --engine pyttsx3 --rate 165

python3 voaice_speech.py stt --in clip.wav                # transcribe (16k mono wav)
python3 voaice_speech.py stt --in clip.wav --engine vosk --model /models/vosk-en
```

Every command prints JSON. On success, `tts` reports `{engine, out, text}` and
`stt` reports `{engine, text, language, audio}`. With **no engine installed**,
both exit non-zero with a structured `{error}` and an install hint — `stt`
never invents a transcript.

## Engines (best-first)

| | engines | note |
|---|---|---|
| **TTS** | `coqui` (TTS) · `pyttsx3` · `gtts` | pyttsx3 is offline + lightest; Coqui is best but pulls torch |
| **STT** | `whisper` · `vosk` · `speech_recognition` | vosk is offline + torch-free; whisper is best but pulls torch |

Install only what you need (see `requirements.txt`). From Node, voaice's
`TTS`/`STT` façades pick the Python backend up automatically as the `python`
engine when `voaice_speech.py capability` reports one available.
