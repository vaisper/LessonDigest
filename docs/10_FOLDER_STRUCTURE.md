# 10 — Folder structure: структура на диске

Корень проекта: `D:\LessonDigest`

```text
D:\LessonDigest\
├── README.md
├── .gitignore
├── .env.example                 # шаблон секретов (без реальных ключей)
├── config.yaml                  # несекретный конфиг (появится с кодом)
├── requirements.txt             # появится с кодом
│
├── docs\                        # ← архитектура (сейчас)
│   ├── 00_OVERVIEW.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_PIPELINE.md
│   ├── 03_COMPONENTS.md
│   ├── 04_STACK.md
│   ├── 05_DATA_MODEL.md
│   ├── 06_SECURITY_PRIVACY.md
│   ├── 07_METRICS.md
│   ├── 08_MVP0.md
│   ├── 09_ROADMAP.md
│   ├── 10_FOLDER_STRUCTURE.md
│   ├── 11_PROMPTS.md
│   ├── 12_DEFENSE.md
│   ├── 13_RISKS.md
│   ├── adr\
│   │   ├── 0001-pipeline-not-monolith-script.md
│   │   ├── 0002-mvp0-on-laptop.md
│   │   ├── 0003-gigachat-as-primary-llm.md
│   │   ├── 0004-asr-whisper-first.md
│   │   ├── 0005-files-as-source-of-truth-mvp0.md
│   │   └── 0006-no-custom-asr.md
│   └── diagrams\                # сюда можно класть png/svg позже
│
├── prompts\                     # версии промптов как файлы
│   └── v1_digest.txt
│
├── audio\
│   ├── raw\                     # канонические копии входных файлов
│   └── normalized\              # wav 16k mono (опционально)
│
├── transcripts\                 # .txt + .segments.json
├── digests\                     # .md + .json
│   └── _eval\                   # таблицы оценок людей
│
├── runs\                        # run.json / metrics на каждый прогон
│   └── {run_id}\
│       ├── run.json
│       └── metrics.json
│
└── src\                         # код (позже)
    └── lessondigest\
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        ├── config.py
        ├── ingest.py
        ├── asr\
        ├── summarize\
        ├── deliver\
        ├── storage.py
        └── domain.py
```

## Правила

1. Реальные `audio/` и `transcripts/` **не светятся** в публичном репозитории.  
2. В git можно держать 1–2 **синтетических** сэмпла в `samples/` (добавим при коде).  
3. Промпты версионируются файлами: `prompts/v1_...`, `prompts/v1_1_...`.  
4. Никогда не класть `.env` с секретами в архив для сдачи без очистки.
