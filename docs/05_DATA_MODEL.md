# 05 — Data model: данные, файлы, метаданные

## 1. Принцип MVP0

**Source of truth = файловая система.**  
База данных не обязательна, пока нет бота с историей многих пользователей.

Позже: SQLite как **индекс** поверх файлов (не замена артефактов).

## 2. Сущности

### Run
Один прогон пайплайна над одним аудио.

| Поле | Тип | Описание |
|------|-----|----------|
| run_id | string | уникальный id |
| created_at | iso8601 | |
| subject | string? | алгебра, физика… |
| status | enum | см. pipeline |
| source_original_name | string | |
| checksum_sha256 | string | |
| duration_sec | float | |
| asr_provider / model | string | |
| llm_provider / model | string | |
| prompt_version | string | |
| timings | object | секунды по stage |
| error | string? | |

### Transcript
| Поле | Тип |
|------|-----|
| text | string |
| segments | array? `{start,end,text}` |
| language | string |
| char_count | int |

### Digest
Структурированный результат:

```json
{
  "topic": "Квадратные уравнения",
  "concepts": ["дискриминант", "теорема Виета"],
  "key_points": ["...", "..."],
  "formulas": ["D = b^2 - 4ac"],
  "homework": "§12 № 345–350",
  "homework_confidence": "high",
  "questions": ["Повторить формулу корней"],
  "prompt_version": "v1",
  "model": "GigaChat-2-Pro"
}
```

`homework_confidence`: `high|medium|low|absent` — либо от LLM, либо эвристика.

### HumanEvaluation (для метрик)
| Поле | Тип |
|------|-----|
| run_id | string |
| usefulness_1_to_5 | int |
| homework_correct | bool \| null |
| notes | string |
| evaluator | string |

## 3. Именование файлов

```text
{YYYYMMDD}_{subject}_{shortid}
пример: 20260923_algebra_a1b2c3
```

`shortid` — 6 hex от hash(checksum + timestamp) или uuid slice.

## 4. JSON-схемы (логические)

Хранить примеры в `docs/schemas/` позже; пока контракт описан здесь.

`run.json` минимальный:

```json
{
  "run_id": "20260923_algebra_a1b2c3",
  "status": "digest_ready",
  "audio_raw": "audio/raw/20260923_algebra_a1b2c3.m4a",
  "transcript": "transcripts/20260923_algebra_a1b2c3.txt",
  "digest_md": "digests/20260923_algebra_a1b2c3.md",
  "digest_json": "digests/20260923_algebra_a1b2c3.json",
  "prompt_version": "v1",
  "timings": {"asr_sec": 312.5, "llm_sec": 18.2}
}
```

## 5. Связи

```text
Run 1──1 Transcript
Run 1──1 Digest
Run 1──0..* HumanEvaluation
Run 1──0..* Chunk (если chunking)
```

## 6. Будущий SQLite (MVP1+)

Таблицы: `runs`, `evaluations`, `users` (telegram_id), `files`.  
Файлы по-прежнему на диске; в БД — пути и индексы поиска по subject/date.
