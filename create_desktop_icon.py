"""천둥감자 실행 파일 아이콘을 만든다."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


SIZE = 512
canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(canvas)
draw.rounded_rectangle((12, 12, 500, 500), radius=122, fill="#123e2b")

glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow)
glow_draw.ellipse((80, 73, 430, 440), fill=(165, 245, 71, 70))
canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(36)))

draw = ImageDraw.Draw(canvas)
draw.ellipse((96, 132, 417, 434), fill="#e8b268", outline="#ffdb8f", width=14)
draw.ellipse((139, 243, 159, 263), fill="#8b5b32")
draw.ellipse((352, 264, 371, 283), fill="#8b5b32")
draw.ellipse((164, 308, 186, 330), fill="#183e2d")
draw.ellipse((326, 308, 348, 330), fill="#183e2d")
draw.arc((217, 318, 298, 369), 10, 170, fill="#183e2d", width=10)
draw.polygon([(293, 69), (214, 202), (265, 199), (227, 304), (343, 159), (284, 163), (329, 73)],
             fill="#b4f155", outline="#f4ffb0")

target = Path(__file__).parent / "assets" / "thunder-potato.ico"
target.parent.mkdir(exist_ok=True)
canvas.save(target, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(target)
