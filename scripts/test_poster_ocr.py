"""Run five in-memory poster-layout OCR checks without touching project data."""
from __future__ import annotations
from io import BytesIO
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion.image_extractor import extract_image_text

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

def font(size):
    try: return ImageFont.truetype(FONT_PATH, size)
    except OSError: return ImageFont.load_default()

def poster(size=(1200, 800), background="white", rotated=0, columns=False, low=False, noisy=False):
    image = Image.new("RGB", size, background); draw = ImageDraw.Draw(image)
    dark = (20, 30, 45) if background == "white" else (255, 255, 255)
    draw.text((50, 35), "ACME TECHNOLOGIES", fill=dark, font=font(44))
    draw.text((50, 105), "Data Analyst Intern", fill=(20, 100, 190) if background == "white" else (255, 230, 80), font=font(52))
    left = "Location: Bengaluru\nSkills: Python, SQL, Excel\nQualifications: Graduate\nApply: careers@example.com"
    right = "Responsibilities:\nBuild dashboards and reports.\nAnalyze business data.\nFull-time internship."
    if columns:
        draw.multiline_text((55, 210), left, fill=dark, font=font(32), spacing=16)
        draw.multiline_text((620, 210), right, fill=dark, font=font(32), spacing=16)
    else:
        draw.multiline_text((55, 210), left + "\n\n" + right, fill=dark, font=font(32), spacing=16)
    if noisy: image = image.filter(ImageFilter.GaussianBlur(1.2))
    if low: image = image.resize((600, 400), Image.Resampling.LANCZOS)
    if rotated: image = image.rotate(rotated, expand=True, fillcolor=background)
    output = BytesIO(); image.save(output, format="PNG"); return output.getvalue()

def main():
    cases = [
        ("clear", poster()),
        ("low_resolution", poster(low=True, noisy=True)),
        ("coloured_background", poster(background=(30, 80, 130))),
        ("multi_column", poster(columns=True)),
        ("rotated", poster(rotated=90)),
    ]
    results = []
    expected = ["ACME", "Data", "Bengaluru", "Python", "example.com"]
    for name, payload in cases:
        result = extract_image_text(payload, f"{name}.png")
        text = result.get("text", "")
        results.append({"case": name, "status": result.get("status"), "characters": len(text), "matched_expected_tokens": [token for token in expected if token.lower() in text.lower()], "missing_expected_tokens": [token for token in expected if token.lower() not in text.lower()], "selected_attempt": result.get("selected_attempt"), "warnings": result.get("warnings", [])})
    import json
    print(json.dumps(results, indent=2))

if __name__ == "__main__": main()
