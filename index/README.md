# Векторный индекс базы знаний

Собирается командой `python build_index.py` (файлы `faiss.index` и `chunks.pkl` лежат в репозитории - 1.2 МБ; пересобираются за ~20 секунд, `stats.json` фиксирует параметры последней сборки).

| Параметр | Значение |
|---|---|
| Модель эмбеддингов | `sentence-transformers/all-MiniLM-L6-v2` - https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 |
| Размерность вектора | 384 |
| База знаний | `knowledge_base/` - 55 документов вселенной «Ashfall Saga» (анонимизированный Star Wars, см. `terms_map.json`) |
| Чанкинг | `RecursiveCharacterTextSplitter`, 800 символов, перекрытие 120, разделители `## `, абзац, строка, предложение; чанки короче 60 символов отбрасываются |
| Чанков в индексе | 588 (в среднем ~90 слов) |
| Индекс | `faiss.IndexFlatIP` - точный поиск по косинусному сходству (векторы нормированы) |
| Метаданные чанка | `chunk_id`, `source` (путь к файлу), `title`, `position` (смещение в символах), `text` |
| Время генерации | ~19 с на CPU (4 vCPU, без GPU), включая загрузку модели |

## Пример запроса

```
$ python build_index.py --query "Who was the mentor of Taren Vossmark?"

[0.726] Taren Vossmark (taren_vossmark#0, pos 18)
Taren Vossmark, a Flux-sensitive human male, was a legendary Vethari Elder ...

[0.684] Murkwell (murkwell#13, pos 4789)
Years later, Taren Vossmark of the Coalition to Restore the Commonwealth traveled to
Murkwell under the direction of late Vethari Elder Orrin Valdane in hopes of finding
Qelmar and being trained in the ways of the Vethari Circle ...
```

Индексация использует только модель эмбеддингов; LLM на этом этапе не участвует.
