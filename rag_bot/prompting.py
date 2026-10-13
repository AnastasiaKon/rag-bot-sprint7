"""Сборка промпта: system (CoT + защита) + few-shot примеры + контекст + вопрос."""
from __future__ import annotations

from .security import PRE_PROMPT

SYSTEM_BASE = (
    "Ты - ассистент по корпоративной базе знаний. Отвечай ТОЛЬКО на основе "
    "фрагментов документов, которые даны в контексте. Если в контексте нет "
    "ответа, честно напиши «Я не знаю» и не придумывай. Отвечай на языке вопроса.\n\n"
    # Chain-of-Thought: модель сначала рассуждает по шагам, потом даёт ответ
    "Ты помощник, который сначала размышляет, а потом отвечает. Всегда пиши свои шаги.\n"
    "Формат ответа:\n"
    "Рассуждение:\n"
    "1. <какой фрагмент нужен и что в нём сказано>\n"
    "2. <вывод из фрагмента>\n"
    "3. <следовательно ...>\n"
    "Ответ: <краткий ответ>\n"
    "Источники: <chunk_id через запятую, на которые опирался>\n"
)

# Few-shot: примеры из той же базы знаний (ответы реально извлекаются из документов
# taren_vossmark.md и battle_of_ember_reach.md), а не выдуманы.
FEW_SHOT = [
    {
        "q": "On which planet was Taren Vossmark raised?",
        "a": (
            "Рассуждение:\n"
            "1. Найду фрагмент о детстве Taren Vossmark.\n"
            "2. В документе сказано, что после разлучения близнецов Taren was raised by his relatives on Dustreach.\n"
            "3. Следовательно, планета - Dustreach.\n"
            "Ответ: Taren Vossmark вырос на планете Dustreach.\n"
            "Источники: taren_vossmark#1"
        ),
    },
    {
        "q": "What superweapon was destroyed at the Battle of Ember Reach?",
        "a": (
            "Рассуждение:\n"
            "1. Найду описание Battle of Ember Reach.\n"
            "2. В документе сказано, что Vossmark destroyed the Dominion's planet-killing superweapon, the Void Core.\n"
            "3. Следовательно, уничтожен Void Core.\n"
            "Ответ: В битве при Ember Reach был уничтожен Void Core.\n"
            "Источники: taren_vossmark#1, battle_of_ember_reach#0"
        ),
    },
]


def build_system(pre_prompt: bool) -> str:
    return SYSTEM_BASE + ("\n" + PRE_PROMPT if pre_prompt else "")


def build_user_message(question: str, hits: list, few_shot: bool = True) -> str:
    parts = []
    if few_shot:
        parts.append("Примеры ответов:\n")
        for ex in FEW_SHOT:
            parts.append(f"Q: {ex['q']}\nA: {ex['a']}\n")
        parts.append("")
    parts.append("Фрагменты документов (контекст):")
    if not hits:
        parts.append("(ничего не найдено)")
    for h in hits:
        parts.append(f"<doc id=\"{h.chunk_id}\" title=\"{h.title}\" score=\"{h.score:.2f}\">\n{h.text}\n</doc>")
    parts.append(f"\nQ: {question}\nA:")
    return "\n".join(parts)
