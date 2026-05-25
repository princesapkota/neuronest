import os
import sys
import random

import matplotlib.pyplot as plt
from PIL import Image

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA_ROOT = os.path.join(ROOT, "Data", "chest_xray")
SPLIT = "train"
CLASSES = ["NORMAL", "PNEUMONIA"]
IMG_EXTS = (".jpg", ".jpeg", ".png")


def pick_random_image(folder: str) -> str:
    files = [f for f in os.listdir(folder) if f.lower().endswith(IMG_EXTS)]
    return os.path.join(folder, random.choice(files))


def main():
    plt.figure(figsize=(10, 4))
    for i, cls in enumerate(CLASSES):
        folder = os.path.join(DATA_ROOT, SPLIT, cls)
        path = pick_random_image(folder)
        img = Image.open(path).convert("RGB")

        plt.subplot(1, 2, i + 1)
        plt.imshow(img)
        plt.title(f"{SPLIT.upper()} - {cls}")
        plt.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()