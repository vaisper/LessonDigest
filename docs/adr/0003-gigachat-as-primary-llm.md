# ADR-0003: GigaChat — основной LLM

- Status: Accepted
- Date: 2026-09-22

## Context

Нужен LLM из России без VPN, с нормальным русским и желательно freemium.  
OpenAI/Anthropic отпадают по доступу/оплате. DeepSeek нестабилен для РФ.

## Decision

Primary: **GigaChat API**.  
Fallback: **YandexGPT**.  
Local GGUF — отдельная «privacy» ветка позже.

## Consequences

+ Соответствует ограничениям среды  
+ Хороший русский для школьных конспектов  
− Нужен OAuth refresh токена  
− Зависимость от внешнего API (закрывается full-local режимом позже)
