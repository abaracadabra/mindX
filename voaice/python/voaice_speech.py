#!/usr/bin/env python3
"""voaice_speech — Python text-to-speech and speech-to-text tools for voaice.

The voaice core is deliberately torch-free and Python-free (in-house JS DSP).
These are the OPTIONAL Python backends: when a host has richer Python speech
stacks installed (Coqui TTS, whisper, vosk…), voaice can reach them through
this one small, dependency-probing bridge — and degrade honestly when it can't.

Same doctrine as the JS side:
  · CAPABILITY is probed and reported before anything is relied on.
  · No engine present → an explicit error with an install hint, never a fake
    transcript and never silent synthesis of nothing.
  · Every result names the engine that produced it.

CLI (JSON on stdout):
  python3 voaice_speech.py capability
  python3 voaice_speech.py tts --text "hello" --out out.wav [--engine E] [--voice V] [--rate R]
  python3 voaice_speech.py stt --in clip.wav [--engine E] [--model PATH] [--language en]

Engines, best-first:
  TTS:  coqui (TTS)  ·  pyttsx3 (offline, OS voices)  ·  gtts (online, Google)
  STT:  whisper (openai-whisper)  ·  vosk  ·  speech_recognition (Google web)

© Professor Codephreak - rage.pythai.net
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
import wave


def _have(mod: str) -> bool:
    """Is an importable module present, without importing it?"""
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


# name -> (probe module, human install hint, quality)
TTS_ENGINES = {
    "coqui":   ("TTS", "pip install TTS", "high"),
    "pyttsx3": ("pyttsx3", "pip install pyttsx3 (offline; uses OS voices)", "medium"),
    "gtts":    ("gtts", "pip install gTTS (online; needs network)", "medium"),
}
STT_ENGINES = {
    "whisper": ("whisper", "pip install -U openai-whisper", "high"),
    "vosk":    ("vosk", "pip install vosk + download a model", "medium"),
    "speech_recognition": ("speech_recognition", "pip install SpeechRecognition (Google web API; needs network)", "medium"),
}


def available(engines: dict) -> list[str]:
    return [name for name, (mod, _h, _q) in engines.items() if _have(mod)]


def voices() -> dict:
    """Enumerate every voice/model the installed engines expose — the raw
    material a voice admin panel offers for selection."""
    out = {"tts": {}, "stt": {}}
    # pyttsx3: OS voices with their metadata + the settable ranges
    if _have("pyttsx3"):
        try:
            import pyttsx3  # noqa
            eng = pyttsx3.init()
            vs = []
            for v in eng.getProperty("voices"):
                vs.append({
                    "id": v.id,
                    "name": getattr(v, "name", v.id),
                    "languages": [l.decode() if isinstance(l, bytes) else str(l) for l in (getattr(v, "languages", []) or [])],
                    "gender": getattr(v, "gender", None),
                    "age": getattr(v, "age", None),
                })
            out["tts"]["pyttsx3"] = {
                "voices": vs,
                "settings": {
                    "rate": {"default": eng.getProperty("rate"), "min": 50, "max": 400, "unit": "wpm"},
                    "volume": {"default": eng.getProperty("volume"), "min": 0.0, "max": 1.0},
                },
            }
        except Exception as e:
            out["tts"]["pyttsx3"] = {"error": str(e)}
    # Coqui: list model names (network/local catalogue)
    if _have("TTS"):
        try:
            from TTS.api import TTS as CoquiTTS  # noqa
            out["tts"]["coqui"] = {"models": list(CoquiTTS().list_models())[:200]}
        except Exception as e:
            out["tts"]["coqui"] = {"note": "install/catalogue unavailable", "error": str(e)}
    # vosk: discover models on disk (VOSK_MODEL_PATH or common dirs)
    if _have("vosk"):
        import os
        roots = [os.environ.get("VOSK_MODEL_PATH", ""), os.path.expanduser("~/vosk-models"),
                 os.path.expanduser("~/.cache/vosk"), "/usr/share/vosk", "./models"]
        found = []
        for root in roots:
            if root and os.path.isdir(root):
                for name in sorted(os.listdir(root)):
                    p = os.path.join(root, name)
                    if os.path.isdir(p) and (os.path.isdir(os.path.join(p, "am")) or name.startswith("vosk")):
                        found.append({"name": name, "path": p})
        out["stt"]["vosk"] = {"models": found, "hint": "set VOSK_MODEL_PATH or drop a model in ~/vosk-models"}
    if _have("whisper"):
        out["stt"]["whisper"] = {"models": ["tiny", "base", "small", "medium", "large"]}
    return out


def capability() -> dict:
    tts = available(TTS_ENGINES)
    stt = available(STT_ENGINES)
    return {
        "python": sys.version.split()[0],
        "tts": {"available": tts, "resolved": tts[0] if tts else None,
                "hints": [] if tts else [f"{n}: {h}" for n, (_m, h, _q) in TTS_ENGINES.items()]},
        "stt": {"available": stt, "resolved": stt[0] if stt else None,
                "hints": [] if stt else [f"{n}: {h}" for n, (_m, h, _q) in STT_ENGINES.items()]},
    }


# ── TTS ─────────────────────────────────────────────────────────────────────
def _tts_coqui(text, out, voice=None, rate=None, volume=None):
    from TTS.api import TTS as CoquiTTS  # noqa
    model = voice or "tts_models/en/ljspeech/tacotron2-DDC"
    CoquiTTS(model_name=model, progress_bar=False).tts_to_file(text=text, file_path=out)


def _tts_pyttsx3(text, out, voice=None, rate=None, volume=None):
    import pyttsx3  # noqa
    eng = pyttsx3.init()
    if rate:
        eng.setProperty("rate", int(rate))
    if volume is not None:
        eng.setProperty("volume", float(volume))
    if voice:
        for v in eng.getProperty("voices"):
            if voice.lower() in (v.id + " " + getattr(v, "name", "")).lower():
                eng.setProperty("voice", v.id)
                break
    eng.save_to_file(text, out)
    eng.runAndWait()


def _tts_gtts(text, out, voice=None, rate=None, volume=None):
    from gtts import gTTS  # noqa
    # gTTS writes mp3; convert to wav only if ffmpeg is present, else keep mp3 path honest
    tmp = out if out.endswith(".mp3") else out + ".mp3"
    gTTS(text=text, lang=(voice or "en")).save(tmp)
    if tmp != out:
        import shutil
        import subprocess
        if shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", tmp, out], check=True)
        else:
            raise RuntimeError("gtts produced mp3; install ffmpeg to write .wav, or request an .mp3 output")


_TTS_IMPL = {"coqui": _tts_coqui, "pyttsx3": _tts_pyttsx3, "gtts": _tts_gtts}


def tts(text, out, engine=None, voice=None, rate=None, volume=None) -> dict:
    if not text or not text.strip():
        raise ValueError("nothing to speak")
    avail = available(TTS_ENGINES)
    if not avail:
        raise RuntimeError("no Python TTS engine installed:\n  " +
                           "\n  ".join(f"{n}: {h}" for n, (_m, h, _q) in TTS_ENGINES.items()))
    name = engine or avail[0]
    if name not in avail:
        raise RuntimeError(f"TTS engine '{name}' not available (have: {', '.join(avail) or 'none'})")
    _TTS_IMPL[name](text, out, voice, rate, volume)
    return {"engine": name, "out": out, "text": text}


# ── STT ─────────────────────────────────────────────────────────────────────
def _read_wav(path):
    with wave.open(path, "rb") as w:
        return {"channels": w.getnchannels(), "rate": w.getframerate(), "frames": w.getnframes()}


def _stt_whisper(path, model=None, language=None):
    import whisper  # noqa
    m = whisper.load_model(model or "base")
    res = m.transcribe(path, language=language, fp16=False)
    return res.get("text", "").strip()


def _stt_vosk(path, model=None, language=None):
    from vosk import Model, KaldiRecognizer  # noqa
    import json as _json
    if not model:
        raise RuntimeError("vosk needs a model path (--model); download one from alphacephei.com/vosk/models")
    with wave.open(path, "rb") as w:
        rec = KaldiRecognizer(Model(model), w.getframerate())
        rec.SetWords(False)
        out = []
        while True:
            data = w.readframes(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                out.append(_json.loads(rec.Result()).get("text", ""))
        out.append(_json.loads(rec.FinalResult()).get("text", ""))
    return " ".join(t for t in out if t).strip()


def _stt_sr(path, model=None, language=None):
    import speech_recognition as sr  # noqa
    r = sr.Recognizer()
    with sr.AudioFile(path) as src:
        audio = r.record(src)
    return r.recognize_google(audio, language=(language or "en-US")).strip()


_STT_IMPL = {"whisper": _stt_whisper, "vosk": _stt_vosk, "speech_recognition": _stt_sr}


def stt(path, engine=None, model=None, language=None) -> dict:
    avail = available(STT_ENGINES)
    if not avail:
        raise RuntimeError("no Python STT engine installed — refusing to invent a transcript:\n  " +
                           "\n  ".join(f"{n}: {h}" for n, (_m, h, _q) in STT_ENGINES.items()))
    name = engine or avail[0]
    if name not in avail:
        raise RuntimeError(f"STT engine '{name}' not available (have: {', '.join(avail) or 'none'})")
    text = _STT_IMPL[name](path, model, language)
    return {"engine": name, "text": text, "language": language or "auto", "audio": _read_wav(path)}


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="voaice_speech", description="voaice Python TTS/STT tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capability")
    sub.add_parser("voices")
    t = sub.add_parser("tts")
    t.add_argument("--text", required=True); t.add_argument("--out", required=True)
    t.add_argument("--engine"); t.add_argument("--voice"); t.add_argument("--rate"); t.add_argument("--volume")
    s = sub.add_parser("stt")
    s.add_argument("--in", dest="inp", required=True); s.add_argument("--engine")
    s.add_argument("--model"); s.add_argument("--language")
    a = p.parse_args(argv)
    try:
        if a.cmd == "capability":
            print(json.dumps(capability(), indent=2))
        elif a.cmd == "voices":
            print(json.dumps(voices(), indent=2))
        elif a.cmd == "tts":
            print(json.dumps(tts(a.text, a.out, a.engine, a.voice, a.rate, a.volume)))
        elif a.cmd == "stt":
            print(json.dumps(stt(a.inp, a.engine, a.model, a.language)))
        return 0
    except Exception as e:  # honest, structured failure
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
