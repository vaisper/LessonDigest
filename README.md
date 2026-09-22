# LessonDigest

**Автоматическая транскрипция и суммаризация школьного урока**  
Запись → текст (ASR) → структурированный дайджест (тема, главное, домашка).

Это репозиторий **сначала архитектуры**, затем кода. Рабочие файлы (аудио, транскрипты, дайджесты) лежат рядом в папках проекта на `D:\LessonDigest`.

---

## Главный тезис

> Аудиозапись урока можно автоматически превратить в полезный структурированный конспект с помощью связки **ASR + LLM**, доступной из России без VPN.

---

## Документация (читать в таком порядке)

| # | Файл | О чём |
|---|------|--------|
| 1 | [docs/00_OVERVIEW.md](docs/00_OVERVIEW.md) | Цель, аудитория, границы продукта |
| 2 | [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) | Общая архитектура системы |
| 3 | [docs/02_PIPELINE.md](docs/02_PIPELINE.md) | Пайплайн шаг за шагом |
| 4 | [docs/03_COMPONENTS.md](docs/03_COMPONENTS.md) | Компоненты и контракты |
| 5 | [docs/04_STACK.md](docs/04_STACK.md) | Стек, API, устройства |
| 6 | [docs/05_DATA_MODEL.md](docs/05_DATA_MODEL.md) | Данные, файлы, хранилище |
| 7 | [docs/06_SECURITY_PRIVACY.md](docs/06_SECURITY_PRIVACY.md) | Приватность, согласия, риски |
| 8 | [docs/07_METRICS.md](docs/07_METRICS.md) | Метрики успеха и эксперименты |
| 9 | [docs/08_MVP0.md](docs/08_MVP0.md) | Scope MVP0 (2–4 недели) |
| 10 | [docs/09_ROADMAP.md](docs/09_ROADMAP.md) | Эволюция после MVP0 |
| 11 | [docs/10_FOLDER_STRUCTURE.md](docs/10_FOLDER_STRUCTURE.md) | Структура папок на диске |
| 12 | [docs/11_PROMPTS.md](docs/11_PROMPTS.md) | Промпты LLM |
| 13 | [docs/12_DEFENSE.md](docs/12_DEFENSE.md) | Защита школьного проекта |
| 14 | [docs/13_RISKS.md](docs/13_RISKS.md) | Риски и митигации |
| 15 | [docs/adr/](docs/adr/) | Архитектурные решения (ADR) |

---

## Быстрая схема (MVP0)

```text
Телефон (диктофон)
      │  .m4a / .mp3 / .wav
      ▼
Ноутбук: LessonDigest (Python)
      │
      ├─ ingest     → принять файл
      ├─ asr        → Whisper / SpeechKit → transcript
      ├─ summarize  → GigaChat → digest
      └─ deliver    → .md (+ позже Telegram)
      ▼
Пользователь: структурированный конспект
```

---

## Статус

- [x] Архитектура в markdown
- [ ] Код MVP0
- [ ] Telegram-бот
- [ ] Своя математика (TF-IDF / TextRank)
- [ ] PWA / мобильное приложение
