import os
import sys
from typing import Dict, Any
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms


# Dynamically find project root: .../ml/pneumonia/inference/predict_image.py -> parents[3] == project root
ROOT = str(Path(__file__).resolve().parents[3])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from ml.pneumonia.models.resnet18 import build_resnet18_binary


def load_ckpt(ckpt_path: str, device: torch.device):
    ckpt = torch.load(ckpt_path, map_location=device)
    model = build_resnet18_binary(pretrained=False).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, ckpt


def predict_image(image_path: str, ckpt_path: str, device_str: str = "cuda") -> Dict[str, Any]:
    device = torch.device(device_str if (device_str == "cuda" and torch.cuda.is_available()) else "cpu")
    model, ckpt = load_ckpt(ckpt_path, device)

    size = int(ckpt.get("image_size", 224))
    tf = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406),
                             std=(0.229, 0.224, 0.225)),
    ])

    img = Image.open(image_path).convert("RGB")
    x = tf(img).unsqueeze(0).to(device)

    with torch.inference_mode():
        logits = model(x)
        prob = torch.sigmoid(logits)[0, 0].item()

    label = "PNEUMONIA" if prob >= 0.5 else "NORMAL"

    if label == "PNEUMONIA":
        diagnosis_text = (
            "Findings suggest pneumonia. Please review promptly and correlate with clinical assessment."
        )
    else:
        diagnosis_text = (
            "No radiographic evidence of pneumonia detected in the analyzed image. Clinical correlation is advised."
        )

    return {
        "label": label,
        "probability": prob,
        "diagnosis_text": diagnosis_text,
        "device": str(device),
        "checkpoint": ckpt_path,
        "image": image_path,
    }


if __name__ == "__main__":
    CKPT = os.path.join(ROOT, "ml", "pneumonia", "checkpoints", "best_resnet18_pneumonia.pth")

    EXAMPLE = os.path.join(ROOT, "Data", "chest_xray", "test", "PNEUMONIA")
    fname = next(f for f in os.listdir(EXAMPLE) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    IMG_PATH = os.path.join(EXAMPLE, fname)

    out = predict_image(IMG_PATH, CKPT, device_str="cuda")
    print(out)

    
    