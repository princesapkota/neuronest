import os
import sys
from typing import Dict,Any

ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
if ROOT not in sys.path:
    sys.path.append(ROOT)

import numpy as np
import nibabel as nib
import cv2
import torch

from ml.brain_tumor.models.unet import UNet


def normalize_zscore(volume: np.ndarray) -> np.ndarray:
    volume = volume.astype(np.float32)
    mean = float(np.mean(volume))
    std = float(np.std(volume))
    if std < 1e-6:
        std = 1.0
    return (volume - mean) / std


def load_model(checkpoint_path: str, device: torch.device) -> UNet:
    model = UNet(in_channels=1, out_channels=1).to(device)
    state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model


def _to_uint8_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert float image to viewable uint8 grayscale (0-255)."""
    img = img.astype(np.float32)
    img = img - img.min()
    mx = img.max()
    if mx > 0:
        img = img / mx
    return (img * 255).astype(np.uint8)


def _make_overlay(gray_u8: np.ndarray, mask01: np.ndarray, alpha: float = 0.35) -> np.ndarray:
    """Overlay green mask over grayscale image."""
    overlay = cv2.cvtColor(gray_u8, cv2.COLOR_GRAY2BGR)
    green = np.zeros_like(overlay)
    green[:, :, 1] = 255
    out = np.where(
        mask01[..., None] == 1,
        (overlay * (1 - alpha) + green * alpha).astype(np.uint8),
        overlay
    )
    return out


def predict_flair_nii_to_pngs(
    flair_nii_path: str,
    checkpoint_path: str,
    out_dir: str,
    size: int = 256,
    threshold: float = 0.5,
    tumor_area_threshold: int = 300,
    device_str: str = "cuda",
) -> Dict[str, Any]:
    """
    Predict brain tumor mask from a FLAIR .nii and save PNG outputs.

    Outputs saved:
      - best_slice_zXXX.png
      - best_mask_zXXX.png
      - best_overlay_zXXX.png

    Returns:
      dict with keys: tumor_found, diagnosis_text, best_idx, best_area, paths, device
    """
    os.makedirs(out_dir, exist_ok=True)

    # device
    if device_str == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    print("Using device:", device)

    # load model
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    model = load_model(checkpoint_path, device)

    # load volume
    if not os.path.exists(flair_nii_path):
        raise FileNotFoundError(f"Input .nii not found: {flair_nii_path}")

    nii = nib.load(flair_nii_path)
    vol = nii.get_fdata()  # expected (240,240,155)
    if vol.ndim != 3:
        raise ValueError(f"Expected 3D volume, got shape: {vol.shape}")

    vol = normalize_zscore(vol)

    z = vol.shape[2]
    best_idx = 0
    best_area = -1
    best_img_r = None
    best_mask01 = None

    with torch.inference_mode():
        for i in range(z):
            img2d = vol[:, :, i]
            img_r = cv2.resize(img2d, (size, size), interpolation=cv2.INTER_LINEAR).astype(np.float32)

            x = torch.from_numpy(img_r).unsqueeze(0).unsqueeze(0).to(device)  # (1,1,H,W)
            logits = model(x)
            prob = torch.sigmoid(logits)[0, 0].detach().cpu().numpy()  # (H,W)
            mask01 = (prob > threshold).astype(np.uint8)
            area = int(mask01.sum())

            if area > best_area:
                best_area = area
                best_idx = i
                best_img_r = img_r
                best_mask01 = mask01

    if best_img_r is None or best_mask01 is None:
        raise RuntimeError("Prediction failed (no best slice found).")

    # formal diagnosis text decision
    tumor_found = best_area >= tumor_area_threshold
    if tumor_found:
        diagnosis_text = (
            "Tumor-like region detected on the analyzed scan. "
            "Please review urgently and proceed with clinical correlation."
        )
    else:
        diagnosis_text = (
            "No tumor-like region detected on the analyzed scan. "
            "Findings appear within normal limits; clinical correlation is advised."
        )

    # save PNGs
    gray_u8 = _to_uint8_grayscale(best_img_r)
    mask_u8 = (best_mask01 * 255).astype(np.uint8)
    overlay = _make_overlay(gray_u8, best_mask01, alpha=0.35)

    slice_path = os.path.join(out_dir, f"best_slice_z{best_idx:03d}.png")
    mask_path = os.path.join(out_dir, f"best_mask_z{best_idx:03d}.png")
    overlay_path = os.path.join(out_dir, f"best_overlay_z{best_idx:03d}.png")

    cv2.imwrite(slice_path, gray_u8)
    cv2.imwrite(mask_path, mask_u8)
    cv2.imwrite(overlay_path, overlay)

    print("Best slice index:", best_idx)
    print("Pred tumor area (pixels):", best_area)
    print("Tumor found:", tumor_found)
    print("Diagnosis:", diagnosis_text)
    print("Saved:")
    print(" ", slice_path)
    print(" ", mask_path)
    print(" ", overlay_path)

    return {
        "best_idx": best_idx,
        "best_area": best_area,
        "tumor_found": tumor_found,
        "diagnosis_text": diagnosis_text,
        "slice_path": slice_path,
        "mask_path": mask_path,
        "overlay_path": overlay_path,
        "device": str(device),
        "threshold": threshold,
        "tumor_area_threshold": tumor_area_threshold,
        "input_nii": flair_nii_path,
        "checkpoint": checkpoint_path,
    }


if __name__ == "__main__":
    ROOT = r"C:\Users\ACER\Desktop\NeuroNest"
    CKPT = os.path.join(ROOT, "ml", "brain_tumor", "checkpoints", "best_unet_flair_binary.pth")

    # Example input (change case id if you want)
    FLAIR_NII = os.path.join(
        ROOT, "Data", "brain_tumor", "raw", "train",
        "BraTS20_Training_001", "BraTS20_Training_001_flair.nii"
    )

    OUT_DIR = os.path.join(ROOT, "ml", "brain_tumor", "inference_outputs", "example_case")

    predict_flair_nii_to_pngs(
        flair_nii_path=FLAIR_NII,
        checkpoint_path=CKPT,
        out_dir=OUT_DIR,
        size=256,
        threshold=0.5,
        tumor_area_threshold=300,
        device_str="cuda",  
    )