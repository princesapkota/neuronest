import os
from typing import Tuple 

from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

class ChestXrayDataset(Dataset):
    """
    Expects:
      root_dir/
        NORMAL/
        PNEUMONIA/
    Returns:
      image: FloatTensor [3,H,W]
      label: FloatTensor [1] (0.0 normal, 1.0 pneumonia)
    """

    def __init__(self, root_dir: str, image_size: int = 224, train: bool = True):
        self.root_dir = root_dir
        self.image_size = image_size

        self.class_to_idx = {"NORMAL": 0, "PNEUMONIA": 1}

        self.samples = []
        for cls in ["NORMAL", "PNEUMONIA"]:
            cls_dir = os.path.join(root_dir, cls)
            if not os.path.isdir(cls_dir):
                raise FileNotFoundError(f"Missing class folder: {cls_dir}")

            for fname in os.listdir(cls_dir):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    self.samples.append((os.path.join(cls_dir, fname), self.class_to_idx[cls]))

        if len(self.samples) == 0:
            raise ValueError(f"No images found in {root_dir}")

        # Transforms
        if train:
            self.tf = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomRotation(degrees=7),
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

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        x = self.tf(img)
        y = torch.tensor([float(label)], dtype=torch.float32)
        return x, y