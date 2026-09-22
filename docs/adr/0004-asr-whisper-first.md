# ADR-0004: Whisper local — основной ASR

- Status: Accepted
- Date: 2026-09-22

## Context

Нужен русский ASR. Облачный OpenAI Whisper неудобен из РФ.  
Vosk легче, но качество обычно хуже.

## Decision

Primary: **faster-whisper** локально, модель `small`, `language=ru`.  
Fallback: Yandex SpeechKit или меньшая модель Whisper / Vosk.

## Consequences

+ Аудио можно не отдавать в ASR-облако  
+ Бесплатно  
− Время на CPU; нужен ffmpeg; RAM
