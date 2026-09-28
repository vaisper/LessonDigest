# 10 — Folder structure: структура на диске

Корень проекта — папка, где лежит `config.yaml` (в примерах `C:\MF\LessonDigest`;
может быть любая, путь задаётся `paths.root` или переменной `LESSONDIGEST_ROOT`).

```text
LessonDigest\
├── README.md
├── .env.example                 # шаблон секретов (без реальных ключей)
├── .env                         # реальные секреты, в git не попадает
├── .gitignore
├── config.yaml                  # несекретный конфиг
├── requirements.txt
├── pyproject.toml               # extras: asr / web / analytic
│
├── certs\
│   └── russian_trusted_ca_bundle.pem   # сертификаты российского УЦ для GigaChat
│
├── docs\                        # архитектура и отчёты
│   ├── 00_OVERVIEW.md … 13_RISKS.md
│   ├── 14_ANALYTIC.md           # своя аналитика (TF-IDF + TextRank)
│   ├── 15_ANALYTIC_RESULTS.md   # сравнение своей аналитики с GigaChat
│   ├── 16_EVALUATION.md         # оценки полезности и домашки
│   ├── adr\                     # ADR-0001 … ADR-0008
│   └── diagrams\                # места под схемы
│
├── prompts\                     # версии промптов
│   ├── v1_digest.txt
│   └── v1_1_digest.txt
│
├── scripts\
│   └── generate_samples.ps1     # пересоздать синтетические озвучки из текстов
│
├── samples\                     # синтетические примеры (большие WAV в .gitignore)
│   ├── sample_ru.wav
│   └── generated\
│       ├── lesson_algebra.txt / .wav
│       ├── lesson_physics.txt / .wav
│       └── lesson_history.txt / .wav
│
├── audio\
│   ├── incoming\                # принятые веб-загрузки (временные)
│   ├── raw\                     # канонические копии входных файлов
│   └── normalized\              # wav 16k mono (опционально)
│
├── transcripts\                 # {run_id}.txt, .segments.json, .chunks.json, .analytic.json
├── digests\                     # {run_id}.md, {run_id}.json, {run_id}.analytic.md
│   └── _eval\                   # оценки людей и summary.md
│
├── runs\                        # {run_id}\run.json и metrics.json
│
└── src\lessondigest\            # код
    ├── cli.py                   # run / doctor / list / eval / analyze / serve
    ├── config.py domain.py storage.py metrics.py logging_setup.py errors.py
    ├── ingest.py media.py chunking.py summarizer.py validate.py pipeline.py
    ├── asr\                     # base, faster_whisper_asr, fake
    ├── summarize\               # base, gigachat, fake, parse, render, normalize
    ├── analytic\                # preprocess, keywords, textrank, homework, compare, engine, render, data\
    ├── deliver\                 # base, file
    └── web\                     # app (FastAPI), jobs (очередь), page (HTML)
```

## Правила

1. Реальные `audio/`, `transcripts/`, `digests/`, `runs/` **не коммитятся** (кроме `_eval/.gitkeep`).
2. Синтетические тексты уроков в `samples/generated/*.txt` — в git; большие `*.wav` — нет
   (пересоздаются `scripts/generate_samples.ps1`).
3. Промпты версионируются файлами: `prompts/v1_...`, `prompts/v1_1_...`.
4. `.env` с секретами никогда не кладётся в архив для сдачи.
