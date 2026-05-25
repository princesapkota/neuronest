"""
Fixes the fracture dataset's broken train/val/test split.

Problem: val and test were subsets of train (6680 duplicate images),
causing the model to score 1.0 on "validation" data it already trained on.

Fix: pool all 3883 unique images (by MD5 hash), then create a
stratified 70 / 15 / 15 split in Data/fracture_clean/.

Run once, then retrain with DATA_ROOT pointing at fracture_clean.
"""

import hashlib
import os
import random
import shutil
from collections import defaultdict
from pathlib import Path

ROOT      = r"C:\Users\ACER\Desktop\NeuroNest"
SRC_ROOT  = os.path.join(ROOT, "Data", "fracture")
DST_ROOT  = os.path.join(ROOT, "Data", "fracture_clean")
IMG_EXTS  = (".jpg", ".jpeg", ".png")

LABEL_MAP = {
    "fractured":     "FRACTURE",
    "not fractured": "NORMAL",
}

SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED = 42

# ── 1. Hash every image, keep first occurrence per hash ──────────────────────
print("Scanning for unique images …")
seen: dict[str, tuple[str, str]] = {}   # hash -> (src_path, label)
dupes = 0

for split in ["train", "val", "test"]:
    for folder, label in LABEL_MAP.items():
        d = os.path.join(SRC_ROOT, split, folder)
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.lower().endswith(IMG_EXTS):
                continue
            p = os.path.join(d, fname)
            with open(p, "rb") as fh:
                h = hashlib.md5(fh.read()).hexdigest()
            if h in seen:
                dupes += 1
            else:
                seen[h] = (p, label)

print(f"  Unique images : {len(seen)}")
print(f"  Duplicates    : {dupes}")

# group by label
by_label: dict[str, list[tuple[str, str]]] = defaultdict(list)
for h, (p, lbl) in seen.items():
    by_label[lbl].append((h, p))

for lbl, items in by_label.items():
    print(f"  {lbl}: {len(items)}")

# ── 2. Stratified split ───────────────────────────────────────────────────────
rng = random.Random(SEED)

splits: dict[str, list[tuple[str, str, str]]] = {"train": [], "val": [], "test": []}

for lbl, items in by_label.items():
    rng.shuffle(items)
    n     = len(items)
    n_val  = int(n * SPLIT_RATIOS["val"])
    n_test = int(n * SPLIT_RATIOS["test"])
    n_train = n - n_val - n_test

    for h, p in items[:n_train]:
        splits["train"].append((p, lbl, h))
    for h, p in items[n_train: n_train + n_val]:
        splits["val"].append((p, lbl, h))
    for h, p in items[n_train + n_val:]:
        splits["test"].append((p, lbl, h))

print("\nNew split sizes:")
for sp, items in splits.items():
    from collections import Counter
    lc = Counter(lbl for _, lbl, _ in items)
    print(f"  {sp}: {len(items)} total  {dict(lc)}")

# ── 3. Copy images to DST_ROOT ────────────────────────────────────────────────
FOLDER_MAP = {"FRACTURE": "fractured", "NORMAL": "not fractured"}

print(f"\nWriting to: {DST_ROOT}")
if os.path.exists(DST_ROOT):
    shutil.rmtree(DST_ROOT)

copied = 0
for sp, items in splits.items():
    for src_path, lbl, img_hash in items:
        folder = FOLDER_MAP[lbl]
        dst_dir = os.path.join(DST_ROOT, sp, folder)
        os.makedirs(dst_dir, exist_ok=True)

        # use hash as filename to avoid collisions
        ext     = Path(src_path).suffix.lower()
        dst_path = os.path.join(dst_dir, img_hash[:16] + ext)
        shutil.copy2(src_path, dst_path)
        copied += 1

print(f"Copied {copied} images.")
print("Done. Point DATA_ROOT in training/eval to:", DST_ROOT)
print("Retrain the model before evaluating — the old checkpoint is tainted.")


if __name__ == "__main__":
    pass
