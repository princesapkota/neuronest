import os
import sys
from typing import Dict

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

# ensure project root is on path 
ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

from ml.pneumonia.training.dataset import ChestXrayDataset
from ml.pneumonia.models.resnet18 import build_resnet18_binary


def metrics_from_logits(logits: torch.Tensor, y: torch.Tensor, thr: float = 0.5) -> Dict[str, float]:
    """
    logits: (B,1) raw
    y: (B,1) 0/1
    """
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
    model.eval()
    total_loss = 0.0
    m = {"acc": 0.0, "prec": 0.0, "rec": 0.0, "f1": 0.0}
    n_batches = 0

    with torch.inference_mode():
        for x, y in loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)

            logits = model(x)
            loss = criterion(logits, y)
            total_loss += loss.item()

            batch_m = metrics_from_logits(logits, y)
            for k in m:
                m[k] += batch_m[k]
            n_batches += 1

    for k in m:
        m[k] /= max(n_batches, 1)

    m["loss"] = total_loss / max(n_batches, 1)
    return m


def main():
    DATA_ROOT = os.path.join(ROOT, "Data", "chest_xray")
    TRAIN_DIR = os.path.join(DATA_ROOT, "train")
    VAL_DIR = os.path.join(DATA_ROOT, "val")
    TEST_DIR = os.path.join(DATA_ROOT, "test")

    CKPT_DIR = os.path.join(ROOT, "ml", "pneumonia", "checkpoints")
    os.makedirs(CKPT_DIR, exist_ok=True)
    BEST_PATH = os.path.join(CKPT_DIR, "best_resnet18_pneumonia.pth")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    # Windows-safe
    num_workers = 0
    batch_size = 32

    train_ds = ChestXrayDataset(TRAIN_DIR, image_size=224, train=True)
    val_ds = ChestXrayDataset(VAL_DIR, image_size=224, train=False)
    test_ds = ChestXrayDataset(TEST_DIR, image_size=224, train=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    print("Train images:", len(train_ds), "Val images:", len(val_ds), "Test images:", len(test_ds))
    print("Train batches:", len(train_loader), "Val batches:", len(val_loader), "Test batches:", len(test_loader))

    model = build_resnet18_binary(pretrained=True).to(device)

    # Handle imbalance using pos_weight
    # pos_weight = (#neg / #pos)
    labels = [lbl for _, lbl in train_ds.samples]
    pos = sum(labels)
    neg = len(labels) - pos
    pos_weight = torch.tensor([neg / max(pos, 1)], dtype=torch.float32).to(device)
    print("pos_weight:", float(pos_weight.item()), " (neg/pos)")

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    epochs = 8
    best_f1 = -1.0

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0

        for x, y in tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}"):
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

        print(
            f"Epoch {epoch:02d} | train_loss={train_loss:.4f} | "
            f"val_loss={val_m['loss']:.4f} | val_acc={val_m['acc']:.4f} | "
            f"val_prec={val_m['prec']:.4f} | val_rec={val_m['rec']:.4f} | val_f1={val_m['f1']:.4f}"
        )

        if val_m["f1"] > best_f1:
            best_f1 = val_m["f1"]
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "arch": "resnet18",
                    "image_size": 224,
                    "classes": ["NORMAL", "PNEUMONIA"],
                    "best_val_f1": best_f1,
                },
                BEST_PATH,
            )
            print("Saved best:", BEST_PATH)

    # Final test evaluation using best checkpoint
    print("Loading best checkpoint for test eval...")
    ckpt = torch.load(BEST_PATH, map_location=device)
    model.load_state_dict(ckpt["model_state"])
    test_m = evaluate(model, test_loader, criterion, device)

    print(
        f"TEST | loss={test_m['loss']:.4f} | acc={test_m['acc']:.4f} | "
        f"prec={test_m['prec']:.4f} | rec={test_m['rec']:.4f} | f1={test_m['f1']:.4f}"
    )


if __name__ == "__main__":
    main()