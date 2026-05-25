import os
import sys
from typing import Dict

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

from ml.fracture_cls.training.dataset import FractureDataset
from ml.fracture_cls.models.densenet121 import build_densenet121_binary


def metrics_from_logits(logits: torch.Tensor, y: torch.Tensor, thr: float = 0.5) -> Dict[str, float]:
    probs = torch.sigmoid(logits)
    pred = (probs >= thr).float()

    tp = (pred * y).sum().item()
    tn = ((1 - pred) * (1 - y)).sum().item()
    fp = (pred * (1 - y)).sum().item()
    fn = ((1 - pred) * y).sum().item()

    eps = 1e-9
    acc = (tp + tn) / (tp + tn + fp + fn + eps)
    prec = tp / (tp + fp + eps)
    rec = tp / (tp + fn + eps)
    f1 = 2 * prec * rec / (prec + rec + eps)
    return {"acc": acc, "prec": prec, "rec": rec, "f1": f1}


def evaluate(model, loader, criterion, device) -> Dict[str, float]:
    """Compute metrics globally over all samples (not per-batch average)."""
    model.eval()
    total_loss = 0.0
    all_logits, all_labels = [], []

    with torch.inference_mode():
        for x, y in loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            logits = model(x)
            total_loss += criterion(logits, y).item()
            all_logits.append(logits.cpu())
            all_labels.append(y.cpu())

    all_logits = torch.cat(all_logits)
    all_labels = torch.cat(all_labels)
    m = metrics_from_logits(all_logits, all_labels)
    m["loss"] = total_loss / max(len(loader), 1)
    return m


def main():
    DATA_ROOT = os.path.join(ROOT, "Data", "fracture_clean")
    TRAIN_DIR = os.path.join(DATA_ROOT, "train")
    VAL_DIR = os.path.join(DATA_ROOT, "val")
    TEST_DIR = os.path.join(DATA_ROOT, "test")

    CKPT_DIR = os.path.join(ROOT, "ml", "fracture_cls", "checkpoints")
    os.makedirs(CKPT_DIR, exist_ok=True)
    BEST_PATH = os.path.join(CKPT_DIR, "best_densenet121_fracture.pth")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    num_workers = 0
    batch_size = 16  
    image_size = 224

    train_ds = FractureDataset(TRAIN_DIR, image_size=image_size, train=True)
    val_ds = FractureDataset(VAL_DIR, image_size=image_size, train=False)
    test_ds = FractureDataset(TEST_DIR, image_size=image_size, train=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    print(f"Train images: {len(train_ds)} | Val images: {len(val_ds)} | Test images: {len(test_ds)}")
    print(f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)}")

    # pos_weight (handles imbalance, though yours is pretty balanced)
    labels = [lbl for _, lbl in train_ds.samples]
    pos = sum(labels)
    neg = len(labels) - pos
    pos_weight = torch.tensor([neg / max(pos, 1)], dtype=torch.float32).to(device)
    print("pos_weight:", float(pos_weight.item()), "(neg/pos)")

    # Full random init — old checkpoint backbone is too corrupted to salvage.
    # Training from scratch is slower but guaranteed not to be stuck.
    model = build_densenet121_binary(pretrained=False).to(device)
    print("Starting from random init (no pretrained weights).")

    criterion  = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer  = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler  = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3, verbose=True
    )

    epochs     = 40
    patience   = 10
    best_f1    = -1.0
    no_improve = 0

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0

        for x, y in tqdm(train_loader, desc=f"Epoch {epoch:02d}/{epochs}"):
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)

            logits = model(x)
            loss = criterion(logits, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running += loss.item()

        train_loss = running / max(len(train_loader), 1)
        val_m = evaluate(model, val_loader, criterion, device)
        scheduler.step(val_m["f1"])

        print(
            f"Epoch {epoch:02d} | train_loss={train_loss:.4f} | "
            f"val_loss={val_m['loss']:.4f} | val_acc={val_m['acc']:.4f} | "
            f"val_prec={val_m['prec']:.4f} | val_rec={val_m['rec']:.4f} | val_f1={val_m['f1']:.4f}"
        )

        if val_m["f1"] > best_f1:
            best_f1    = val_m["f1"]
            no_improve = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "arch": "densenet121",
                    "image_size": image_size,
                    "classes": ["NORMAL", "FRACTURE"],
                    "best_val_f1": best_f1,
                },
                BEST_PATH,
            )
            print(f"  Saved best (val_f1={best_f1:.4f}): {BEST_PATH}")
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"Early stopping at epoch {epoch} — no val F1 improvement for {patience} epochs.")
                break

    print("\nLoading best checkpoint for TEST evaluation...")
    ckpt = torch.load(BEST_PATH, map_location=device)
    model.load_state_dict(ckpt["model_state"])

    test_m = evaluate(model, test_loader, criterion, device)
    print(
        f"TEST | loss={test_m['loss']:.4f} | acc={test_m['acc']:.4f} | "
        f"prec={test_m['prec']:.4f} | rec={test_m['rec']:.4f} | f1={test_m['f1']:.4f}"
    )

    print("Best checkpoint:", BEST_PATH)
    print("Best val f1:", best_f1)


if __name__ == "__main__":
    main()