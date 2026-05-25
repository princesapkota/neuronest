import os
import sys
from pathlib import Path
from collections import Counter
from PIL import Image

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

# Your dataset root (as per screenshot)
DATA_ROOT = os.path.join(ROOT, "Data", "fracture")

IMG_EXTS = (".jpg", ".jpeg", ".png")


def map_class_from_folder(folder_name: str) -> str:
    """
    Uses ONLY the immediate class folder name.
    Expected:
      fractured
      not fractured
    """
    name = folder_name.strip().lower()
    if name in ["fractured", "fracture", "fx", "broken"]:
        return "FRACTURE"
    if name in ["not fractured", "not_fractured", "nonfractured", "non fractured", "normal", "no fracture"]:
        return "NORMAL"
    return "UNKNOWN"


def main():
    if not os.path.isdir(DATA_ROOT):
        raise FileNotFoundError(f"Dataset folder not found: {DATA_ROOT}")

    total = 0
    split_counter = Counter()
    class_counter = Counter()
    mode_counter = Counter()
    size_counter = Counter()
    corrupt = []
    unknown_examples = []

    for split in ["train", "val", "test"]:
        split_dir = os.path.join(DATA_ROOT, split)
        if not os.path.isdir(split_dir):
            continue

        for class_dir in os.listdir(split_dir):
            class_path = os.path.join(split_dir, class_dir)
            if not os.path.isdir(class_path):
                continue

            mapped = map_class_from_folder(class_dir)
            if mapped == "UNKNOWN":
                unknown_examples.append(class_path)

            for p in Path(class_path).rglob("*"):
                if p.is_file() and p.suffix.lower() in IMG_EXTS:
                    total += 1
                    split_counter[split] += 1
                    class_counter[mapped] += 1
                    try:
                        with Image.open(p) as img:
                            mode_counter[img.mode] += 1
                            size_counter[img.size] += 1
                    except Exception:
                        corrupt.append(str(p))

    print("Dataset root:", DATA_ROOT)
    print("Total images:", total)
    print("Split counts:", dict(split_counter))
    print("Class distribution:", dict(class_counter))
    print("Image modes:", dict(mode_counter))
    print("Most common sizes:", size_counter.most_common(5))
    print("Corrupt images:", len(corrupt))

    if unknown_examples:
        print("\nUNKNOWN class folders detected (first 10):")
        for u in unknown_examples[:10]:
            print(" -", u)
        print("\nRename folders or update map_class_from_folder() mapping.")

    if corrupt:
        print("\nExample corrupt files (first 10):")
        for c in corrupt[:10]:
            print(" -", c)

    print("\nInspection complete.")


if __name__ == "__main__":
    main()