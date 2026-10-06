"""Make display copies of the product photos with a consistent white background.

74 of the 102 supplied photos sit on a black background (they look like cut-out
images saved without transparency); the rest are on white. On the navy-and-white
site that mix looks uneven, so this script writes copies to data/products_web/
where the black background is replaced with white. The supplied images in
data/products/ are never modified.

How: starting from the image border, flood-fill only pixels that are almost
pure black (every channel <= 14) and connected to the border, so dark navy
garments (which are clearly lighter than pure black) are left alone.
Background also shows through the gaps between sleeves and body, which don't
touch the border; those are filled too, but only pure-black areas that are
tall and narrow and sit towards the left or right side. Black details inside
crests and logos are compact and central, so they are kept. Pixels just next
to the filled area are blended towards white to avoid a dark halo.

Run from the backend folder (needs Pillow):
    python prepare_images.py
"""

import sys
from collections import deque

from PIL import Image, ImageFilter

from db import DATA_DIR, PRODUCTS_DIR

OUT_DIR = DATA_DIR / "products_web"
BLACK = 14          # max channel value treated as background black
HALO = 60           # pixels next to the background darker than this get lightened
MIN_EDGE_BLACK = 0.5  # only treat images whose border is mostly black


def edge_pixels(w: int, h: int):
    for x in range(w):
        yield x, 0
        yield x, h - 1
    for y in range(h):
        yield 0, y
        yield w - 1, y


def fill_sleeve_gaps(px, mask, w: int, h: int) -> None:
    """Also mark enclosed pure-black regions shaped like a sleeve-body gap."""
    seen = bytearray(w * h)
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0 * w + x0] or mask[x0, y0] or max(px[x0, y0]) > BLACK:
                continue
            region, queue = [], deque([(x0, y0)])
            seen[y0 * w + x0] = 1
            while queue:
                x, y = queue.popleft()
                region.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and not mask[nx, ny] and max(px[nx, ny]) <= BLACK:
                        seen[ny * w + nx] = 1
                        queue.append((nx, ny))
            xs, ys = [x for x, _ in region], [y for _, y in region]
            rw, rh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            cx = (min(xs) + max(xs)) / 2 / w
            if len(region) >= 150 and rh >= 2.5 * rw and rh >= 0.12 * h and (cx < 0.32 or cx > 0.68):
                for x, y in region:
                    mask[x, y] = 255


def whiten_background(im: Image.Image) -> Image.Image | None:
    im = im.convert("RGB")
    w, h = im.size
    px = im.load()
    border = list(edge_pixels(w, h))
    if sum(1 for x, y in border if max(px[x, y]) <= BLACK) / len(border) < MIN_EDGE_BLACK:
        return None  # already a light background

    bg = Image.new("L", (w, h), 0)
    mask = bg.load()
    queue = deque((x, y) for x, y in border if max(px[x, y]) <= BLACK)
    for x, y in queue:
        mask[x, y] = 255
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not mask[nx, ny] and max(px[nx, ny]) <= BLACK:
                mask[nx, ny] = 255
                queue.append((nx, ny))

    fill_sleeve_gaps(px, mask, w, h)

    # Soften the boundary: a slightly grown mask, applied only to dark pixels, removes the black fringe.
    grown = bg.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    g = grown.load()
    out = im.copy()
    o = out.load()
    for y in range(h):
        for x in range(w):
            if mask[x, y]:
                o[x, y] = (255, 255, 255)
            elif g[x, y] and max(px[x, y]) < HALO:
                a = g[x, y] / 255
                r, gg, b = px[x, y]
                o[x, y] = tuple(round(c + (255 - c) * a) for c in (r, gg, b))
    return out


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    changed = copied = 0
    for src in sorted(PRODUCTS_DIR.glob("*.jpg")):
        dst = OUT_DIR / src.name
        result = whiten_background(Image.open(src))
        if result is None:
            dst.write_bytes(src.read_bytes())
            copied += 1
        else:
            result.save(dst, quality=92)
            changed += 1
    print(f"{changed} backgrounds whitened, {copied} copied unchanged -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
