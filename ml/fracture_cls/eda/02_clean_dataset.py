import os
import sys
from pathlib import Path
from PIL import Image

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA_ROOT = os.path.join(ROOT, "Data", "fracture")
IMG_EXTS = (".jpg", ".jpeg", ".png")


def main():
    removed = 0
    checked = 0

    for p in Path(DATA_ROOT).rglob("*"):
        if not p.is_file():
            continue

        if p.suffix.lower() not in IMG_EXTS:
            # remove non-image files 
            continue

        checked += 1
        try:
            with Image.open(p) as img:
                img.verify()  # quick integrity check
        except Exception:
            try:
                os.remove(p)
                removed += 1
                print("Removed corrupt:", str(p))
            except Exception:
                print("Failed to remove:", str(p))

    print("Checked images:", checked)
    print("Removed corrupt images:", removed)
    print("Done.")


if __name__ == "__main__":
    main()