import os
import sys
from typing import List

from PIL import Image

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA_ROOT = os.path.join(ROOT, "Data", "chest_xray")
SPLITS = ["train", "val", "test"]
CLASSES = ["NORMAL", "PNEUMONIA"]
IMG_EXTS = (".jpg", ".jpeg", ".png")


def find_corrupt() -> List[str]:
    bad = []
    for split in SPLITS:
        for cls in CLASSES:
            d = os.path.join(DATA_ROOT, split, cls)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if not f.lower().endswith(IMG_EXTS):
                    continue
                path = os.path.join(d, f)
                try:
                    with Image.open(path) as img:
                        img.verify()  # verify file integrity
                except Exception:
                    bad.append(path)
    return bad


def main():
    bad = find_corrupt()
    out_path = os.path.join(ROOT, "ml", "pneumonia", "eda", "corrupt_images.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for p in bad:
            f.write(p + "\n")

    print("Corrupt images found:", len(bad))
    print("List saved to:", out_path)

    if len(bad) > 0:
        print("\nSample:")
        for p in bad[:10]:
            print(" -", p)


if __name__ == "__main__":
    main()