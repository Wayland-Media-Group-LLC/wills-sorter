"""Draws the app icon and writes assets/app_icon.ico and .png.

Only needed to change the icon; requires Pillow (pip install pillow).
Colors come from the app's own palette in src/theme.py.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
NAVY, TEAL, WHITE = "#142b32", "#3cc2bf", "#f4fafb"
S = 1024   # drawn large, then scaled down so edges stay smooth


def draw():
    image = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=NAVY)
    # tray the download lands in
    width = 96
    tray = [(236, 610), (236, 800), (788, 800), (788, 610)]
    d.line(tray, fill=TEAL, width=width, joint="curve")
    for x, y in (tray[0], tray[-1]):
        d.ellipse((x - width // 2, y - width // 2, x + width // 2, y + width // 2), fill=TEAL)
    # arrow pointing into it
    d.rounded_rectangle((452, 190, 572, 520), radius=40, fill=WHITE)
    d.polygon([(322, 470), (702, 470), (512, 690)], fill=WHITE)
    return image


def main():
    ASSETS.mkdir(exist_ok=True)
    icon = draw()
    icon.resize((256, 256), Image.LANCZOS).save(ASSETS / "app_icon.png")
    icon.save(ASSETS / "app_icon.ico", sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])


if __name__ == "__main__":
    main()
