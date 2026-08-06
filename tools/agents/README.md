# Training a FLUX LoRA for the CodeJourney agents

The goal: generate the same four characters, forever, in any pose, on any
background, at any size — without redrawing them and without them drifting into
four different people.

Prompting alone will not do this. A LoRA will.

## The thing everyone gets wrong

**One group illustration is not a training set.** A character LoRA wants roughly
15–30 images *per character*: different angles, expressions, framings,
lighting. Train on one image and the model learns that image — the exact pose,
the exact crop, the white backdrop — instead of the character.

So there are three stages, and the first one is the one people skip.

---

## Where the files live

    tools/agents/source/all.png      the master illustration (not shipped)
    tools/agents/dataset/<name>.png  1024px with alpha, the training seeds
    apps/web/public/agents/*.webp    what the landing page serves

Masters stay out of `public/` on purpose: everything in there is copied
verbatim into the build and served to every visitor, and the source PNG is
2MB against 161KB for the WebP. Nothing in `public/agents/` is hand-edited --
rerun `prep.py` and it is all regenerated.

## Stage 1 — references (free, local, done)

Turn the group shot into four clean, cut-out, square references.

```bash
python tools/agents/prep.py tools/agents/source/all.png \
    --names scout coach forge keeper
```

Writes:

- `apps/web/public/agents/<name>.webp` — 640px, for the landing page tabs
- `tools/agents/dataset/<name>.png` — 1024px with alpha, the training seed

Notes:

- The backdrop is removed by flooding inward from the border, so a white
  background goes but a **cream jumper does not**. If a character still comes
  out too small, the script says so and backs the tolerance off automatically.
- The joins are found automatically. The characters in a posed group *touch*,
  so there is no empty column to look for -- instead each character is a hump
  in the column-density profile and the joins are the troughs between them. On
  the current illustration it finds x=413, 759, 1122; equal quarters would have
  cut through an arm. Override with `--bounds 0,0.26 0.24,0.52 ...` if needed.
- Any crescent of a neighbour left inside a band is removed as a disconnected
  piece. Measured on the real art those slivers were 0.1-0.3% of the figure
  while a held laptop and a belt chain both came back joined to their owner.
- `--keep-background` skips the cut-out entirely.

## Stage 2 — build the set (this is the work)

`variations.py` re-poses each reference through Gemini's image model ("Nano
Banana"): same face, same clothes, same style, different angle, expression,
framing and background.

```bash
export GEMINI_API_KEY=...        # https://aistudio.google.com/apikey

python tools/agents/variations.py --dry-run           # see the prompts, spend nothing
python tools/agents/variations.py --fake              # exercise the pipeline, spend nothing
python tools/agents/variations.py --only scout        # one character, ~28 images
python tools/agents/variations.py                     # all four, ~112 images
```

Writes `dataset/<name>/01-three-quarter-left.png` and a matching `.txt`
caption beside it, which is the layout LoRA trainers expect — zip the folder
and upload.

It is **resumable**: anything already on disk is skipped, so an interrupted run
costs only the images it had not reached. A 401/403/404 stops the run
immediately rather than burning through 112 identical failures; anything else
is logged and skipped.

The 28 variations are deliberately balanced across four axes — angle,
expression, pose, framing — because a set that is twenty smiles and one profile
teaches the model to smile rather than to be the character. Backgrounds rotate
through plain white, charcoal and grey so it does not learn a backdrop either.

If the model id has moved on:

```bash
python tools/agents/variations.py --list-models        # ask the key what it can reach
python tools/agents/variations.py --model <id>         # or set GEMINI_IMAGE_MODEL
```

**Then curate.** This is not optional. Delete anything with a mangled hand, a
drifted face, or a background that came back busy. 20 good images beat 60
mediocre ones, because the bad ones teach the model to make bad ones.

## Stage 3 — train

**fal.ai** (fastest to get going):

```bash
export FAL_KEY=...            # never commit this
# model: fal-ai/flux-lora-fast-training
# input: a zip of the captioned images, plus the trigger word
# time:  ~5 minutes    cost: a few dollars per character
```

**Replicate** (`ostris/flux-dev-lora-trainer`) is equivalent and takes a zip the
same way. **Astria** and **Scenario.gg** are more hand-holding, more per month.

Sensible starting points: 1000–1500 steps, learning rate 1e-4, and *do not*
train on more than ~30 images for a single character — more is not better here.

Train **one LoRA per character** rather than one for all four. Multi-subject
LoRAs bleed features between subjects, and you cannot then adjust one character
without retraining the rest.

## Stage 4 — generate

With the trained LoRA, generate the assets the site wants:

- portraits on transparent/dark backgrounds for the coach tabs
- the group shot for the "Meet all four" tab
- later: empty-state art, celebration art, dashboard illustrations

Run the results back through `prep.py --keep-background` to square and resize
them for the web.

---

## Costs, roughly

| | |
|---|---|
| Stage 1 | free |
| Stage 2 | ~100 images through an image API — single-digit dollars |
| Stage 3 | ~$2–5 per character, one time |
| Stage 4 | pennies per image |

Under $30 all in, and after that the characters are yours to generate forever.

## What is deliberately not here

No API keys, and no code that calls a paid service. Keys go in the environment;
if a generation step gets scripted, it reads `FAL_KEY` (or equivalent) from
there and never from the repo.
