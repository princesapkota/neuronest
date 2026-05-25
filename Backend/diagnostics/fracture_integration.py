from __future__ import annotations

from pathlib import Path
import io
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont


# this walks up the folders to find the top NeuroNest project folder
def _project_root() -> Path:
    # Backend/diagnostics/fracture_integration.py -> parents[0]=diagnostics, [1]=Backend, [2]=NeuroNest
    return Path(__file__).resolve().parents[2]


# make sure the project root is on the path so the "import ml...." line below can find the ml folder
PROJECT_ROOT = str(_project_root())
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# this points to the trained fracture model file on disk
def _ckpt_path() -> str:
    return str(_project_root() / "ml" / "fracture_cls" / "checkpoints" / "best_densenet121_fracture.pth")


# this loads a font for drawing text, and falls back to a default one if arial is missing
def _load_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


# this runs the fracture model on the x-ray then draws a report image showing the input and the result
def build_fracture_report_png(input_image_path: str) -> tuple[bytes, dict]:
    """
    Runs:
      ml/fracture_cls/inference/predict_image.py

    Returns:
      (png_bytes, pred_dict)
    """
    from ml.fracture_cls.inference.predict_image import predict_image

    pred = predict_image(
        image_path=input_image_path,
        ckpt_path=_ckpt_path(),
        device_str="cpu",
    )

    label = str(pred["label"])
    prob = float(pred["probability"])
    threshold = float(pred["threshold"])
    diagnosis_text = str(pred["diagnosis_text"])

    W, H = 1100, 620
    bg = (23, 24, 29)
    border = (45, 47, 58)
    white = (255, 255, 255)
    muted = (184, 188, 198)
    primary = (47, 111, 235)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((10, 10, W - 10, H - 10), radius=18, outline=border, width=2)

    f_title = _load_font(28)
    f_text = _load_font(18)
    f_small = _load_font(15)

    # Title
    draw.text((34, 28), "Fracture Report", fill=white, font=f_title)
    draw.rounded_rectangle((34, 72, 230, 78), radius=6, fill=primary)

    # Left: input image preview
    src = Image.open(input_image_path).convert("RGB")

    box = (34, 110, 520, 560)
    bw = box[2] - box[0]
    bh = box[3] - box[1]

    preview = src.copy()
    preview.thumbnail((bw, bh))

    px = box[0] + (bw - preview.size[0]) // 2
    py = box[1] + (bh - preview.size[1]) // 2

    draw.rounded_rectangle(box, radius=16, outline=border, width=2)
    img.paste(preview, (px, py))
    draw.text((34, 570), "Input X-ray", fill=muted, font=f_small)

    # Right: model output
    x0 = 560
    y0 = 120

    draw.text((x0, y0), "Model Output", fill=white, font=f_title)
    y0 += 52

    draw.text((x0, y0), f"Label: {label}", fill=muted, font=f_text)
    y0 += 34

    draw.text((x0, y0), f"Probability: {prob:.4f}", fill=muted, font=f_text)
    y0 += 34

    draw.text((x0, y0), f"Threshold: {threshold:.2f}", fill=muted, font=f_text)
    y0 += 42

    draw.text((x0, y0), "Diagnosis:", fill=white, font=f_text)
    y0 += 28

    wrapped = textwrap.wrap(diagnosis_text, width=44)
    for line in wrapped[:8]:
        draw.text((x0, y0), line, fill=muted, font=f_text)
        y0 += 26

    draw.text((x0, 560), "Final verdict must be confirmed by employee.", fill=muted, font=f_small)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), pred