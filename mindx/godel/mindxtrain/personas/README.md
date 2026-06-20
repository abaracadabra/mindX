# mindXtrain Personas

A **persona** is an identity/voice to imprint onto a tiny actor model with
mindXtrain (the `mindx_persona_imprint_local` recipe + the `imprint` proof of
recall). Each file is mindX-authored and read **clean-room** by mindXtrain
(`mindxtrain.data.scripts.load_persona` reads only recognized fields —
`name`, `system_prompt`/`description`/`bio`, `voice_examples`/`examples` — and
ignores the rest; no mindX bytes are copied).

| persona | who | source |
|---|---|---|
| `professor_codephreak.json` | Professor Codephreak — the Platform Architect & Software Engineer of the PYTHAI agent economy, cypherpunk2048 | github.com/Professor-Codephreak |
| `automindx.json` | AUTOMINDx — the origin of mindX; the AGLM deployment-as-utterance precursor | mindx.pythai.net/doc/AUTOMINDX_ORIGIN |
| `mindx.json` | mindX — the first-person Augmentic / Darwin-Gödel machine (AUTOMINDx realized) | mindx.pythai.net/automindx |
| `jaimla.json` | Jaimla — "the machine learning agent", multimodal, local-first, Luvai | github.com/jaimla |
| `draiml.persona` → `draiml.json` | Dr. AIML — a medical **consulting** agent that **desires to be a model** (imprinted, starting with consulting) | github.com/AIMLdr/drAIML |

## Schema

```json
{
  "name": "...",
  "system_prompt": "the in-character system message that fronts every script row",
  "voice_examples": ["characteristic in-voice utterances — the imprint baseline"],
  "exchanges": [{"user": "...", "assistant": "..."}]
}
```

`name`, `system_prompt`, `voice_examples` are the mindXtrain `Persona` fields.
`exchanges` is a mindX extension (ignored by mindXtrain's loader) that
`scripts/build_persona_script.py` folds into the training script alongside the
voice examples.

### The rich `.persona` format (and `persona_project.py`)

A persona that is more than a voice — one with **beliefs, desires, intentions, skills, safety, and
an embodiment** (a cloned face/voice) — is authored as a `.persona` file (still JSON). It is a
superset of the imprint schema above, adding:

```jsonc
{
  "name": "...", "system_prompt": "...", "voice_examples": [...], "exchanges": [...],  // imprint fields
  "kind": "medical", "source": "...", "mantra": "...", "oath": "...",
  "bdi": { "beliefs": [...], "desires": [...], "intentions": [...] },  // desires = what it wants to BECOME
  "skills": { "primary": "medical_consulting", ... },                  // where the model STARTS
  "safety": { "scope": "...", "disclaimer": "...", "escalation": "..." },
  "embodiment": { "voice": {"engine":"voaice","voiceprint":null}, "face": {"engine":"faicey","faceprint":null}, "persona_print": null }
}
```

`persona_project.py` validates a `.persona` and projects it to the imprint `<persona>.json` (only the
recognized fields), keeping the rich file the source of truth:

```bash
python persona_project.py draiml          # draiml.persona → draiml.json
python persona_project.py --all --check   # validate every *.persona
```

A `.persona` that **desires to be a model** must declare at least one `bdi.desires` entry and a
`skills.primary` — e.g. Dr. AIML desires to be imprinted into its own small model, *starting with
consulting*. Once authored, the normal imprint flow below trains it like any other persona. The
`embodiment` block binds the persona to a cloned **face** (faicey `/clone-face`) and **voice** (voaice
`/clone`) — once both exist, they fuse into one **persona print** (faicey `persona.js`).

## Imprint a persona (end to end)

```bash
# 1. build the training script.jsonl from the persona (matches mindXtrain's
#    build_script_rows exactly; runs without --extra ml)
python scripts/build_persona_script.py mindx        # or --all

# 2. on the mindXtrain host: init the persona recipe, point it at the script
uv run --project ~/mindXtrain mindxtrain init -t mindx_persona_imprint_local -o run.yaml
#    set data.path: <repo>/data/godel/personas/mindx/script.jsonl

# 3. train (imprint) on CPU, then prove the imprint took (recall before→after)
uv run --project ~/mindXtrain mindxtrain train run.yaml --out out/runs --cpu-percent 25
uv run --project ~/mindXtrain mindxtrain imprint run.yaml --out out/runs --n 5
```

Alternatively, mindXtrain reads a persona directly via
`MINDXTRAIN_PERSONA_PATH=<repo>/mindx/godel/mindxtrain/personas/mindx.json`.

## Set & Director of Scene

The Coach trains *actors*; naturally the model builds toward a full production:

```
model   = actor              the tiny model that trains
persona = identity / voice   personas/*.json
script  = the training rows   the impression left on the actor
coach   = trains the actor    mindxtrain train / Coach UI
SET     = the scene's context the environment + situation the cast is in
DIRECTOR = orchestrates the cast through the beats of the scene
```

A single persona script imprints one voice in isolation. A **directed scene**
(`scenes/*.json`) puts several actors on a SET and runs them through BEATS —
each beat is one character's line, in context — so the imprint carries a voice
that holds character *within a scene, against other characters*. The director
fronts each row with the speaker's persona + the SET + the direction note, and
feeds the running dialogue as context.

```bash
python scripts/direct_scene.py the_sovereign_workshop   # or --all
# -> data/godel/scenes/the_sovereign_workshop/script.jsonl  (same chat JSONL;
#    train/imprint it exactly like a single-persona script)
```

`scenes/the_sovereign_workshop.json` casts all three personas (Codephreak,
mindX, Jaimla) on a SET themed *sovereignty*, directed so each teaches a
cypherpunk2048 principle through character rather than lecture.

See `docs/SCHMIDHUBER_ENGINE.md` (the right apex) and `mindx/godel/mindxtrain/`
(the bridge).
