import os
from typing import Tuple, List

import torch
from torch.utils.data import Dataset
from PIL import Image, ImageFile
from torchvision import transforms

# Allow loading truncated images (still may fail sometimes, but helps)
ImageFile.LOAD_TRUNCATED_IMAGES = True

IMG_EXTS = (".jpg", ".jpeg", ".png")

RAW_TO_STD = {
    "fractured": "FRACTURE",
    "not fractured": "NORMAL",
}


class FractureDataset(Dataset):
    """
    Returns:
      x: FloatTensor [3,H,W]
      y: FloatTensor [1] (1=FRACTURE, 0=NORMAL)
    Skips unreadable images safely (will try next index).
    """

    def __init__(self, split_dir: str, image_size: int = 224, train: bool = True, log_bad: bool = True):
        if not os.path.isdir(split_dir):
            raise FileNotFoundError(f"Split folder not found: {split_dir}")

        self.split_dir = split_dir
        self.image_size = image_size
        self.log_bad = log_bad

        self.samples: List[Tuple[str, int]] = []
        self.class_to_idx = {"NORMAL": 0, "FRACTURE": 1}

        for raw_name in os.listdir(split_dir):
            class_path = os.path.join(split_dir, raw_name)
            if not os.path.isdir(class_path):
                continue

            key = raw_name.strip().lower()
            if key not in RAW_TO_STD:
                continue

            std = RAW_TO_STD[key]
            y = self.class_to_idx[std]

            for fn in os.listdir(class_path):
                if fn.lower().endswith(IMG_EXTS):
                    self.samples.append((os.path.join(class_path, fn), y))

        if len(self.samples) == 0:
            raise ValueError(f"No images found in: {split_dir}")

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomRotation(10),
                transforms.ColorJitter(brightness=0.10, contrast=0.10),
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.485, 0.456, 0.406),
                                     std=(0.229, 0.224, 0.225)),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.485, 0.456, 0.406),
                                     std=(0.229, 0.224, 0.225)),
            ])

    def __len__(self):
        return len(self.samples)

    def _load_image_rgb(self, path: str) -> Image.Image:
        # context manager ensures file handle is closed quickly on Windows
        with Image.open(path) as im:
            return im.convert("RGB")

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        # Keep trying until we find a valid image
        tries = 0
        while True:
            path, label = self.samples[idx]
            try:
                img = self._load_image_rgb(path)
                x = self.tf(img)
                y = torch.tensor([float(label)], dtype=torch.float32)
                return x, y
            except Exception as e:
                tries += 1
                if self.log_bad:
                    print(f"[BAD IMAGE] {path} | {type(e).__name__}: {e}")

                # move to next index (wrap around)
                idx = (idx + 1) % len(self.samples)

                # If we somehow hit too many bad in a row, raise
                if tries >= 20:
                    raise RuntimeError("Too many unreadable images encountered in a row. Dataset may be corrupted.")