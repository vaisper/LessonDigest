# 04 — Stack: стек технологий и провайдеры

## 1. Базовый стек MVP0

| Слой | Выбор | Почему |
|------|-------|--------|
| Язык | Python 3.11+ | Экосистема ASR/LLM, быстро для MVP |
| CLI | `argparse` или `typer` | Простота |
| ASR | **faster-whisper** (local) | Бесплатно, РФ ok, хороший русский |
| LLM | **GigaChat API** | Из РФ без VPN, freemium, русский |
| Аудио utils | `ffmpeg` / `ffprobe` | Метаданные и конвертация |
| Конфиг | YAML + `.env` | Стандарт |
| Логи | stdlib `logging` | Достаточно |
| Тесты | `pytest` | Позже |

Fallback LLM: **YandexGPT** (OpenAI-compatible endpoint удобен).  
Fallback ASR: **Yandex SpeechKit** или **Vosk** (если Whisper тяжёлый для железа).

## 2. Устройства

### Запись
- Любой смартфон с диктофоном (iOS/Android).  
- Форматы: m4a/mp3 предпочтительно.

### Обработка MVP0
- Ноутбук Windows (у автора проект на `D:\LessonDigest`).  
- Рекомендуемый минимум: **8 GB RAM**, CPU современный.  
- GPU необязателен; на CPU модель Whisper `small` обычно ок для MVP.

### Обработка MVP1+
- Тот же ноутбук **или** недорогой VPS (оплата картой РФ: Aeza / Timeweb EU).  
- Бот должен иметь исходящий HTTPS до GigaChat / Telegram.

## 3. Сравнение LLM (доступ из РФ)

| Провайдер | VPN | Оплата РФ | Русский | Старт |
|-----------|-----|-----------|---------|-------|
| GigaChat | не нужен | да | отлично | **primary** |
| YandexGPT | не нужен | да | отлично | fallback |
| OpenAI / Anthropic | обычно нужен | сложно | отлично | не берём |
| DeepSeek API | нестабильно | плохо | слабее | не primary |
| Local GGUF | не нужен | нет | зависит | фаза «privacy» |

## 4. Сравнение ASR

| Провайдер | Где | Плюсы | Минусы |
|-----------|-----|-------|--------|
| faster-whisper | local | бесплатно, контроль | CPU время, RAM |
| whisper API OpenAI | cloud | просто | VPN/оплата |
| Yandex SpeechKit | cloud РФ | хороший RU | квоты/деньги |
| Vosk | local | лёгкий | качество ниже |

**Primary MVP0: faster-whisper `small`, language=`ru`.**

## 5. Telegram (фаза MVP1)

- Библиотека: `python-telegram-bot` (v20+ async) или aiogram.  
- Хранение: файлы + позже SQLite.  
- Длинные уроки: принимать как **document**, не voice.

## 6. Что ставить на машину (чеклист)

1. Python 3.11+  
2. Git  
3. ffmpeg в PATH  
4. Аккаунт GigaChat (developers.sber.ru)  
5. (Опц.) CUDA — только если есть NVIDIA и время настроить  

## 7. Зависимости Python (черновик `requirements.txt`)

```text
faster-whisper
python-dotenv
pyyaml
httpx
pydantic
# later:
# python-telegram-bot
# pytest
```

Точные версии зафиксировать при первой рабочей сборке.

## 8. Офлайн vs онлайн

| Режим | ASR | LLM | Когда |
|-------|-----|-----|-------|
| Hybrid (MVP0) | local Whisper | cloud GigaChat | старт |
| Cloud-cloud | SpeechKit | GigaChat | если CPU не тянет |
| Full local | Whisper | Qwen/Llama GGUF | приватность / защита «офлайн» |

Hybrid — лучший баланс для школьного проекта: аудио можно не слать в ASR-облако, текст уходит в GigaChat (всё равно нужен disclosure).
