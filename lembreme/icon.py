"""Ícone (sino branco em quadrado azul arredondado) desenhado com Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw

ICO_PATH = Path(__file__).resolve().parent.parent / "assets" / "lembreme.ico"


def draw(size: int = 256) -> Image.Image:
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 248, 248), radius=56, fill="#4f8cff")
    w = "white"
    d.ellipse((118, 34, 138, 54), fill=w)                         # argola
    d.ellipse((80, 48, 176, 144), fill=w)                         # cúpula
    d.polygon([(80, 96), (176, 96), (194, 176), (62, 176)], fill=w)  # corpo
    d.rounded_rectangle((48, 166, 208, 192), radius=13, fill=w)   # aba
    d.ellipse((110, 186, 146, 222), fill=w)                       # badalo
    return img if size == S else img.resize((size, size), Image.LANCZOS)


def ensure_ico() -> Path:
    if not ICO_PATH.exists():
        ICO_PATH.parent.mkdir(parents=True, exist_ok=True)
        draw(256).save(ICO_PATH, sizes=[(s, s) for s in (16, 20, 24, 32, 48, 64, 128, 256)])
    return ICO_PATH


if __name__ == "__main__":
    ICO_PATH.unlink(missing_ok=True)
    print(ensure_ico())
