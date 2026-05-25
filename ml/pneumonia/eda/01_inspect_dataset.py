import os
import sys
from collections import Counter
from typing import Dict, Tuple

from PIL import Image

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA_ROOT = os.path.join(ROOT, "Data", "chest_xray")
SPLITS = ["train", "val", "test"]
CLASSES = ["NORMAL", "PNEUMONIA"]
IMG_EXTS = (".jpg", ".jpeg", ".png")


def count_images(split_dir: str) -> Dict[str, int]:
    counts = {}
    for cls in CLASSES:
        p = os.path.join(split_dir, cls)
        if not os.path.isdir(p):
            counts[cls] = 0
            continue
        counts[cls] = sum(1 for f in os.listdir(p) if f.lower().endswith(IMG_EXTS))
    return counts


def scan_sizes_and_modes(split_dir: str, max_files_per_class: int = 300) -> Tuple[Counter, Counter]:
    size_counter = Counter()
    mode_counter = Counter()

    for cls in CLASSES:
        cls_dir = os.path.join(split_dir, cls)
        if not os.path.isdir(cls_dir):
            continue

        files = [f for f in os.listdir(cls_dir) if f.lower().endswith(IMG_EXTS)]
        files = files[:max_files_per_class]

        for f in files:
            path = os.path.join(cls_dir, f)
            try:
                with Image.open(path) as img:
                    size_counter[img.size] += 1  # (W,H)
                    mode_counter[img.mode] += 1  # L/RGB/etc
            except Exception:
                mode_counter["CORRUPT"] += 1

    return size_counter, mode_counter


def main():
    print("Dataset root:", DATA_ROOT)
    for split in SPLITS:
        split_dir = os.path.join(DATA_ROOT, split)
        if not os.path.isdir(split_dir):
            print(f"[MISSING] {split_dir}")
            continue

        counts = count_images(split_dir)
        total = sum(counts.values())
        print(f"\n=== {split.upper()} ===")
        print("Counts:", counts, "| Total:", total)

        sizes, modes = scan_sizes_and_modes(split_dir, max_files_per_class=300)
        top_sizes = sizes.most_common(5)
        top_modes = modes.most_common(5)

        print("Top image sizes (W,H):", top_sizes)
        print("Top modes:", top_modes)

        if modes.get("CORRUPT", 0) > 0:
            print("WARNING: Corrupt images detected:", modes["CORRUPT"])

    print("\nDone.")


if __name__ == "__main__":
    main()