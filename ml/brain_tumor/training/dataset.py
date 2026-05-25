import os
import numpy as np
import torch
from torch.utils.data import Dataset

class NPYSegDataset(Dataset):
    def __init__(self, images_dir: str, masks_dir: str):
        self.images_dir = images_dir
        self.masks_dir = masks_dir

        self.files = sorted([f for f in os.listdir(images_dir) if f.endswith(".npy")])

        # sanity check
        if len(self.files) == 0:
            raise ValueError(f"No .npy files found in {images_dir}")

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        fname = self.files[idx]

        img_path = os.path.join(self.images_dir, fname)
        msk_path = os.path.join(self.masks_dir, fname)

        img = np.load(img_path).astype(np.float32)  # (256,256)
        msk = np.load(msk_path).astype(np.float32)  # (256,256) 0/1

        # add channel dim: (1, H, W)
        img = torch.from_numpy(img).unsqueeze(0)
        msk = torch.from_numpy(msk).unsqueeze(0)

        return img, msk