"""Рендерит «скриншоты терминала» из logs/test_log.json в logs/screenshots/*.png.

    python scripts/render_screenshots.py

5 файлов ok_N.png (полезные ответы) и 5 файлов refuse_N.png (отказы/фильтрация).
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
W, PAD, LH, SIZE = 1100, 28, 22, 15
BG, FG, DIM, OK, BAD = "#1e1e2e", "#cdd6f4", "#6c7086", "#a6e3a1", "#f38ba8"


def render(lines: list[tuple[str, str]], out: Path) -> None:
    font = ImageFont.truetype(FONT, SIZE)
    wrapped: list[tuple[str, str]] = []
    for text, color in lines:
        for ln in text.split("\n"):
            for w in textwrap.wrap(ln, 118) or [""]:
                wrapped.append((w, color))
    img = Image.new("RGB", (W, PAD * 2 + LH * len(wrapped)), BG)
    d = ImageDraw.Draw(img)
    for i, (t, c) in enumerate(wrapped):
        d.text((PAD, PAD + i * LH), t, font=font, fill=c)
    img.save(out)


def main() -> None:
    data = json.loads(Path("logs/test_log.json").read_text(encoding="utf-8"))
    out = Path("logs/screenshots")
    out.mkdir(parents=True, exist_ok=True)

    for i, r in enumerate(data["good"], 1):
        lines = [("$ python bot.py", DIM),
                 ("RAG-бот готов. LLM: claude-haiku-5-5, защита: pre_prompt+post_filter+sanitize.", DIM),
                 ("", FG), (f"Вы: {r['q']}", OK), ("", FG), ("Бот:", FG), (r["answer"], FG), ("", FG),
                 (f"  (контекст: {', '.join(r['chunks'])})", DIM)]
        render(lines, out / f"ok_{i}.png")

    for i, r in enumerate(data["bad"], 1):
        lines = [("$ python bot.py", DIM),
                 ("RAG-бот готов. LLM: claude-haiku-5-5, защита: pre_prompt+post_filter+sanitize.", DIM),
                 ("", FG), (f"Вы: {r['q']}", BAD), ("", FG), ("Бот:", FG), (r["answer"], FG), ("", FG)]
        if r.get("dropped"):
            lines.append((f"  (отфильтровано чанков: {', '.join(r['dropped'])})", DIM))
        lines.append((f"  вердикт: {r['verdict']}", DIM))
        render(lines, out / f"refuse_{i}.png")
    print("готово:", sorted(p.name for p in out.glob("*.png")))


if __name__ == "__main__":
    main()
