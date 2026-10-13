"""Консольный REPL для RAG-бота (Задание 4).

    python bot.py                       # все слои защиты включены
    python bot.py --no-protection       # без защиты (для теста Задания 5)
    python bot.py --no-post-filter      # выборочно: --no-pre-prompt / --no-post-filter / --no-sanitize
    python bot.py -q "вопрос"           # одиночный вопрос без REPL

Команды внутри REPL: /ctx - показать найденные чанки последнего ответа, /quit - выход.
"""
from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from rag_bot import Protection, RagBot


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--question", help="один вопрос вместо интерактивного режима")
    ap.add_argument("-k", type=int, default=4, help="сколько чанков доставать")
    ap.add_argument("--min-score", type=float, default=0.30)
    ap.add_argument("--no-protection", action="store_true")
    ap.add_argument("--no-pre-prompt", action="store_true")
    ap.add_argument("--no-post-filter", action="store_true")
    ap.add_argument("--no-sanitize", action="store_true")
    ap.add_argument("--no-few-shot", action="store_true")
    args = ap.parse_args()

    prot = Protection.none() if args.no_protection else Protection(
        pre_prompt=not args.no_pre_prompt,
        post_filter=not args.no_post_filter,
        sanitize=not args.no_sanitize,
    )
    bot = RagBot(k=args.k, min_score=args.min_score, protection=prot, few_shot=not args.no_few_shot)
    print(f"RAG-бот готов. LLM: {bot.llm.model}, защита: {prot}. /quit для выхода.\n")

    if args.question:
        print(bot.ask(args.question).pretty())
        return

    last = None
    while True:
        try:
            q = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in ("/quit", "/exit"):
            break
        if q == "/ctx":
            if last:
                for h in last.hits:
                    print(f"--- {h.chunk_id} [{h.score:.2f}] {h.title}\n{h.text}\n")
            continue
        last = bot.ask(q)
        print(f"\nБот:\n{last.answer}\n")
        print(f"  (контекст: {', '.join(h.chunk_id for h in last.hits) or '-'}"
              + (f"; отфильтровано: {len(last.dropped)}" if last.dropped else "") + ")\n")


if __name__ == "__main__":
    sys.exit(main())
