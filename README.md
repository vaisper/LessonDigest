# LessonDigest

**Автоматическая транскрипция и суммаризация школьного урока.**
Запись с диктофона → текст (ASR) → структурированный конспект: тема, ключевые понятия,
главные тезисы, формулы, **домашнее задание**.

Проект сделан так, чтобы работать **из России без VPN**: распознавание речи — локально
(faster-whisper), суммаризация — через GigaChat API. Интерфейс — веб-страница, куда
загружают аудио.

---

## Содержание

- [Что умеет](#что-умеет)
- [Как это работает](#как-это-работает)
- [Требования](#требования)
- [Установка с нуля](#установка-с-нуля)
- [Настройка](#настройка)
- [Использование: веб-интерфейс](#использование-веб-интерфейс)
- [Использование: командная строка](#использование-командная-строка)
- [Где лежат результаты](#где-лежат-результаты)
- [Демо без внешних сервисов](#демо-без-внешних-сервисов)
- [Тесты](#тесты)
- [Решение проблем](#решение-проблем)
- [Приватность и безопасность](#приватность-и-безопасность)
- [Структура репозитория](#структура-репозитория)
- [Документация](#документация)
- [Статус и план](#статус-и-план)

---

## Что умеет

- Принимает аудио урока: `.m4a`, `.mp3`, `.wav`, `.ogg`, `.flac`, `.opus`, `.aac`, `.mp4`.
- Считает длительность и параметры файла, копирует оригинал в проект (не трогая запись на телефоне).
- Распознаёт речь локально (faster-whisper, модель `small`, русский язык).
- Для длинных уроков режет транскрипт на части и собирает итог (map-reduce).
- Делает структурированный дайджест через GigaChat и **рендерит `.md` сам** (контроль структуры).
- Проверяет результат (есть ли тема/тезисы/домашка, не выдумана ли домашка).
- Считает метрики времени на каждый этап.
- Отдаёт всё через веб-страницу: загрузка файла, **прогресс обработки в процентах**, просмотр и скачивание дайджеста.

## Как это работает

```text
Телефон (диктофон)
   │  .m4a / .mp3 / .wav
   ▼
Веб-страница (FastAPI)  ──►  очередь задач (1 worker)
   │                              │
   │                              ▼
   │                    ingest   → принять файл, checksum, метаданные
   │                    asr      → faster-whisper → transcript
   │                    chunk    → нарезка, если урок длинный
   │                    summarize→ GigaChat → digest (.md + .json)
   │                    validate → проверки качества
   │                    deliver  → путь к файлу / показ на странице
   ▼
Готовый конспект
```

Ключевые принципы — в [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md). Слои разделены
(ingest / asr / summarize / deliver), между ними — артефакты на диске, поэтому любой этап
можно перезапустить.

## Требования

| Что | Версия / примечание |
|-----|---------------------|
| Python | 3.11+ (проверено на 3.13) |
| ffmpeg | нужен для метаданных и нормализации аудио |
| GigaChat | Client ID + Secret (или один Authorization key), аккаунт физлица — бесплатный старт |
| ОС | Windows (проверено), Linux/macOS тоже должны работать |
| RAM | 8 ГБ достаточно для модели `small` |

> GPU не обязателен: на CPU модель `small` даёт real-time factor ≈ 0.16 (урок 45 минут
> обрабатывается примерно за 7 минут).

## Установка с нуля

Все команды выполняются в PowerShell из папки проекта (пример: `cd C:\MF\LessonDigest` —
подставь свой путь). Если команда `python` не найдена, используй полный путь к `python.exe`.

### 1. Виртуальное окружение

```powershell
cd C:\MF\LessonDigest
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

### 2. Зависимости

Рекомендуемый способ — установить проект с нужными дополнениями (`asr` и `web`):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[asr,web]"
```

Альтернатива, если editable-установка не нужна:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install faster-whisper fastapi uvicorn python-multipart markdown
```

После этого доступна команда `lessondigest` (`.\.venv\Scripts\lessondigest.exe`).

### 3. ffmpeg

Установи один раз в систему (winget, Windows):

```powershell
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
```

Перезапусти терминал, чтобы `ffmpeg` попал в `PATH`. Код дополнительно ищет ffmpeg и в
папке winget, поэтому работать будет даже до перезапуска (см. `src/lessondigest/media.py`).

### 4. Ключи GigaChat

Скопируй шаблон и заполни:

```powershell
Copy-Item .env.example .env
notepad .env
```

**Откуда взять ключи (по шагам):**

1. Зайди в личный кабинет Sber Developer Studio: **https://developers.sber.ru/studio**
   (нужен аккаунт Sber ID; для физлиц доступ к GigaChat API бесплатный на старте).
2. Открой раздел **GigaChat API** и **создай проект** (приложение).
3. Внутри проекта открой **«Авторизационные данные»** (может называться «Настройки API» / «Ключи»).
4. Скопируй значения в `.env`:
   - **Client ID** → `GIGACHAT_CLIENT_ID`;
   - **Client Secret** → `GIGACHAT_CLIENT_SECRET`.
5. Если вместо двух полей показан **один длинный ключ** (Authorization key, base64) —
   вставь его в `GIGACHAT_CLIENT_SECRET` (код распознаёт такой ключ сам) или в `GIGACHAT_AUTH_KEY`.
6. `GIGACHAT_SCOPE` оставь `GIGACHAT_API_PERS` для аккаунта физлица
   (`GIGACHAT_API_B2B` / `GIGACHAT_API_CORP` — для юрлиц).

Проверь, что ключи подхватились:

```powershell
.\.venv\Scripts\lessondigest.exe doctor
```

В строке `GigaChat keys:` должно быть `есть`, а список проблем — пустым.

> Ссылка на конкретное рабочее пространство у каждого своя (в адресе есть личный
> идентификатор) — её не нужно вставлять в файлы репозитория.

### 5. Проверка окружения

```powershell
.\.venv\Scripts\lessondigest.exe doctor
```

Код возврата `0` — всё хорошо; `2` — есть проблемы, они будут перечислены.

## Настройка

### `.env` — только секреты (в git не попадает)

```env
GIGACHAT_CLIENT_ID=
GIGACHAT_CLIENT_SECRET=
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# если в кабинете выдан ОДИН ключ (Authorization key, base64) —
# впиши его сюда, CLIENT_ID/SECRET можно не заполнять
# GIGACHAT_AUTH_KEY=
```

| Переменная | Обязательна | Смысл |
|---|---|---|
| `GIGACHAT_CLIENT_ID` | да* | Client ID приложения GigaChat |
| `GIGACHAT_CLIENT_SECRET` | да* | Client Secret или готовый Authorization key |
| `GIGACHAT_SCOPE` | нет | Тариф: `GIGACHAT_API_PERS` (физлица), `GIGACHAT_API_B2B`, `GIGACHAT_API_CORP` |
| `GIGACHAT_AUTH_KEY` | нет | Альтернатива паре ID/SECRET: один base64-ключ |
| `LESSONDIGEST_ROOT` | нет | Переопределить корень проекта |
| `LESSONDIGEST_CONFIG` | нет | Путь к другому `config.yaml` |
| `LESSONDIGEST_FFMPEG_BIN` / `LESSONDIGEST_FFPROBE_BIN` | нет | Явные пути к ffmpeg/ffprobe |

\* достаточно либо пары ID/SECRET, либо одного `GIGACHAT_AUTH_KEY`.

### `config.yaml` — несекретные настройки

```yaml
paths:
  root: "."            # корень проекта относительно самого config.yaml

asr:
  provider: faster_whisper   # или fake (заглушка для демо)
  model: small               # tiny | base | small | medium
  device: cpu
  compute_type: int8
  language: ru

llm:
  provider: gigachat         # или fake
  model: GigaChat-2-Pro
  prompt_version: v1
  ca_bundle: "certs/russian_trusted_ca_bundle.pem"   # сертификаты российского УЦ

chunking:
  enabled: true
  soft_char_limit: 24000     # больше — включается map-reduce
```

## Использование: веб-интерфейс

Одна команда поднимает **и веб-страницу, и фоновую обработку** (отдельного «бэкенда» нет).

```powershell
cd C:\MF\LessonDigest
.\.venv\Scripts\lessondigest.exe serve
```

Открой **http://127.0.0.1:8000**:

1. «Выбрать файл» — укажи аудио урока.
2. «Предмет» — необязательно (алгебра, физика…).
3. «Обработать» — статус меняется: *в очереди → распознаю речь → делаю конспект → готово*,
   а под ним растёт полоса прогресса с процентами (они честные: считаются по времени
   уже распознанного аудио от общей длительности).
4. Ниже появится дайджест и ссылки «Скачать .md» / «Скачать транскрипт».
5. «История прогонов» — можно вернуться к любому прошлому результату.

Полезно:

- Автодокументация API: **http://127.0.0.1:8000/docs**
- Обработка идёт в фоне — вкладку можно закрыть, задача не прервётся.
- Остановить сервер — `Ctrl + C` в том же окне.

### Доступ с телефона (та же Wi-Fi-сеть)

```powershell
.\.venv\Scripts\lessondigest.exe serve --host 0.0.0.0 --port 8000
ipconfig          # найди «IPv4-адрес», например 192.168.1.42
```

На телефоне открой `http://192.168.1.42:8000`. Windows может спросить разрешение
брандмауэра — разреши для «частных сетей».

> Авторизации нет. Наружу в интернет так выставлять нельзя — см.
> [Приватность и безопасность](#приватность-и-безопасность).

## Использование: командная строка

```powershell
# проверить окружение
.\.venv\Scripts\lessondigest.exe doctor

# обработать урок (локальный ASR + GigaChat)
.\.venv\Scripts\lessondigest.exe run --audio D:\lesson.m4a --subject algebra

# открыть готовый дайджест сразу после обработки
.\.venv\Scripts\lessondigest.exe run --audio D:\lesson.m4a --subject algebra --open

# пересчитать только дайджест по готовому транскрипту
.\.venv\Scripts\lessondigest.exe run --run 20260923_algebra_a1b2c3 --from summarize --force

# список прогонов
.\.venv\Scripts\lessondigest.exe list

# оценить дайджест вручную (для метрик эксперимента)
.\.venv\Scripts\lessondigest.exe eval --run 20260923_algebra_a1b2c3 --usefulness 4 --homework yes
```

Основные команды `run`:

| Флаг | Смысл |
|------|-------|
| `--audio PATH` | путь к аудиофайлу |
| `--run RUN_ID` | продолжить существующий прогон |
| `--subject NAME` | предмет (попадает в `run_id`) |
| `--from auto\|ingest\|asr\|summarize\|deliver` | с какого этапа начать |
| `--force` | пересчитать выбранные этапы заново |
| `--open` | открыть готовый `.md` |
| `--asr-model tiny\|base\|small\|medium` | переопределить модель распознавания |
| `--llm-provider gigachat\|fake`, `--asr-provider faster_whisper\|fake` | переопределить провайдера |

Коды возврата: `0` — успех, `2` — ошибка входных данных/конфига, `3` — ошибка ASR, `4` — ошибка LLM.

## Где лежат результаты

```text
LessonDigest/
├── audio/
│   ├── incoming/        принятые веб-загрузки (временные)
│   ├── raw/             канонические копии входных файлов
│   └── normalized/      wav 16k mono (если используется)
├── transcripts/         <run_id>.txt и <run_id>.segments.json
├── digests/             <run_id>.md (человеку) и <run_id>.json (машине)
│   └── _eval/           оценки людей и summary.md
├── runs/<run_id>/       run.json (статус, метаданные) и metrics.json (тайминги)
├── prompts/             v1_digest.txt и будущие версии
├── samples/             синтетические примеры для тестов
└── src/lessondigest/    код
```

`run_id` имеет вид `20260923_algebra_a1b2c3` (дата _ предмет _ короткий хэш). Он
детерминированный: тот же файл + предмет + дата дают тот же `run_id`, поэтому повторный
запуск не тратит время (пересчёт — через `--force`).

## Демо без внешних сервисов

Без ключей GigaChat и без скачивания моделей можно проверить весь конвейер на заглушках.
Укажи в `config.yaml`:

```yaml
asr:
  provider: fake
llm:
  provider: fake
```

или разово из CLI:

```powershell
.\.venv\Scripts\lessondigest.exe run --audio .\samples\sample_ru.wav --subject demo --llm-provider fake --llm-model fake
```

Результат будет с фиктивным содержимым, но структура, файлы, метрики и веб — настоящие.

Синтетические примеры лежат в `samples/`. Готовые озвучки `samples/generated/*.wav`
большие (~25 МБ) и в git не попадают — их можно пересоздать из текстов:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_samples.ps1
```
Скрипт использует встроенный синтез речи Windows (голос `Microsoft Irina Desktop`).

## Тесты

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Покрыты: конфиг, чанкинг, разбор/рендер дайджеста, валидация, пайплайн end-to-end и веб-API.

## Решение проблем

| Симптом | Причина и решение |
|---------|-------------------|
| `python` не найден | Python не в `PATH`. Вызови полный путь к `python.exe` или переустанови Python с галочкой «Add to PATH». |
| `Activate.ps1 ... cannot be loaded` | Политика выполнения PowerShell. Либо вызывай `.\.venv\Scripts\lessondigest.exe` напрямую, либо один раз: `Set-ExecutionPolicy -Scope Process Bypass`. |
| `ffprobe не найден` | Установи ffmpeg (`winget install --id Gyan.FFmpeg -e`), перезапусти терминал. |
| `faster-whisper не установлен` | `.\.venv\Scripts\python.exe -m pip install faster-whisper`. |
| Первый прогон очень долгий | Идёт скачивание модели (`small` ≈ 460 МБ) в `~/.cache/huggingface`. Дальше — быстрее. |
| Мало RAM / падает на ASR | Возьми модель меньше: `--asr-model base` или `tiny`. |
| `CERTIFICATE_VERIFY_FAILED` | Сертификаты российского УЦ. Бандл уже в `certs/russian_trusted_ca_bundle.pem` и прописан в `config.yaml` (`llm.ca_bundle`). |
| `Can't decode 'Authorization' header` | В кабинете Сбера выдан один Authorization key. Впиши его в `GIGACHAT_CLIENT_SECRET` (код распознаёт) или в `GIGACHAT_AUTH_KEY`. |
| Порт занят (`address already in use`) | Запусти на другом порту: `serve --port 8010`. |
| Не открывается с телефона | Проверь `--host 0.0.0.0`, один Wi-Fi, и разреши приложению доступ в брандмауэре (частные сети). |
| `No module named lessondigest` | Пакет не установлен. Выполни `pip install -e .` или запускай через `python -m lessondigest` с `PYTHONPATH=src`. |

## Приватность и безопасность

- Аудио урока и транскрипты — **персональные данные**. Нужно согласие учителя на запись.
- В MVP-режиме аудио распознаётся **локально**, а текст транскрипта уходит в **GigaChat**.
- Секреты — только в `.env`; файл в `.gitignore` и в репозиторий не попадает.
- Реальные `audio/`, `transcripts/`, `digests/`, `runs/` тоже не коммитятся.
- Веб-интерфейс не имеет авторизации: только локально или в своей сети. Для публикации
  нужны логин и HTTPS.

Подробнее — [docs/06_SECURITY_PRIVACY.md](docs/06_SECURITY_PRIVACY.md).

## Структура репозитория

```text
src/lessondigest/
├── cli.py            команды: doctor / run / list / eval / serve
├── config.py         config.yaml + .env
├── domain.py         модели (RunMeta, Transcript, Digest, …)
├── ingest.py         приём и метаданные файла
├── media.py          ffprobe / ffmpeg
├── chunking.py       нарезка длинного транскрипта
├── summarizer.py     промпт + map-reduce → дайджест
├── validate.py       автопроверки результата
├── pipeline.py       оркестрация этапов
├── storage.py        файловое хранилище артефактов
├── metrics.py        тайминги и счётчики
├── asr/              адаптеры распознавания (faster-whisper, fake)
├── summarize/        адаптеры LLM (GigaChat, fake), разбор и рендер
├── deliver/          выдача результата (файл)
└── web/              FastAPI: очередь задач, API и страница
```

## Документация

Читать по порядку:

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
| 9 | [docs/08_MVP0.md](docs/08_MVP0.md) | Scope MVP0 |
| 10 | [docs/09_ROADMAP.md](docs/09_ROADMAP.md) | Эволюция после MVP0 |
| 11 | [docs/10_FOLDER_STRUCTURE.md](docs/10_FOLDER_STRUCTURE.md) | Структура папок на диске |
| 12 | [docs/11_PROMPTS.md](docs/11_PROMPTS.md) | Промпты LLM |
| 13 | [docs/12_DEFENSE.md](docs/12_DEFENSE.md) | Защита школьного проекта |
| 14 | [docs/13_RISKS.md](docs/13_RISKS.md) | Риски и митигации |
| 15 | [docs/adr/](docs/adr/) | Архитектурные решения (ADR) |

## Статус и план

- [x] Архитектура в markdown
- [x] Пайплайн: CLI, ingest, ASR/LLM-адаптеры, chunking, summary, validate, deliver, metrics, storage
- [x] Реальные прогоны faster-whisper + GigaChat (RTF ≈ 0.16 на CPU)
- [x] Веб-интерфейс (FastAPI): загрузка из браузера, фоновая очередь, просмотр дайджеста
- [ ] 5–10 прогонов на **реальных** записях урока + оценки (`docs/07_METRICS.md`)
- [ ] `prompt v1.1`: чистка формул и обозначений
- [ ] Своя математика (TF-IDF / TextRank) — научная часть
- [ ] Авторизация веб-интерфейса и HTTPS для доступа не из своей сети
