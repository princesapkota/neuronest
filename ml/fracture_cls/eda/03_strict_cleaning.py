#detects and handles truncated data that keeps fking interrupting the training 
import os
import sys
from pathlib import Path
from PIL import Image

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA_ROOT = os.path.join(ROOT, "Data", "fracture")
IMG_EXTS = (".jpg", ".jpeg", ".png")

# 
ACTION = "quarantine"  # safer than delete

QUARANTINE_DIR = os.path.join(ROOT, "Data", "fracture_bad_images")


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMG_EXTS


def ensure_dir(d: str):
    os.makedirs(d, exist_ok=True)


def move_to_quarantine(src: str):
    ensure_dir(QUARANTINE_DIR)
    base = os.path.basename(src)
    dst = os.path.join(QUARANTINE_DIR, base)

    # making sure its safe from collision 
    if os.path.exists(dst):
        stem, ext = os.path.splitext(base)
        i = 1
        while os.path.exists(dst):
            dst = os.path.join(QUARANTINE_DIR, f"{stem}_{i}{ext}")
            i += 1

    os.replace(src, dst)
    return dst


def main():
    checked = 0
    bad = 0

    for p in Path(DATA_ROOT).rglob("*"):
        if not p.is_file():
            continue
        if not is_image(p):
            continue

        checked += 1
        try:
            with Image.open(p) as img:
                img.load()  
        except Exception as e:
            bad += 1
            src = str(p)

            if ACTION == "delete":
                try:
                    os.remove(src)
                    print(f"[DELETED] {src} | {type(e).__name__}: {e}")
                except Exception as e2:
                    print(f"[FAILED DELETE] {src} | {e2}")

            else:
                try:
                    dst = move_to_quarantine(src)
                    print(f"[QUARANTINED] {src} -> {dst} | {type(e).__name__}: {e}")
                except Exception as e2:
                    print(f"[FAILED MOVE] {src} | {e2}")

    print("\n=== STRICT CLEAN REPORT ===")
    print("Checked:", checked)
    print("Bad found:", bad)
    print("Action:", ACTION)
    if ACTION == "quarantine":
        print("Quarantine folder:", QUARANTINE_DIR)
    print("Done.")


if __name__ == "__main__":
    main()