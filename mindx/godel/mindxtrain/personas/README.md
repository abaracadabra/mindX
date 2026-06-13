# mindXtrain Personas

A **persona** is an identity/voice to imprint onto a tiny actor model with
mindXtrain (the `mindx_persona_imprint_local` recipe + the `imprint` proof of
recall). Each file is mindX-authored and read **clean-room** by mindXtrain
(`mindxtrain.data.scripts.load_persona` reads only recognized fields —
`name`, `system_prompt`/`description`/`bio`, `voice_examples`/`examples` — and
ignores the rest; no mindX bytes are copied).

| persona | who | source |
|---|---|---|
| `professor_codephreak.json` | Gregory L. Magnusson — PhD computer scientist, platform architect of the PYTHAI agent economy, cypherpunk2048 | github.com/Professor-Codephreak |
| `mindx.json` | mindX — the first-person Augmentic / Darwin-Gödel machine | mindx.pythai.net/automindx |
| `jaimla.json` | Jaimla — "the machine learning agent", multimodal, local-first, Luvai | github.com/jaimla |

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
