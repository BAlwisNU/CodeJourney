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

## Stage 1 — references (free, local, done)

Turn the group shot into four clean, cut-out, square references.

```bash
# save the group illustration first, then:
python tools/agents/prep.py apps/web/public/agents/all.png \
    --names scout coach forge keeper
```

Writes:

- `apps/web/public/agents/<name>.webp` — 640px, for the landing page tabs
- `tools/agents/dataset/<name>.png` — 1024px with alpha, the training seed

Notes:

- The backdrop is removed by flooding inward from the border, so a white
  background goes but a **cream jumper does not**. If a character still comes
  out too small, the script says so and backs the tolerance off automatically.
- If the characters are not evenly spaced, pass explicit bands:
  `--bounds 0,0.26 0.24,0.52 0.5,0.76 0.74,1`
- `--keep-background` skips the cut-out entirely.

## Stage 2 — build the set (this is the work)

Take each 1024px reference and produce 20–30 variations of that character.
Use a model that can hold a character across images:

- **Gemini image editing ("Nano Banana")** — best at "same character, new pose,
  keep the face". Has a real API, so this stage can be scripted.
- **Midjourney `--cref`** — excellent results, no public API, so it's manual.
- **OpenAI `gpt-image-1`** — accepts reference images, has an API.

Ask for variety on the axes a LoRA needs to generalise:

    three-quarter view · profile · looking up · looking down · smiling ·
    thinking · arms crossed · waving · close crop on the face · full body ·
    plain dark background · plain light background

Then curate hard. **20 good images beat 60 mediocre ones** — anything with a
mangled hand or a wandering face teaches the model to produce those.

Put them in `tools/agents/dataset/<name>/` and caption each one with a unique
trigger word, e.g. `SCOUTCHAR, a young man with dark curly hair and glasses,
three-quarter view, dark background`.

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
