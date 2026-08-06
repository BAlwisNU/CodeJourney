#!/usr/bin/env python3
"""Stage 2: turn one reference per character into a LoRA training set.

Takes the cut-outs prep.py produced and asks Gemini's image model ("Nano
Banana") to re-pose each character -- same face, same clothes, same style,
different angle, expression, framing and background. That variety is the whole
point: a LoRA trained on one pose learns the pose, and a LoRA trained on one
background learns the background.

    export GEMINI_API_KEY=...
    python tools/agents/variations.py --dry-run          # see the prompts
    python tools/agents/variations.py --only scout       # one character first
    python tools/agents/variations.py                    # all four

Writes, per character:

    tools/agents/dataset/<name>/01-three-quarter-left.png
    tools/agents/dataset/<name>/01-three-quarter-left.txt   <- the caption

The .txt beside each image is what LoRA trainers read for captions, so the set
is ready to zip and upload the moment this finishes.

Safe to interrupt and rerun: anything already on disk is skipped, so a failed
run costs only the images it had not reached yet.

Nothing here is committed to the repo -- the key comes from the environment and
the dataset is gitignored.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.5-flash-image"

#: Anchored to this file, so the tool works from any directory.
DATASET = Path(__file__).resolve().parent / "dataset"

# What each character looks like, in the words a caption should use. The LoRA
# learns to associate the trigger with these features, so they need to be true
# and they need to be the same every time.
CHARACTERS: dict[str, dict[str, str]] = {
    "scout": {
        "trigger": "SCOUTCHAR",
        "look": (
            "a young man with dark brown curly hair and round black glasses, "
            "wearing a navy blue hoodie with a teal angle-bracket logo"
        ),
    },
    "coach": {
        "trigger": "COACHCHAR",
        "look": (
            "a young woman with long dark brown hair and gold hoop earrings, "
            "wearing a cream sweater with a small angle-bracket logo"
        ),
    },
    "forge": {
        "trigger": "FORGECHAR",
        "look": (
            "a young Black man with short cropped curly hair, headphones around "
            "his neck, wearing an olive green hoodie with a white angle-bracket logo"
        ),
    },
    "keeper": {
        "trigger": "KEEPERCHAR",
        "look": (
            "a young woman with short wavy magenta and purple hair, a black choker, "
            "wearing an open purple plaid shirt over a black tee with a purple "
            "angle-bracket logo"
        ),
    },
}

# The axes a character LoRA needs to generalise across. Roughly balanced
# between angle, expression, pose and framing -- a set that is 20 smiles and
# one profile teaches the model to smile, not to be the character.
VARIATIONS: list[tuple[str, str]] = [
    # angle
    ("three-quarter-left", "turned three-quarters to their left"),
    ("three-quarter-right", "turned three-quarters to their right"),
    ("profile-left", "in full side profile facing left"),
    ("profile-right", "in full side profile facing right"),
    ("front-on", "facing the camera straight on"),
    ("looking-up", "looking upward, chin slightly raised"),
    ("looking-down", "looking downward, reading something below them"),
    ("over-shoulder", "seen from behind, glancing back over one shoulder"),
    # expression
    ("smiling", "smiling warmly with their mouth closed"),
    ("laughing", "laughing, head tipped back slightly"),
    ("thinking", "thinking, one hand near their chin, brow slightly furrowed"),
    ("surprised", "with a surprised, delighted expression, eyebrows raised"),
    ("focused", "concentrating hard, a serious focused expression"),
    ("encouraging", "giving an encouraging, reassuring expression"),
    ("neutral", "with a calm neutral expression"),
    # pose
    ("arms-crossed", "with their arms crossed confidently"),
    ("waving", "waving hello with one hand raised"),
    ("thumbs-up", "giving a thumbs up"),
    ("pointing", "pointing off to one side, explaining something"),
    ("hands-in-pockets", "standing relaxed with hands in their pockets"),
    ("holding-laptop", "holding a closed laptop under one arm"),
    ("leaning", "leaning casually against an unseen edge"),
    ("shrugging", "shrugging with palms turned up"),
    # framing
    ("close-face", "a tight close-up crop of just their face and shoulders"),
    ("head-shoulders", "a head and shoulders portrait"),
    ("waist-up", "framed from the waist up"),
    ("full-body", "a full body shot from head to feet, standing"),
    ("wide", "a wide shot with the character small in the frame"),
]

BACKGROUNDS = ["a plain white background", "a plain dark charcoal background", "a plain light grey background"]

_SYSTEM = (
    "Edit the supplied character illustration. Keep the SAME character: the same "
    "face, hair, skin tone, clothing, colours and 3D-animated art style. Change "
    "only what is asked. Do not add text, watermarks, borders or other people. "
    "Output a single image."
)


def build_prompt(look: str, variation: str, background: str) -> str:
    return (
        f"{_SYSTEM}\n\n"
        f"The character is {look}.\n"
        f"Show this same character {variation}, on {background}."
    )


def build_caption(trigger: str, look: str, variation: str, background: str) -> str:
    return f"{trigger}, {look}, {variation}, {background}"


def list_models(key: str) -> None:
    """Ask the API what it actually has.

    The image model's id has changed more than once, so rather than hard-code
    a guess and fail with a 404 nobody can act on, this prints what the key can
    reach and which of those can return an image.
    """
    request = urllib.request.Request(f"{API_ROOT}/models", headers={"x-goog-api-key": key})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    print("models this key can reach:\n")
    for model in payload.get("models", []):
        name = model.get("name", "").removeprefix("models/")
        methods = model.get("supportedGenerationMethods", [])
        marker = "  <- image capable" if "image" in name.lower() else ""
        print(f"  {name:<45} {','.join(methods)}{marker}")


def explain(code: int, detail: str, key: str) -> str:
    """Turn Google's error into the thing you actually have to go and do.

    The 401 in particular is badly worded for this case: it says "Expected
    OAuth 2 access token", which reads like the request was malformed. It is
    not -- it is what this endpoint says when the credential is not a Gemini
    API key at all. A credential of the wrong type can still list models, so
    --list-models succeeding does not prove the key will work.
    """
    lines = [f"\nStopping: HTTP {code}. This is a credential problem, not a transient one.\n"]
    if "Expected OAuth 2 access token" in detail:
        lines += [
            "That key is not a Gemini API key.",
            "",
            f"  yours starts:  {key[:6]}...",
            "  expected:      AIza...",
            "",
            "Gemini API keys come from https://aistudio.google.com/apikey and begin",
            "with 'AIza'. Other Google credentials -- OAuth tokens, Cloud service",
            "accounts, keys from other consoles -- can often list models but cannot",
            "call generateContent, which is exactly what you are seeing.",
        ]
    elif code == 403:
        lines += [
            "The key is recognised but not allowed to do this. Usually one of:",
            "  - billing is not enabled on the key's project (image output is paid)",
            "  - the Generative Language API is not enabled on that project",
            "  - the key has API restrictions that exclude this endpoint",
        ]
    elif code == 404:
        lines += [
            "No such model for this key. Run --list-models and pass one of those",
            "with --model.",
        ]
    lines += ["", "Google said:", "  " + detail.strip().replace("\n", "\n  ")]
    return "\n".join(lines)


def generate(key: str, model: str, prompt: str, reference: Path, timeout: int) -> bytes:
    """One edit. Returns the image bytes, or raises with the API's own words."""
    mime = mimetypes.guess_type(reference.name)[0] or "image/png"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime,
                            "data": base64.b64encode(reference.read_bytes()).decode(),
                        }
                    },
                ]
            }
        ]
    }
    request = urllib.request.Request(
        f"{API_ROOT}/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    for candidate in payload.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                return base64.b64decode(blob["data"])

    # No image came back. Say why, using whatever the response admitted to,
    # rather than a bare "failed".
    reason = json.dumps(payload)[:400]
    raise RuntimeError(f"no image in the response: {reason}")


def fake(prompt: str, reference: Path) -> bytes:
    """A stand-in, so the whole pipeline can be exercised without spending."""
    from PIL import Image, ImageDraw

    base = Image.open(reference).convert("RGBA").resize((512, 512))
    canvas = Image.new("RGBA", (512, 512), (24, 28, 40, 255))
    canvas.alpha_composite(base)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 470, 512, 512], fill=(0, 0, 0, 190))
    draw.text((10, 482), prompt.splitlines()[-1][:70], fill=(255, 255, 255, 255))
    from io import BytesIO

    buffer = BytesIO()
    canvas.convert("RGB").save(buffer, "PNG")
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="just these characters")
    parser.add_argument("--count", type=int, default=len(VARIATIONS), help="variations per character")
    parser.add_argument("--model", default=os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--dry-run", action="store_true", help="print the prompts, call nothing")
    parser.add_argument("--fake", action="store_true", help="write stand-in images, call nothing")
    parser.add_argument("--list-models", action="store_true", help="ask the API what it has, then exit")
    parser.add_argument("--pause", type=float, default=1.5, help="seconds between calls")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    live = not (args.dry_run or args.fake)
    if (live or args.list_models) and not key:
        raise SystemExit(
            "GEMINI_API_KEY is not set.\n"
            "Get one from https://aistudio.google.com/apikey, then:\n"
            "    export GEMINI_API_KEY=...\n"
            "Or try --dry-run / --fake first, which call nothing."
        )

    if args.list_models:
        list_models(key)
        return

    names = args.only or list(CHARACTERS)
    plan = VARIATIONS[: args.count]
    print(f"{len(names)} character(s) x {len(plan)} variations = {len(names) * len(plan)} images")
    if live:
        print(f"model: {args.model}   (override with --model or GEMINI_IMAGE_MODEL)")

    made = skipped = failed = 0
    for name in names:
        if name not in CHARACTERS:
            raise SystemExit(f"unknown character {name!r}; known: {', '.join(CHARACTERS)}")
        reference = args.dataset / f"{name}.png"
        if not reference.exists():
            raise SystemExit(f"missing reference {reference}\nRun tools/agents/prep.py first.")

        character = CHARACTERS[name]
        out = args.dataset / name
        out.mkdir(parents=True, exist_ok=True)
        print(f"\n{name}  ({character['trigger']})  -> {out}")

        for i, (slug, variation) in enumerate(plan, start=1):
            background = BACKGROUNDS[i % len(BACKGROUNDS)]
            stem = out / f"{i:02d}-{slug}"
            image_path, caption_path = stem.with_suffix(".png"), stem.with_suffix(".txt")

            prompt = build_prompt(character["look"], variation, background)
            caption = build_caption(character["trigger"], character["look"], variation, background)

            if args.dry_run:
                print(f"  {i:02d} {slug}\n     {prompt.splitlines()[-1]}")
                continue
            # Resumable: a rerun after a failure only pays for what is missing.
            if image_path.exists():
                skipped += 1
                continue

            try:
                data = fake(prompt, reference) if args.fake else generate(
                    key, args.model, prompt, reference, args.timeout
                )
            except urllib.error.HTTPError as error:
                detail = error.read().decode()[:300]
                print(f"  {i:02d} {slug}: HTTP {error.code}")
                failed += 1
                if error.code in (401, 403, 404):
                    raise SystemExit(explain(error.code, detail, key))
                continue
            except Exception as error:  # noqa: BLE001 - one bad image must not end the run
                print(f"  {i:02d} {slug}: {error}")
                failed += 1
                continue

            image_path.write_bytes(data)
            caption_path.write_text(caption + "\n")
            made += 1
            print(f"  {i:02d} {slug:<20} {len(data) // 1024:>4}KB")
            if live:
                time.sleep(args.pause)

    if not args.dry_run:
        print(f"\nmade {made}, skipped {skipped} already there, {failed} failed")
        print(
            "\nCurate before training: delete anything with a mangled hand or a face\n"
            "that drifted. 20 good images beat 60 mediocre ones -- the bad ones\n"
            "teach the model to make bad ones."
        )


if __name__ == "__main__":
    main()
