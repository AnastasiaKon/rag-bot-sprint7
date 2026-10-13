"""Скачивает страницы Fandom-вики (MediaWiki API) и сохраняет чистый текст.

Использование:
    python scripts/fetch_wiki.py --pages scripts/pages.txt --out data/raw

Для каждой страницы берётся HTML через action=parse, из него вырезаются
инфобоксы, навигация, ссылки «[1]» и прочий мусор, остаются абзацы и
заголовки. Чтобы база не разрасталась, берём первые MAX_WORDS слов.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API = "https://starwars.fandom.com/api.php"
HEADERS = {"User-Agent": "rag-bot-sprint7/0.1 (educational project)"}
MAX_WORDS = 900

# Блоки, которые не несут связного текста
JUNK_SELECTORS = [
    "aside", "table", "figure", "div.toc", "div.reference", "sup.reference",
    "div.quote", "div.navbox", "div.mw-references-wrap", "ol.references",
    "div.notice", "div.hidden", "style", "script", "div.gallery",
    "span.mw-editsection", "div.printfooter", "div.wds-dropdown",
]


def fetch_page(title: str) -> tuple[str, str]:
    """Возвращает (нормализованный заголовок, html) для страницы."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text|displaytitle",
        "format": "json",
        "redirects": 1,
        "disabletoc": 1,
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"{title}: {data['error'].get('info')}")
    return data["parse"]["title"], data["parse"]["text"]["*"]


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for sel in JUNK_SELECTORS:
        for node in soup.select(sel):
            node.decompose()

    lines: list[str] = []
    for node in soup.find_all(["h2", "h3", "p", "li"]):
        text = node.get_text(" ", strip=True)
        text = re.sub(r"\[\d+\]", "", text)          # сноски [1]
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([,.;:!?%)\]])", r"\1", text)   # «слово ,» -> «слово,»
        text = re.sub(r"([(\[])\s+", r"\1", text)
        text = re.sub(r"\s+([-–—])\s+", r" \1 ", text)
        if not text or len(text) < 3:
            continue
        if node.name in ("h2", "h3"):
            if text.lower() in {"contents", "appearances", "sources", "notes and references",
                                "external links", "behind the scenes", "non-canon appearances"}:
                break  # дальше идут списки появлений в медиа - не нужны
            lines.append(f"\n## {text}\n")
        elif node.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    words = " ".join(lines).split()
    if len(words) > MAX_WORDS:
        # режем по словам, но заканчиваем на границе абзаца
        out, count = [], 0
        for line in lines:
            count += len(line.split())
            out.append(line)
            if count >= MAX_WORDS:
                break
        lines = out
    return "\n".join(lines).strip() + "\n"


def slugify(title: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return s.lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="scripts/pages.txt")
    ap.add_argument("--out", default="data/raw")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    titles = [t.strip() for t in Path(args.pages).read_text().splitlines()
              if t.strip() and not t.startswith("#")]

    manifest = []
    for title in titles:
        try:
            real_title, html = fetch_page(title)
            text = html_to_text(html)
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {title}: {exc}")
            continue
        fname = slugify(real_title) + ".md"
        (out_dir / fname).write_text(f"# {real_title}\n\n{text}", encoding="utf-8")
        manifest.append({"title": real_title, "file": fname, "words": len(text.split())})
        print(f"OK   {real_title:40s} {len(text.split()):5d} words")
        time.sleep(0.5)  # вежливость к API

    (out_dir / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено {len(manifest)} страниц в {out_dir}")


if __name__ == "__main__":
    main()
