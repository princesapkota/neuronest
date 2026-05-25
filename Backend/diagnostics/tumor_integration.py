from __future__ import annotations

from pathlib import Path
import sys
import io
import textwrap

from PIL import Image, ImageDraw, ImageFont


# this walks up the folders to find the top NeuroNest project folder
def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# make sure the project root is on the path so the "import ml...." line below can find the ml folder
PROJECT_ROOT = str(_project_root())

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# this points to the trained brain tumor model file on disk
def _ckpt_path() -> str:
    return str(
        _project_root()
        / "ml"
        / "brain_tumor"
        / "checkpoints"
        / "best_unet_flair_binary.pth"
    )


# this loads a font for drawing text, and falls back to a default one if arial is missing
def _load_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


# this runs the tumor segmentation on the nii scan then draws a report image with the overlay and result
def build_tumor_report_png(input_nii_path: str) -> tuple[bytes, dict]:
    """
    Runs tumor segmentation inference and creates a combined report PNG.

    Returns:
      (png_bytes, result_dict)
    """

    from ml.brain_tumor.inference.predict_volume import predict_flair_nii_to_pngs

    tmp_dir = (
        _project_root()
        / "media"
        / "brain_tumor"
        / "tmp"
    )
    tmp_dir.mkdir(parents=True, exist_ok=True)

    result = predict_flair_nii_to_pngs(
        flair_nii_path=input_nii_path,
        checkpoint_path=_ckpt_path(),
        out_dir=str(tmp_dir),
        device_str="cpu",
    )

    overlay_path = result["overlay_path"]
    diagnosis_text = str(result["diagnosis_text"])
    best_idx = int(result["best_idx"])
    best_area = int(result["best_area"])
    tumor_found = bool(result["tumor_found"])

    # Load overlay image
    overlay_img = Image.open(overlay_path).convert("RGB")

    # ---------- Build final report image ----------
    W, H = 1100, 620
    bg = (23, 24, 29)
    border = (45, 47, 58)
    white = (255, 255, 255)
    muted = (184, 188, 198)
    primary = (47, 111, 235)

    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((10, 10, W - 10, H - 10), radius=18, outline=border, width=2)

    f_title = _load_font(28)
    f_text = _load_font(18)
    f_small = _load_font(15)

    # Title
    draw.text((34, 28), "Brain Tumor Segmentation Report", fill=white, font=f_title)
    draw.rounded_rectangle((34, 72, 360, 78), radius=6, fill=primary)

    # Left: overlay preview
    box = (34, 110, 520, 560)
    bw = box[2] - box[0]
    bh = box[3] - box[1]

    preview = overlay_img.copy()
    preview.thumbnail((bw, bh))

    px = box[0] + (bw - preview.size[0]) // 2
    py = box[1] + (bh - preview.size[1]) // 2

    draw.rounded_rectangle(box, radius=16, outline=border, width=2)
    canvas.paste(preview, (px, py))
    draw.text((34, 570), "Best tumor slice overlay", fill=muted, font=f_small)

    # Right: text output
    x0 = 560
    y0 = 120

    draw.text((x0, y0), "Model Output", fill=white, font=f_title)
    y0 += 52

    status_text = "Tumor Detected" if tumor_found else "No Tumor Detected"
    draw.text((x0, y0), f"Prediction: {status_text}", fill=muted, font=f_text)
    y0 += 34

    draw.text((x0, y0), f"Best Slice Index: {best_idx}", fill=muted, font=f_text)
    y0 += 34

    draw.text((x0, y0), f"Tumor Area (pixels): {best_area}", fill=muted, font=f_text)
    y0 += 42

    draw.text((x0, y0), "Diagnosis:", fill=white, font=f_text)
    y0 += 28

    wrapped = textwrap.wrap(diagnosis_text, width=42)
    for line in wrapped[:8]:
        draw.text((x0, y0), line, fill=muted, font=f_text)
        y0 += 26

    draw.text((x0, 560), "Final verdict must be confirmed by employee.", fill=muted, font=f_small)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue(), result