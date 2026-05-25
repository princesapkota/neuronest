import os
import sys
from typing import Dict, Any
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

# Dynamically find project root: .../ml/fracture_cls/inference/predict_image.py -> parents[3] == project root
ROOT = str(Path(__file__).resolve().parents[3])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from ml.fracture_cls.models.densenet121 import build_densenet121_binary

THRESHOLD = 0.51  # tuned on validation


def load_ckpt(ckpt_path: str, device: torch.device):
    ckpt = torch.load(ckpt_path, map_location=device)
    model = build_densenet121_binary(pretrained=False).to(device)
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

    label = "FRACTURE" if prob >= THRESHOLD else "NORMAL"

    if label == "FRACTURE":
        diagnosis_text = (
            "Findings suggest a fracture. Please review promptly and correlate with clinical assessment."
        )
    else:
        diagnosis_text = (
            "No fracture-like finding detected in the analyzed X-ray image. Clinical correlation is advised."
        )

    return {
        "label": label,
        "probability": prob,
        "threshold": THRESHOLD,
        "diagnosis_text": diagnosis_text,
        "device": str(device),
        "checkpoint": ckpt_path,
        "image": image_path,
    }


if __name__ == "__main__":
    CKPT = os.path.join(ROOT, "ml", "fracture_cls", "checkpoints", "best_densenet121_fracture.pth")

    test_frac = os.path.join(ROOT, "Data", "fracture", "test", "fractured")
    test_norm = os.path.join(ROOT, "Data", "fracture", "test", "not fractured")

    folder = test_frac if os.path.isdir(test_frac) and len(os.listdir(test_frac)) > 0 else test_norm
    fn = next(f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    img_path = os.path.join(folder, fn)

    print(predict_image(img_path, CKPT, device_str="cuda"))