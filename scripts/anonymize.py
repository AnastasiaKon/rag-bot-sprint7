"""Подменяет термины исходной вселенной на вымышленные по словарю terms_map.json.

Использование:
    python scripts/anonymize.py --src data/raw --dst knowledge_base --map terms_map.json

Правила замены:
- термины сортируются по длине (длинные первыми), чтобы «Han Solo» заменился
  целиком раньше, чем отдельное «Han»;
- совпадение ищется по границам слов (\\b), поэтому «Count» не тронет «account»;
- ключ, начинающийся с заглавной буквы, матчится с учётом регистра (имена
  собственные: «Force» != «force», «Count» != «count»);
- ключ в нижнем регистре матчится без учёта регистра, а регистр первой буквы
  исходного слова переносится на замену («Lightsaber» -> «Flux blade»);
- имя файла тоже переименовывается по тому же словарю.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def build_patterns(mapping: dict[str, str]) -> list[tuple[re.Pattern, str]]:
    patterns = []
    for term, repl in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
        flags = 0 if term[0].isupper() else re.IGNORECASE
        patterns.append((re.compile(rf"\b{re.escape(term)}\b", flags), repl))
    return patterns


def apply_case(src: str, repl: str) -> str:
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def anonymize_text(text: str, patterns: list[tuple[re.Pattern, str]]) -> tuple[str, int]:
    total = 0

    for pattern, repl in patterns:
        def _sub(m: re.Match) -> str:
            return apply_case(m.group(0), repl)

        text, n = pattern.subn(_sub, text)
        total += n
    return text, total


def slugify(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_").lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw")
    ap.add_argument("--dst", default="knowledge_base")
    ap.add_argument("--map", default="terms_map.json")
    args = ap.parse_args()

    mapping = load_map(Path(args.map))
    patterns = build_patterns(mapping)
    src, dst = Path(args.src), Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)

    stats = []
    for f in sorted(src.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        new_text, n = anonymize_text(text, patterns)
        # заголовок первой строки -> новое имя файла
        title = new_text.splitlines()[0].lstrip("# ").strip()
        out = dst / f"{slugify(title)}.md"
        out.write_text(new_text, encoding="utf-8")
        stats.append((f.name, out.name, n))
        print(f"{f.name:45s} -> {out.name:45s} замен: {n}")

    # контроль: не осталось ли исходных терминов из словаря
    leaked = []
    for f in dst.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        for term in mapping:
            flags = 0 if term[0].isupper() else re.IGNORECASE
            if re.search(rf"\b{re.escape(term)}\b", t, flags):
                leaked.append((f.name, term))
    print(f"\nФайлов: {len(stats)}, всего замен: {sum(s[2] for s in stats)}")
    if leaked:
        print("ВНИМАНИЕ, остались исходные термины:", leaked[:20])
    else:
        print("Утечек исходных терминов не найдено.")


if __name__ == "__main__":
    main()
