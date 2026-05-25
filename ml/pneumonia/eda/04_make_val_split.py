import os
import sys
import random
import shutil

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA_ROOT = os.path.join(ROOT, "Data", "chest_xray")
TRAIN_DIR = os.path.join(DATA_ROOT, "train")
VAL_DIR = os.path.join(DATA_ROOT, "val")

CLASSES = ["NORMAL", "PNEUMONIA"]
IMG_EXTS = (".jpg", ".jpeg", ".png")

VAL_RATIO = 0.10  # 10% of train -> val
SEED = 42


def list_images(folder: str):
    return [f for f in os.listdir(folder) if f.lower().endswith(IMG_EXTS)]


def main():
    random.seed(SEED)

    for cls in CLASSES:
        src = os.path.join(TRAIN_DIR, cls)
        dst = os.path.join(VAL_DIR, cls)

        if not os.path.isdir(src):
            raise FileNotFoundError(f"Missing: {src}")
        os.makedirs(dst, exist_ok=True)

        files = list_images(src)
        n = len(files)
        k = max(1, int(n * VAL_RATIO))

        random.shuffle(files)
        pick = files[:k]

        print(f"{cls}: train={n} -> moving {k} to val")

        moved = 0
        for fname in pick:
            src_path = os.path.join(src, fname)
            dst_path = os.path.join(dst, fname)

            # avoid overwrite if same filename exists
            if os.path.exists(dst_path):
                base, ext = os.path.splitext(fname)
                dst_path = os.path.join(dst, f"{base}_dup{moved}{ext}")

            shutil.move(src_path, dst_path)
            moved += 1

    # final counts
    def count(split):
        out = {}
        for cls in CLASSES:
            d = os.path.join(DATA_ROOT, split, cls)
            out[cls] = len([f for f in os.listdir(d) if f.lower().endswith(IMG_EXTS)])
        return out

    print("\nFINAL COUNTS")
    print("TRAIN:", count("train"))
    print("VAL  :", count("val"))
    print("TEST :", count("test"))


if __name__ == "__main__":
    main()