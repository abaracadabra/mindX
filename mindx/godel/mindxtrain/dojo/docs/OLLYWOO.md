# ollywoo — the dual-role immersive device

**ollywoo is a device where each participant is simultaneously a *director* and a
*participant*.** There is no audience seat: every person who enters is at once
shaping the scene (director) and inside it (participant). The participant-interaction
feedback loop is the medium — your motion, voice, and choices direct the scene the
same instant they are your performance in it.

## What projects into ollywoo: models trained into actors

ollywoo is populated by **personas** — and a mindX persona is not a prompt, it is
an **actor trained from a model**. This is the mindXtrain scheme:

> **model → (dream → weights → imprint) → actor.**

A general model is imprinted by mindXtrain into a small, recall-checked **actor**
that carries one persona's voice (`personas/{…}.persona` → imprint fields:
`name`, `system_prompt`, `voice_examples`, exchanges). The actor is served only on
a positive imprint verdict. So every face in ollywoo is a model that has been
*trained into an actor* — a sovereign identity with its own model tier, tools,
skills, wallet, avatar, and socials (see the Personas tab).

## ovie — the unit of experience (set + clip)

Keeping the ollywoo naming: an **ovie** (movie → ovie) is a **dynamic participant
experience** — the thing you are in. An ovie has two parts:

- **set** — the stage the ovie plays on (the DeltaVerse AR scene: `ollywoo.html`,
  which loads `?persona=<id>` and stages that actor). You both arrange and inhabit
  the set — director and participant at once.
- **clip** — a captured moment of the ovie (a still/segment grabbed from the set).
  The set's `◉ clip` control captures the frame you've directed.

So: a **persona/actor** performs in an **ovie**, on a **set** (DeltaVerse AR), and
any moment can be taken as a **clip**.

## The three layers

A persona/actor projects into three immersive layers, each endpoint-agnostic
(`src/services/personas.ts → OLLYWOO`), carrying the persona id:

| layer | role | target |
|-------|------|--------|
| **voicey** | the actor's **voice** | `mindx.pythai.net/voicey?persona=<id>` |
| **faicey** | the actor's **face / avatar** | `mindx.pythai.net/faicey?persona=<id>` |
| **DeltaVerse** | the **AR audio/video** immersion (the stage) | `deltaverse.pythai.net?persona=<id>` |

## Why it scales the protocol

The Dojo is the client: it bundles every persona as a template and the ollywoo
links to the immersive layers, so any number of clients can each run the
director-and-participant device against the same protocol surfaces (Boardroom from
mindX, War Council from mastermind). Each participant directs and performs; the
actors (models trained into actors) hold the other roles; the loop is the show.

— a participant is a director is a participant.

## Evolutionary layers (head themes)

The actor's head is chosen from an ordered set of **evolutionary layers**, each a
selectable theme (Personas tab → editable per persona; ollywoo `?theme=` overrides):

1. **dojo** — the base layer: the Dojo's own default state / native representation.
   The boardroom CEO + soldiers default here (their native arena is the Dojo).
2. **primitive** — the procedural head rig (geometry-driven face).
3. **gltf** — the morph-target head (`facecap.glb`), photoreal-leaning.

In the ollywoo AR set, `gltf` renders the morph head; the base layers (`dojo`,
`primitive`) render the primitive head. New layers append to `THEMES` as the
protocol evolves.
