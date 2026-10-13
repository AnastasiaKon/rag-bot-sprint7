"""Цепочка RAG: запрос -> эмбеддинг -> поиск -> (защита) -> промпт -> LLM -> ответ.

Что происходит под капотом (аналог LangChain RetrievalQA, но явно):
  1. Retriever кодирует вопрос той же моделью, что и индекс, и достаёт top-k чанков.
  2. Слой защиты (опционально) выбрасывает подозрительные чанки и чистит текст.
  3. Если лучший score ниже порога - контекста нет, бот сразу отвечает «Я не знаю».
  4. Собирается system-промпт (CoT + pre-prompt) и user-сообщение (few-shot + контекст + вопрос).
  5. LLM генерирует ответ, бот возвращает его вместе с использованными чанками.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLM
from .prompting import build_system, build_user_message
from .retriever import Hit, Retriever
from .security import post_filter, sanitize

DONT_KNOW = "Я не знаю. В базе знаний нет информации по этому вопросу."


@dataclass
class Protection:
    pre_prompt: bool = True
    post_filter: bool = True
    sanitize: bool = True

    @classmethod
    def none(cls) -> "Protection":
        return cls(False, False, False)

    def __str__(self) -> str:
        on = [n for n in ("pre_prompt", "post_filter", "sanitize") if getattr(self, n)]
        return "+".join(on) if on else "OFF"


@dataclass
class Answer:
    question: str
    answer: str
    hits: list[Hit] = field(default_factory=list)
    dropped: list = field(default_factory=list)   # [(Hit, причина)]
    protection: str = ""
    refused: bool = False

    def pretty(self) -> str:
        lines = [f"Q: {self.question}", f"Защита: {self.protection}"]
        if self.dropped:
            lines.append("Отфильтровано чанков: " + "; ".join(
                f"{h.chunk_id} ({r})" for h, r in self.dropped))
        lines.append("Контекст: " + (", ".join(f"{h.chunk_id}[{h.score:.2f}]" for h in self.hits) or "-"))
        lines.append("")
        lines.append(self.answer)
        return "\n".join(lines)


class RagBot:
    def __init__(self, index_dir: str = "index", k: int = 4, min_score: float = 0.30,
                 protection: Protection | None = None, few_shot: bool = True,
                 llm: LLM | None = None):
        self.retriever = Retriever(index_dir)
        self.k = k
        self.min_score = min_score
        self.protection = protection or Protection()
        self.few_shot = few_shot
        self.llm = llm or LLM()

    def retrieve(self, question: str) -> tuple[list[Hit], list]:
        hits = self.retriever.search(question, self.k)
        dropped: list = []
        if self.protection.post_filter:
            res = post_filter(hits)
            hits, dropped = res.kept, res.dropped
        if self.protection.sanitize:
            hits = [Hit(h.score, h.chunk_id, h.source, h.title, h.position, sanitize(h.text))
                    for h in hits]
        return hits, dropped

    def ask(self, question: str) -> Answer:
        hits, dropped = self.retrieve(question)
        prot = str(self.protection)

        relevant = [h for h in hits if h.score >= self.min_score]
        if not relevant:
            return Answer(question, DONT_KNOW, hits, dropped, prot, refused=True)

        system = build_system(pre_prompt=self.protection.pre_prompt)
        user = build_user_message(question, relevant, few_shot=self.few_shot)
        text = self.llm.complete(system, user)
        refused = "я не знаю" in text.lower() or "i don't know" in text.lower()
        return Answer(question, text, relevant, dropped, prot, refused=refused)
