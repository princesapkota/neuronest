import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

import sys

# Add project root to Python path
ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
sys.path.append(ROOT)

from ml.brain_tumor.training.dataset import NPYSegDataset
from ml.brain_tumor.models.unet import UNet

def dice_score(pred, target, eps=1e-6):
    pred = (pred > 0.5).float()
    target = target.float()
    inter = (pred * target).sum()
    union = pred.sum() + target.sum()
    return (2 * inter + eps) / (union + eps)

def main():
    ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
    BASE = os.path.join(ROOT, "ml", "brain_tumor", "processed")

    train_img = os.path.join(BASE, "train", "images")
    train_msk = os.path.join(BASE, "train", "masks")
    val_img   = os.path.join(BASE, "val", "images")
    val_msk   = os.path.join(BASE, "val", "masks")

    ckpt_dir = os.path.join(ROOT, "ml", "brain_tumor", "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    train_ds = NPYSegDataset(train_img, train_msk)
    val_ds   = NPYSegDataset(val_img, val_msk)

    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True, num_workers=0)
    val_loader   = DataLoader(val_ds, batch_size=8, shuffle=False, num_workers=0)

    print("Train batches:", len(train_loader))
    print("Val batches:", len(val_loader))

    model = UNet(in_channels=1, out_channels=1).to(device)

    # BCEWithLogits expects raw logits, so don't sigmoid in model
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    best_dice = 0.0
    epochs = 10

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0

        for imgs, msks in tqdm(train_loader, desc=f"Epoch{epoch}"):
            
            imgs = imgs.to(device, non_blocking=True)
            msks = msks.to(device, non_blocking=True)

            logits = model(imgs)
            loss = criterion(logits, msks)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)

        # validation
        model.eval()
        val_loss = 0.0
        val_dice = 0.0

        with torch.inference_mode():
            for imgs, msks in val_loader:
                imgs = imgs.to(device, non_blocking=True)
                msks = msks.to(device, non_blocking=True)

                logits = model(imgs)
                loss = criterion(logits, msks)
                val_loss += loss.item()

                probs = torch.sigmoid(logits)
                val_dice += dice_score(probs, msks).item()
            

        val_loss /= len(val_loader)
        val_dice /= len(val_loader)

        print(f"Epoch {epoch:02d} | train_loss={train_loss:.4f} | val_loss={val_loss:.4f} | val_dice={val_dice:.4f}")
        # save best
        if val_dice > best_dice:
            best_dice = val_dice
            ckpt_path = os.path.join(ckpt_dir, "best_unet_flair_binary.pth")
            torch.save(model.state_dict(), ckpt_path)
            print("Saved:", ckpt_path)

    print("Best val dice:", best_dice)

if __name__ == "__main__":
    main()