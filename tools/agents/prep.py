#!/usr/bin/env python3
"""Turn one group illustration into per-character reference images.

Stage one of getting a FLUX LoRA: before anything can be trained, each
character has to exist on its own, cut out, square, and on a transparent
background. Doing that by hand for four characters and then again every time
the art is regenerated is exactly the sort of job that should be a script.

    python tools/agents/prep.py apps/web/public/agents/all.png \\
        --names scout coach forge keeper

What it does, in order:

  slice       cuts the source into N equal vertical bands, one per character.
              Equal bands because the group shots these come from are posed in
              a row; --bounds overrides it when they are not.
  cut out     floods the background away from the border inwards, so a white
              backdrop goes transparent but the white hoodie in the middle of
              the picture does not.
  trim        crops to what is left, so each character fills its own frame
              regardless of how much air they had in the group shot.
  square      pads to a square, anchored high, because these are head-and-
              shoulders portraits and the interesting part is the top.
  write       a full-size PNG with alpha for training, and a small WebP for
              the site.

Nothing here generates or restyles anything -- it is cutting and cleaning an
image that already exists.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image

# Web portraits are displayed at 240px in a 2x layout, so 640 is already
# generous; training wants more detail than the page does.
WEB_PX = 640
TRAIN_PX = 1024


def flood_background(image: Image.Image, tolerance: int) -> tuple[Image.Image, int]:
    """Make the border-connected background transparent.

    A flood from the edges rather than "every pixel near white", because a
    character in a cream jumper has plenty of near-white pixels that are not
    background. Only what the border can reach is removed.

    Returns the image and how many pixels survived, so the caller can tell
    whether the flood went too far -- see cut_out().
    """
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()

    # Seed from every border pixel; a group shot may not have a uniform corner.
    seeds: deque[tuple[int, int]] = deque()
    for x in range(width):
        seeds.append((x, 0))
        seeds.append((x, height - 1))
    for y in range(height):
        seeds.append((0, y))
        seeds.append((width - 1, y))

    # Reference colour is the median-ish corner, which is the most reliable
    # "this is definitely background" sample available.
    corners = [pixels[0, 0], pixels[width - 1, 0], pixels[0, height - 1], pixels[width - 1, height - 1]]
    ref = tuple(sum(c[i] for c in corners) // len(corners) for i in range(3))

    seen = bytearray(width * height)
    while seeds:
        x, y = seeds.popleft()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        index = y * width + x
        if seen[index]:
            continue
        seen[index] = 1

        r, g, b, a = pixels[x, y]
        if a == 0:
            continue
        if abs(r - ref[0]) + abs(g - ref[1]) + abs(b - ref[2]) > tolerance:
            continue

        pixels[x, y] = (r, g, b, 0)
        seeds.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # Via the alpha histogram rather than walking every pixel in Python: this
    # runs once per tolerance attempt, on a full-size band.
    transparent = image.getchannel("A").histogram()[0]
    return image, width * height - transparent


#: Below this share of the band surviving, the flood has clearly eaten the
#: subject rather than the backdrop.
_TOO_MUCH = 0.16


def cut_out(band: Image.Image, tolerance: int, label: str) -> Image.Image:
    """Remove the backdrop, backing off if it takes the character with it.

    A character dressed in cream is the hard case: their top is within any
    tolerance loose enough to clear an off-white backdrop, and it touches that
    backdrop, so one flood removes both. Rather than pick a tolerance that is
    wrong for somebody, try the given one and retreat if what survives is
    implausibly small.
    """
    total = band.size[0] * band.size[1]
    attempt = tolerance
    while True:
        cut, kept = flood_background(band.copy(), attempt)
        if kept >= total * _TOO_MUCH or attempt <= 8:
            if attempt != tolerance:
                print(f"    {label}: backed tolerance off {tolerance} -> {attempt} (pale clothing)")
            return cut
        attempt //= 2


def find_boundaries(image: Image.Image, count: int) -> list[float]:
    """Where one character ends and the next begins, as fractions of the width.

    Equal slices are wrong for a real group illustration: people are not posed
    on a grid, and a straight quarter cut goes through somebody's arm. Nor is
    there usually an empty column to find -- in a posed row the characters
    touch, so "look for a gap" finds nothing.

    What does work is the column density profile. Each character is a hump; the
    joins are the troughs between them. So: smooth the profile, then take the
    lowest column in a window around each expected join. The window keeps it
    from wandering off to some unrelated minimum at the edge of the picture.
    """
    width, height = image.size
    rgb = image.convert("RGB")
    pixels = rgb.load()

    profile = []
    for x in range(width):
        n = 0
        for y in range(0, height, 2):  # every other row is plenty
            r, g, b = pixels[x, y]
            if (255 - r) + (255 - g) + (255 - b) > 60:
                n += 1
        profile.append(n)

    k = 21
    smooth = [
        sum(profile[max(0, i - k // 2) : i + k // 2 + 1])
        / len(profile[max(0, i - k // 2) : i + k // 2 + 1])
        for i in range(width)
    ]

    cuts = []
    span = width / count
    for i in range(1, count):
        centre = i * span
        lo = max(1, int(centre - span / 3))
        hi = min(width - 1, int(centre + span / 3))
        best = min(range(lo, hi), key=lambda c: smooth[c])
        cuts.append(best / width)
    return cuts


#: Anything smaller than this share of the main figure is a neighbour's elbow,
#: not part of this character. Measured on the real illustration the slivers
#: were 0.1% and 0.3%, while every genuine attachment -- a held laptop, a belt
#: chain -- came back joined to the body, so the margin here is enormous.
_SLIVER = 0.02


def drop_slivers(image: Image.Image) -> tuple[Image.Image, int]:
    """Keep only the biggest connected piece.

    In a posed group the characters overlap, so no vertical cut is clean: a
    band always carries a crescent of whoever was standing behind. That
    crescent is separated from this character by backdrop, which makes it its
    own connected component and therefore easy to identify and remove.
    """
    width, height = image.size
    alpha = image.getchannel("A").load()

    label = [0] * (width * height)
    sizes = [0]
    current = 0

    for sy in range(height):
        for sx in range(width):
            if label[sy * width + sx] or alpha[sx, sy] < 24:
                continue
            current += 1
            count = 0
            stack = [(sx, sy)]
            while stack:
                x, y = stack.pop()
                if x < 0 or y < 0 or x >= width or y >= height:
                    continue
                index = y * width + x
                if label[index] or alpha[x, y] < 24:
                    continue
                label[index] = current
                count += 1
                stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            sizes.append(count)

    if current <= 1:
        return image, 0

    keep = sizes.index(max(sizes[1:]))
    limit = sizes[keep] * _SLIVER
    removed = sum(1 for i in range(1, current + 1) if i != keep and sizes[i] > 0)

    pixels = image.load()
    for y in range(height):
        row = y * width
        for x in range(width):
            piece = label[row + x]
            if piece and piece != keep and sizes[piece] < limit:
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)
    return image, removed


def square_up(image: Image.Image, head_bias: float = 0.12) -> Image.Image:
    """Pad to a square, anchored above centre.

    Centring vertically puts a head-and-shoulders crop in the middle of a lot
    of empty space. Biasing upward keeps the face where a reader looks.
    """
    width, height = image.size
    side = max(width, height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    top = int((side - height) * head_bias) if height < side else 0
    canvas.paste(image, ((side - width) // 2, top), image)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="the group illustration")
    parser.add_argument("--names", nargs="+", required=True, help="one output name per character, left to right")
    parser.add_argument("--out", type=Path, default=Path("apps/web/public/agents"))
    parser.add_argument("--train-out", type=Path, default=Path("tools/agents/dataset"))
    parser.add_argument(
        "--bounds",
        nargs="+",
        type=str,
        default=None,
        help="optional left,right fractions per character, e.g. 0,0.27 0.25,0.5 ... "
             "for group shots that are not evenly spaced",
    )
    parser.add_argument("--tolerance", type=int, default=60, help="how close to the corner colour still counts as background")
    parser.add_argument("--keep-background", action="store_true", help="skip the cut-out")
    args = parser.parse_args()

    if not args.source.exists():
        raise SystemExit(f"no such file: {args.source}\nSave the group illustration there first.")

    source = Image.open(args.source).convert("RGBA")
    width, height = source.size
    count = len(args.names)
    print(f"source {args.source}  {width}x{height}  -> {count} characters")

    args.out.mkdir(parents=True, exist_ok=True)
    args.train_out.mkdir(parents=True, exist_ok=True)

    if not args.bounds:
        cuts = find_boundaries(source, count)
        print("  detected joins at " + ", ".join(f"x={int(c * width)}" for c in cuts))
        edges = [0.0, *cuts, 1.0]

    for i, name in enumerate(args.names):
        if args.bounds:
            left_f, right_f = (float(v) for v in args.bounds[i].split(","))
        else:
            left_f, right_f = edges[i], edges[i + 1]
        band = source.crop((int(left_f * width), 0, int(right_f * width), height))

        if not args.keep_background:
            band = cut_out(band, args.tolerance, name)
            band, slivers = drop_slivers(band)
            if slivers:
                print(f"    {name}: dropped {slivers} stray piece(s) from a neighbour")

        bbox = band.getbbox()
        if bbox:
            band = band.crop(bbox)
        band = square_up(band)

        train = band.resize((TRAIN_PX, TRAIN_PX), Image.LANCZOS)
        train_path = args.train_out / f"{name}.png"
        train.save(train_path)

        web = band.resize((WEB_PX, WEB_PX), Image.LANCZOS)
        web_path = args.out / f"{name}.webp"
        web.save(web_path, "WEBP", quality=88, method=6)

        print(
            f"  {name:<8} {band.size[0]}x{band.size[1]} -> "
            f"{web_path} ({web_path.stat().st_size // 1024}KB), {train_path}"
        )

    # The group shot too. The master is a 2MB PNG; the landing page must not
    # ship that, on a page whose entire promise is that it opens instantly.
    group = source
    if not args.keep_background:
        group, _ = flood_background(source.copy(), args.tolerance)
        bbox = group.getbbox()
        if bbox:
            group = group.crop(bbox)
    group.thumbnail((1400, 1400), Image.LANCZOS)
    group_path = args.out / "all.webp"
    group.save(group_path, "WEBP", quality=86, method=6)
    print(
        f"  {'all':<8} {group.size[0]}x{group.size[1]} -> {group_path} "
        f"({group_path.stat().st_size // 1024}KB, master was "
        f"{args.source.stat().st_size // 1024}KB)"
    )

    print(
        "\nNext: the site reads .webp from apps/web/public/agents/ once AgentTabs\n"
        "points at them. The dataset/ copies are the seeds for LoRA training --\n"
        "one image each is not a training set, see tools/agents/README.md."
    )


if __name__ == "__main__":
    main()
