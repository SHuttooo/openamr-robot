#!/usr/bin/env python3
"""Clean up a SLAM map (.pgm): erase ISOLATED black dots (lidar noise /
moving objects) while keeping walls. A "dot" = small connected component of
occupied pixels; a "wall" = large component. Components smaller than MIN_SIZE
are removed (repainted as free).

Usage:
    python3 clean_map.py input.pgm output.pgm [MIN_SIZE]
MIN_SIZE default = 12 (pixels). Increase if dots remain; decrease if a real
small wall disappears.
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

OCC_THRESH = 100   # pixel <= 100 => occupied (black)
FREE = 254         # "free" value (white)

src = sys.argv[1]
dst = sys.argv[2]
min_size = int(sys.argv[3]) if len(sys.argv) > 3 else 12

img = np.array(Image.open(src).convert("L"))
occ = img <= OCC_THRESH

# connected components (8-connectivity) of occupied pixels
lbl, n = ndimage.label(occ, structure=np.ones((3, 3)))
sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1))

print(f"Map {img.shape[1]}x{img.shape[0]} | {n} clusters of black pixels")
big = sizes[sizes >= min_size]
small = sizes[sizes < min_size]
print(f"  kept (>= {min_size}px) : {len(big)}  (walls)")
print(f"  erased (< {min_size}px) : {len(small)}  (dots/noise)  total {int(small.sum())} pixels")

out = img.copy()
removed = 0
for i in range(1, n + 1):
    if sizes[i - 1] < min_size:
        out[lbl == i] = FREE
        removed += 1

Image.fromarray(out).save(dst)
# PNG preview for visual check
Image.fromarray(out).save(dst.rsplit(".", 1)[0] + "_apercu.png")
print(f"=> {removed} clusters erased. Cleaned map: {dst}")
print(f"   preview: {dst.rsplit('.', 1)[0]}_apercu.png  (open it to check)")
