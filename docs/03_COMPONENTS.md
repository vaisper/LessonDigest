# 03 — Components: компоненты и контракты

## 1. Карта компонентов

```text
lessondigest/
  cli            — точка входа
  config         — загрузка настроек и секретов
  ingest         — приём и нормализация аудио
  asr            — интерфейс + адаптеры провайдеров
  chunking       — нарезка транскрипта
  summarize      — интерфейс + адаптеры LLM
  deliver        — файл / telegram
  domain         — модели данных (Run, Digest, Transcript)
  storage        — работа с FS (+ позже SQLite)
  logging        — единый логгер
  metrics        — запись таймингов и оценок
```

## 2. Принцип: Ports & Adapters

Ядро знает только **интерфейсы**:

```text
class AsrProvider(Protocol):
    def transcribe(self, audio_path: Path, opts: AsrOptions) -> TranscriptResult: ...

class LlmProvider(Protocol):
    def complete(self, prompt: str, opts: LlmOptions) -> LlmResult: ...

class Deliverer(Protocol):
    def send(self, digest: Digest, dest: Destination) -> None: ...
```

Реализации:

| Port | Adapter MVP0 | Adapter later |
|------|--------------|---------------|
| AsrProvider | `FasterWhisperAsr` | `YandexSpeechKitAsr`, `VoskAsr` |
| LlmProvider | `GigaChatLlm` | `YandexGptLlm`, `LocalGgufLlm` |
| Deliverer | `FileDeliverer` | `TelegramDeliverer` |
| Storage | `FilesystemStorage` | `SqliteIndex` |

## 3. Компонент `cli`

Ответственность:
- парсинг аргументов (`run`, `asr-only`, `summarize-only`, `doctor`);
- сборка графа зависимостей (DI вручную);
- код возврата: 0 ok, 2 validation, 3 asr fail, 4 llm fail.

Пример команд (целевой UX):

```bash
python -m lessondigest doctor
python -m lessondigest run --audio D:\...\lesson.m4a --subject algebra
python -m lessondigest run --audio ... --from summarize --force
```

## 4. Компонент `config`

Источники (приоритет сверху вниз):
1. CLI flags  
2. ENV / `.env`  
3. `config.yaml`  
4. defaults в коде  

Секреты **только** в `.env` (не в git):

```env
GIGACHAT_CLIENT_ID=...
GIGACHAT_CLIENT_SECRET=...
YANDEX_API_KEY=...          # optional
TELEGRAM_BOT_TOKEN=...      # later
```

`config.yaml` — несекретное:

```yaml
paths:
  root: "D:/LessonDigest"
asr:
  provider: faster_whisper
  model: small
  device: cpu
  language: ru
llm:
  provider: gigachat
  model: GigaChat-2-Pro
  prompt_version: v1
chunking:
  enabled: true
  soft_char_limit: 24000
```

## 5. Компонент `ingest`

Контракт:

```text
IngestRequest { source_path, subject?, notes? }
IngestResult  { run_id, raw_audio_path, checksum, duration_sec, media_info }
```

Не занимается распознаванием.

## 6. Компонент `asr`

```text
AsrOptions { language, model, vad?, beam_size? }
TranscriptResult {
  text: str
  segments: list[{start, end, text}] | None
  language: str
  provider: str
  model: str
  elapsed_sec: float
}
```

Инварианты:
- `text` не пустой после успешного вызова;
- кодировка UTF-8;
- язык по умолчанию `ru`.

## 7. Компонент `chunking`

```text
Chunk { index, text, start_sec?, end_sec? }
ChunkingResult { chunks: list[Chunk], strategy: str }
```

## 8. Компонент `summarize`

```text
Digest {
  topic: str
  concepts: list[str]
  key_points: list[str]
  formulas: list[str]
  homework: str | None
  questions: list[str]
  raw_markdown: str
  prompt_version: str
  model: str
}
```

LLM должна по возможности вернуть **и** markdown для человека, **и** JSON для машин (два вызова или один ответ с JSON-блоком — решить в реализации; предпочтительно JSON schema + рендер md).

Рекомендация MVP0:
1. Просить JSON по схеме.  
2. Рендерить `.md` шаблоном у себя (контроль структуры).

## 9. Компонент `deliver`

```text
FileDeliverer → digests/{run_id}.md
TelegramDeliverer → message + optional document
```

## 10. Компонент `storage`

MVP0 layout см. `10_FOLDER_STRUCTURE.md`.

Интерфейс:

```text
save_transcript(run_id, result)
load_transcript(run_id) -> TranscriptResult
save_digest(run_id, digest)
save_run_meta(run_id, meta)
```

## 11. Зависимости между компонентами

```text
cli → config
cli → ingest → storage
cli → asr → storage
cli → chunking
cli → summarize → storage
cli → deliver
cli → metrics
```

Запрещено: `asr` импортирует `summarize`; `gigachat` импортирует `telegram`.

## 12. Точки расширения (extension points)

1. Новый ASR = новый adapter + строка в config.  
2. Новый LLM = новый adapter.  
3. Новый канал доставки = новый Deliverer.  
4. Новая «своя математика» = модуль `analytic/` между ASR и Summarize или parallel path для сравнения.
