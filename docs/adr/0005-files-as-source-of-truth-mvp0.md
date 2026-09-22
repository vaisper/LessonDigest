# ADR-0005: Файлы как source of truth в MVP0

- Status: Accepted
- Date: 2026-09-22

## Context

Можно сразу тащить Postgres/SQLite. Для одного пользователя и школьного MVP это overkill.

## Decision

Артефакты run хранятся в папках `audio/`, `transcripts/`, `digests/`, `runs/`.  
SQLite — когда появится бот и история пользователей.

## Consequences

+ Прозрачность, лёгкий бэкап, удобно для отчёта  
− Слабый поиск/мультипользователь до SQLite
