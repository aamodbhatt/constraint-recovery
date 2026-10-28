"""Conservative local text metrics; exact browser typography is a later milestone."""
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont


@lru_cache(maxsize=128)
def font(size):
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                 "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(path, size=max(1, round(size)))
        except OSError:
            pass
    return ImageFont.load_default(size=max(1, round(size)))


def text_width(text, size):
    return float(font(size).getlength(text)) * 1.08


def wrap(text, size, preferred_width):
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if current and text_width(trial, size) > preferred_width:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    return lines or [""]
